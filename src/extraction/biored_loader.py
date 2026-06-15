from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import pandas as pd

from src.kb.evidence import split_abstract_into_sentences


@dataclass
class _BioRedEntity:
    text: str
    entity_type: str
    concept_ids: List[str]
    start: int
    end: int


@dataclass
class _BioRedRelation:
    relation_type: str
    concept_1: str
    concept_2: str
    novelty: str


def _iter_pubtator_docs(path: str):
    with open(path, "r", encoding="utf-8") as f:
        block: List[str] = []
        for raw_line in f:
            line = raw_line.rstrip("\n")
            if line.strip():
                block.append(line)
            elif block:
                yield block
                block = []
        if block:
            yield block


def _parse_pubtator_doc(lines: List[str]) -> Tuple[Dict, List[_BioRedEntity], List[_BioRedRelation]]:
    if len(lines) < 2:
        raise ValueError("Each BioRED PubTator document must contain title and abstract lines.")

    pmid_title = lines[0].split("|", 2)
    pmid_abs = lines[1].split("|", 2)
    if len(pmid_title) < 3 or len(pmid_abs) < 3:
        raise ValueError("Unexpected BioRED PubTator title/abstract format.")

    pmid = str(pmid_title[0]).strip()
    title = pmid_title[2].strip()
    abstract = pmid_abs[2].strip()

    entities: List[_BioRedEntity] = []
    relations: List[_BioRedRelation] = []
    for line in lines[2:]:
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        type_marker = parts[1].strip()
        if type_marker.isnumeric() and len(parts) >= 6:
            start = int(type_marker)
            end = int(parts[2].strip())
            mention = parts[3].strip()
            entity_type = parts[4].strip()
            concept_ids = [x.strip() for x in parts[5].split(",") if x.strip()]
            if not concept_ids:
                concept_ids = ["UNRESOLVED"]
            entities.append(
                _BioRedEntity(
                    text=mention,
                    entity_type=entity_type,
                    concept_ids=concept_ids,
                    start=start,
                    end=end,
                )
            )
        elif len(parts) >= 5:
            relation_type = parts[1].strip()
            relations.append(
                _BioRedRelation(
                    relation_type=relation_type,
                    concept_1=parts[2].strip(),
                    concept_2=parts[3].strip(),
                    novelty=parts[4].strip(),
                )
            )

    paper = {
        "pmid": pmid,
        "title": title,
        "year": "",
        "journal": "",
        "abstract": abstract,
    }
    return paper, entities, relations


def _select_evidence_sentence(abstract: str, head_text: str, tail_text: str) -> str:
    for sentence in split_abstract_into_sentences(abstract):
        s = sentence.lower()
        if head_text.lower() in s and tail_text.lower() in s:
            return sentence
    return split_abstract_into_sentences(abstract)[0] if abstract else ""


def load_biored_pubtator_as_dataframes(
    *,
    pubtator_path: str,
    max_docs: int | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load BioRED PubTator file and convert it into papers/entities/relations tables.
    """
    papers_rows: List[Dict] = []
    entities_rows: List[Dict] = []
    relations_rows: List[Dict] = []

    docs_seen = 0
    for doc_lines in _iter_pubtator_docs(pubtator_path):
        paper, entities, relations = _parse_pubtator_doc(doc_lines)
        pmid = paper["pmid"]

        concept_to_primary_mention: Dict[str, Tuple[str, str]] = {}
        for ent in entities:
            for concept_id in ent.concept_ids:
                concept_to_primary_mention.setdefault(concept_id, (ent.text, ent.entity_type))
                entities_rows.append(
                    {
                        "pmid": pmid,
                        "entity_type": ent.entity_type,
                        "entity_text": ent.text,
                        "token_start": ent.start,
                        "token_end": ent.end,
                        "normalized_text": ent.text,
                        "normalized_id": concept_id,
                        "normalized_source": "biored_annotation_v1",
                        "normalized_score": 1.0,
                    }
                )

        for rel in relations:
            head_text, head_type = concept_to_primary_mention.get(rel.concept_1, ("", "Unknown"))
            tail_text, tail_type = concept_to_primary_mention.get(rel.concept_2, ("", "Unknown"))
            relations_rows.append(
                {
                    "pmid": pmid,
                    "relation_type": rel.relation_type,
                    "entity1_text": head_text,
                    "entity1_type": head_type,
                    "entity1_normalized_id": rel.concept_1,
                    "entity2_text": tail_text,
                    "entity2_type": tail_type,
                    "entity2_normalized_id": rel.concept_2,
                    "evidence_sentence": _select_evidence_sentence(
                        paper["abstract"], head_text, tail_text
                    ),
                    "relation_source": "biored_pubtator",
                    "novelty": rel.novelty,
                    "confidence": 1.0,
                }
            )

        paper["entity_count"] = len(entities)
        paper["entity_types"] = ", ".join(
            sorted({ent.entity_type for ent in entities})
        )
        papers_rows.append(paper)
        docs_seen += 1
        if max_docs is not None and docs_seen >= max_docs:
            break

    papers_df = pd.DataFrame(papers_rows)
    entities_df = pd.DataFrame(entities_rows)
    relations_df = pd.DataFrame(relations_rows)

    if papers_df.empty:
        papers_df = pd.DataFrame(
            columns=["pmid", "title", "year", "journal", "abstract", "entity_count", "entity_types"]
        )
    if entities_df.empty:
        entities_df = pd.DataFrame(
            columns=[
                "pmid",
                "entity_type",
                "entity_text",
                "token_start",
                "token_end",
                "normalized_text",
                "normalized_id",
                "normalized_source",
                "normalized_score",
            ]
        )
    if relations_df.empty:
        relations_df = pd.DataFrame(
            columns=[
                "pmid",
                "relation_type",
                "entity1_text",
                "entity1_type",
                "entity1_normalized_id",
                "entity2_text",
                "entity2_type",
                "entity2_normalized_id",
                "evidence_sentence",
                "relation_source",
                "novelty",
                "confidence",
            ]
        )

    # Ensure exact contract order expected by biored:v1 (+ novelty for provenance).
    relations_df = relations_df[
        [
            "pmid",
            "relation_type",
            "entity1_text",
            "entity1_type",
            "entity1_normalized_id",
            "entity2_text",
            "entity2_type",
            "entity2_normalized_id",
            "evidence_sentence",
            "relation_source",
            "novelty",
            "confidence",
        ]
    ]
    return papers_df, entities_df, relations_df
