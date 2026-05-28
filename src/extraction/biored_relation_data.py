from __future__ import annotations

import random
from dataclasses import dataclass
from itertools import combinations
from typing import Dict, List, Tuple

import pandas as pd

from src.kb.evidence import split_abstract_into_sentences

GENE_TYPES = {"GeneOrGeneProduct"}
DISEASE_TYPES = {"DiseaseOrPhenotypicFeature"}


@dataclass(frozen=True)
class RelationSample:
    pmid: str
    sentence: str
    head_text: str
    head_type: str
    head_id: str
    tail_text: str
    tail_type: str
    tail_id: str
    label: str
    split: str


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


def _parse_pubtator_doc(lines: List[str]) -> Tuple[str, str, List[Dict], List[Dict]]:
    pmid = lines[0].split("|", 2)[0].strip()
    abstract = lines[1].split("|", 2)[2].strip() if len(lines) > 1 else ""
    entities: List[Dict] = []
    relations: List[Dict] = []
    for line in lines[2:]:
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        if parts[1].isnumeric() and len(parts) >= 6:
            concept_ids = [x.strip() for x in parts[5].split(",") if x.strip()]
            if not concept_ids:
                concept_ids = ["UNRESOLVED"]
            entities.append(
                {
                    "text": parts[3].strip(),
                    "type": parts[4].strip(),
                    "concept_ids": concept_ids,
                }
            )
        elif len(parts) >= 5:
            relations.append(
                {
                    "relation_type": parts[1].strip(),
                    "concept_1": parts[2].strip(),
                    "concept_2": parts[3].strip(),
                }
            )
    return pmid, abstract, entities, relations


def _is_allowed_pair(type_a: str, type_b: str, pair_mode: str) -> bool:
    if pair_mode == "gene_disease":
        return (type_a in GENE_TYPES and type_b in DISEASE_TYPES) or (
            type_a in DISEASE_TYPES and type_b in GENE_TYPES
        )
    if pair_mode == "all":
        return True
    raise ValueError(f"Unknown pair_mode: {pair_mode}")


def _select_sentence(abstract: str, left_text: str, right_text: str) -> str:
    for sentence in split_abstract_into_sentences(abstract):
        s = sentence.lower()
        if left_text.lower() in s and right_text.lower() in s:
            return sentence
    sentences = split_abstract_into_sentences(abstract)
    return sentences[0] if sentences else abstract


def build_biored_relation_samples(
    *,
    pubtator_path: str,
    split: str,
    pair_mode: str = "gene_disease",
    negative_ratio: int = 1,
    max_docs: int | None = None,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Build relation samples with positives from gold annotations and negatives
    from unlabeled candidate pairs in the same corpus.
    """
    if negative_ratio < 1:
        raise ValueError("negative_ratio must be >= 1")
    rng = random.Random(seed)

    positives: List[RelationSample] = []
    negatives: List[RelationSample] = []

    seen_docs = 0
    for lines in _iter_pubtator_docs(pubtator_path):
        pmid, abstract, entities, relations = _parse_pubtator_doc(lines)

        concept_to_repr: Dict[str, Tuple[str, str]] = {}
        for ent in entities:
            for cid in ent["concept_ids"]:
                concept_to_repr.setdefault(cid, (ent["text"], ent["type"]))

        gold_pairs: set[Tuple[str, str]] = set()
        for rel in relations:
            c1, c2 = rel["concept_1"], rel["concept_2"]
            if c1 not in concept_to_repr or c2 not in concept_to_repr:
                continue
            t1 = concept_to_repr[c1][1]
            t2 = concept_to_repr[c2][1]
            if not _is_allowed_pair(t1, t2, pair_mode):
                continue
            gold_pairs.add((c1, c2))
            sentence = _select_sentence(abstract, concept_to_repr[c1][0], concept_to_repr[c2][0])
            positives.append(
                RelationSample(
                    pmid=pmid,
                    sentence=sentence,
                    head_text=concept_to_repr[c1][0],
                    head_type=t1,
                    head_id=c1,
                    tail_text=concept_to_repr[c2][0],
                    tail_type=t2,
                    tail_id=c2,
                    label=rel["relation_type"],
                    split=split,
                )
            )

        concept_ids = sorted(concept_to_repr.keys())
        candidate_pairs: List[Tuple[str, str]] = []
        for a, b in combinations(concept_ids, 2):
            ta = concept_to_repr[a][1]
            tb = concept_to_repr[b][1]
            if not _is_allowed_pair(ta, tb, pair_mode):
                continue
            # Respect direction by checking both orientations in positives.
            if (a, b) in gold_pairs or (b, a) in gold_pairs:
                continue
            candidate_pairs.append((a, b))

        rng.shuffle(candidate_pairs)
        # defer ratio application globally for stable sample size across docs
        for a, b in candidate_pairs:
            sentence = _select_sentence(abstract, concept_to_repr[a][0], concept_to_repr[b][0])
            negatives.append(
                RelationSample(
                    pmid=pmid,
                    sentence=sentence,
                    head_text=concept_to_repr[a][0],
                    head_type=concept_to_repr[a][1],
                    head_id=a,
                    tail_text=concept_to_repr[b][0],
                    tail_type=concept_to_repr[b][1],
                    tail_id=b,
                    label="No_Relation",
                    split=split,
                )
            )

        seen_docs += 1
        if max_docs is not None and seen_docs >= max_docs:
            break

    neg_keep = min(len(negatives), len(positives) * negative_ratio)
    rng.shuffle(negatives)
    selected = positives + negatives[:neg_keep]
    rng.shuffle(selected)

    return pd.DataFrame(
        [
            {
                "pmid": x.pmid,
                "sentence": x.sentence,
                "head_text": x.head_text,
                "head_type": x.head_type,
                "head_id": x.head_id,
                "tail_text": x.tail_text,
                "tail_type": x.tail_type,
                "tail_id": x.tail_id,
                "label": x.label,
                "split": x.split,
            }
            for x in selected
        ]
    )
