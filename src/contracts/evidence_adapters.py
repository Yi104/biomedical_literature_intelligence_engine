from __future__ import annotations

from typing import Any

from src.contracts.unified_evidence_schema import (
    EvidenceBundleV1,
    EvidenceRecord,
    EntityRecord,
    ProvenanceRecord,
    RelationRecord,
    SCHEMA_VERSION,
)


def _safe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _derived_entity_id(
    *,
    pmid: str,
    entity_type: str,
    token_start: int | None,
    token_end: int | None,
    entity_text: str,
) -> str:
    return f"entity:{pmid}:{entity_type}:{token_start}:{token_end}:{entity_text}"


def _derived_relation_id(
    *,
    pmid: str,
    relation_type: str,
    entity1_normalized_id: str,
    entity2_normalized_id: str,
) -> str:
    return (
        f"rel:{pmid}:{entity1_normalized_id}:{entity2_normalized_id}:{relation_type}"
    )


def _derived_evidence_id(*, pmid: str, sentence_index: int | None, fallback: Any) -> str:
    if sentence_index is not None and sentence_index >= 0:
        return f"ev:{pmid}:{sentence_index}"
    return f"ev:{pmid}:{fallback}"


def _document_id_for_pmid(pmid: str) -> str:
    return f"pmid:{pmid}"


def mention_row_to_entity_record(row: dict[str, Any]) -> EntityRecord:
    pmid = str(row.get("pmid", ""))
    entity_type = str(row.get("entity_type", ""))
    entity_text = str(row.get("entity_text", ""))
    token_start = _safe_int(row.get("token_start"))
    token_end = _safe_int(row.get("token_end"))

    record: EntityRecord = {
        "entity_id": _derived_entity_id(
            pmid=pmid,
            entity_type=entity_type,
            token_start=token_start,
            token_end=token_end,
            entity_text=entity_text,
        ),
        "pmid": pmid,
        "document_id": _document_id_for_pmid(pmid),
        "text": entity_text,
        "type": entity_type,
        "mention_span": {
            "token_start": token_start,
            "token_end": token_end,
            "char_start": None,
            "char_end": None,
        },
    }

    normalized_id = str(row.get("normalized_id", "") or "")
    normalized_text = str(row.get("normalized_text", "") or "")
    if normalized_id:
        source_vocab = str(row.get("normalized_source", "") or "")
        if ":" in normalized_id:
            source_vocab = normalized_id.split(":", 1)[0]
        record["normalized"] = {
            "id": normalized_id,
            "label": normalized_text,
            "source_vocab": source_vocab,
            "method": str(row.get("normalized_source", "") or ""),
            "score": _safe_float(row.get("normalized_score")),
        }
    return record


def entity_row_to_entity_record(row: dict[str, Any]) -> EntityRecord:
    return mention_row_to_entity_record(row)


def relation_row_to_relation_record(row: dict[str, Any]) -> RelationRecord:
    pmid = str(row.get("pmid", ""))
    relation_type = str(row.get("relation_type", ""))
    entity1_type = str(row.get("entity1_type", ""))
    entity2_type = str(row.get("entity2_type", ""))
    entity1_text = str(row.get("entity1_text", ""))
    entity2_text = str(row.get("entity2_text", ""))
    entity1_normalized_id = str(row.get("entity1_normalized_id", ""))
    entity2_normalized_id = str(row.get("entity2_normalized_id", ""))
    relation_id = _derived_relation_id(
        pmid=pmid,
        relation_type=relation_type,
        entity1_normalized_id=entity1_normalized_id,
        entity2_normalized_id=entity2_normalized_id,
    )

    first_provenance = {}
    provenance = row.get("provenance", [])
    if isinstance(provenance, list) and provenance:
        first_provenance = provenance[0]

    return {
        "relation_id": relation_id,
        "pmid": pmid,
        "document_id": _document_id_for_pmid(pmid),
        "type": relation_type,
        "subject": {
            "entity_id": _derived_entity_id(
                pmid=pmid,
                entity_type=entity1_type,
                token_start=None,
                token_end=None,
                entity_text=entity1_text,
            ),
            "text": entity1_text,
            "type": entity1_type,
            "normalized_id": entity1_normalized_id,
        },
        "object": {
            "entity_id": _derived_entity_id(
                pmid=pmid,
                entity_type=entity2_type,
                token_start=None,
                token_end=None,
                entity_text=entity2_text,
            ),
            "text": entity2_text,
            "type": entity2_type,
            "normalized_id": entity2_normalized_id,
        },
        "extraction": {
            "source": str(row.get("relation_source", "")),
            "confidence": _safe_float(first_provenance.get("confidence"), default=0.0),
            "novelty": str(first_provenance.get("novelty", "") or ""),
        },
    }


def sentence_row_to_evidence_record(
    row: dict[str, Any],
    *,
    relation_id: str | None = None,
) -> EvidenceRecord:
    pmid = str(row.get("pmid", ""))
    sentence_index = _safe_int(row.get("sentence_index"))
    evidence_id = _derived_evidence_id(
        pmid=pmid,
        sentence_index=sentence_index,
        fallback=row.get("evidence_id", "unknown"),
    )
    record: EvidenceRecord = {
        "evidence_id": evidence_id,
        "pmid": pmid,
        "document_id": _document_id_for_pmid(pmid),
        "text": str(row.get("sentence_text", row.get("evidence_sentence", ""))),
        "source": str(row.get("source", "pubmed_abstract") or "pubmed_abstract"),
        "sentence_index": sentence_index,
    }
    if relation_id:
        record["supports"] = {"relation_id": relation_id}
        record["score"] = {
            "relation_confidence": _safe_float(row.get("confidence"), default=0.0),
            "evidence_rank_score": _safe_float(row.get("confidence"), default=0.0),
        }
    return record


def provenance_row_to_provenance_record(
    row: dict[str, Any],
    *,
    pmid: str,
    relation_id: str | None = None,
    evidence_id: str | None = None,
    linked_entities: list[str] | None = None,
) -> ProvenanceRecord:
    sentence_index = _safe_int(row.get("sentence_index"))
    relation_key = relation_id or "unknown"
    evidence_key = evidence_id or f"ev:{pmid}:unknown"
    record: ProvenanceRecord = {
        "provenance_id": f"prov:{relation_key}:{evidence_key}",
        "pmid": pmid,
        "source_document": str(row.get("source_document", "pubmed_abstract") or "pubmed_abstract"),
        "source_pmid": pmid,
        "method": str(row.get("link_method", "surface_match_v1") or "surface_match_v1"),
        "source_system": str(
            row.get("provenance_source", row.get("source_system", "")) or ""
        ),
        "sentence_index": sentence_index,
        "sentence_span": {
            "char_start": _safe_int(row.get("char_start")),
            "char_end": _safe_int(row.get("char_end")),
        },
        "linked_entities": linked_entities or [],
        "evidence_sentence": str(row.get("evidence_sentence", "") or ""),
        "confidence": _safe_float(row.get("confidence"), default=0.0),
        "novelty": str(row.get("novelty", "") or ""),
    }
    if relation_id:
        record["relation_id"] = relation_id
    if evidence_id:
        record["evidence_id"] = evidence_id
    return record


def _sorted_unique_pmids_from_sections(
    entities: list[EntityRecord],
    relations: list[RelationRecord],
    evidence: list[EvidenceRecord],
) -> list[str]:
    pmids = {
        str(row.get("pmid", "")).strip()
        for collection in (entities, relations, evidence)
        for row in collection
        if str(row.get("pmid", "")).strip()
    }
    return sorted(pmids)


def _relation_record_to_legacy_row(
    relation: RelationRecord,
    evidence: list[EvidenceRecord],
    provenance: list[ProvenanceRecord],
) -> dict[str, Any]:
    relation_id = relation["relation_id"]
    evidence_row = next(
        (row for row in evidence if row.get("supports", {}).get("relation_id") == relation_id),
        {},
    )
    prov_rows = [row for row in provenance if row.get("relation_id") == relation_id]
    confidence = float(relation["extraction"].get("confidence", 0.0) or 0.0)
    return {
        "evidence_type": "relation",
        "pmid": relation["pmid"],
        "relation_type": relation["type"],
        "entity1_text": relation["subject"]["text"],
        "entity1_type": relation["subject"]["type"],
        "entity1_normalized_id": relation["subject"]["normalized_id"],
        "entity2_text": relation["object"]["text"],
        "entity2_type": relation["object"]["type"],
        "entity2_normalized_id": relation["object"]["normalized_id"],
        "evidence_sentence": str(evidence_row.get("text", "")),
        "novelty": str(relation["extraction"].get("novelty", "")),
        "provenance_source": str(
            prov_rows[0].get("source_system", "") if prov_rows else relation["extraction"].get("source", "")
        ),
        "confidence": confidence,
    }


def _sentence_record_to_legacy_row(row: EvidenceRecord, entities: list[EntityRecord]) -> dict[str, Any]:
    pmid = row["pmid"]
    linked_entities = [entity for entity in entities if entity["pmid"] == pmid]
    return {
        "evidence_type": "sentence",
        "pmid": pmid,
        "task": "",
        "sentence_index": row.get("sentence_index", -1),
        "evidence_sentence": row["text"],
        "entities": [
            {
                "entity_text": entity["text"],
                "entity_type": entity["type"],
                "normalized_id": entity.get("normalized", {}).get("id", ""),
                "normalized_text": entity.get("normalized", {}).get("label", ""),
            }
            for entity in linked_entities
        ],
        "source": row["source"],
    }


def _entity_record_to_legacy_row(row: EntityRecord) -> dict[str, Any]:
    normalized = row.get("normalized", {})
    return {
        "evidence_type": "mention",
        "pmid": row["pmid"],
        "entity_type": row["type"],
        "entity_text": row["text"],
        "normalized_id": str(normalized.get("id", "")),
        "normalized_text": str(normalized.get("label", "")),
    }


def build_unified_evidence_bundle_from_agent_result(
    question: str,
    agent_result: dict[str, Any],
) -> EvidenceBundleV1:
    mode = str(agent_result.get("retrieval_mode", ""))
    task = str(agent_result.get("task", ""))
    status = str(agent_result.get("status", ""))
    rows = agent_result.get("evidence", [])
    if not isinstance(rows, list):
        rows = []

    entities: list[EntityRecord] = []
    relations: list[RelationRecord] = []
    evidence: list[EvidenceRecord] = []
    provenance: list[ProvenanceRecord] = []

    if mode.startswith("relation_"):
        for row in rows:
            relation = relation_row_to_relation_record(row)
            relations.append(relation)
            relation_id = relation["relation_id"]
            prov_rows = row.get("provenance", [])
            if not isinstance(prov_rows, list):
                prov_rows = []
            for idx, prov_row in enumerate(prov_rows):
                ev = sentence_row_to_evidence_record(
                    {
                        "pmid": relation["pmid"],
                        "sentence_index": idx,
                        "evidence_sentence": prov_row.get("evidence_sentence", ""),
                        "confidence": prov_row.get("confidence", 0.0),
                        "source": "pubmed_abstract",
                    },
                    relation_id=relation_id,
                )
                evidence.append(ev)
                provenance.append(
                    provenance_row_to_provenance_record(
                        prov_row,
                        pmid=relation["pmid"],
                        relation_id=relation_id,
                        evidence_id=ev["evidence_id"],
                        linked_entities=[
                            relation["subject"]["entity_id"],
                            relation["object"]["entity_id"],
                        ],
                    )
                )
    elif mode.startswith("evidence_"):
        for row in rows:
            evidence.append(sentence_row_to_evidence_record(row))
            for entity_row in row.get("entities", []):
                entity_with_pmid = dict(entity_row)
                entity_with_pmid["pmid"] = row.get("pmid", "")
                entities.append(entity_row_to_entity_record(entity_with_pmid))
    else:
        for row in rows:
            entities.append(mention_row_to_entity_record(row))

    documents = [
        {
            "document_id": _document_id_for_pmid(pmid),
            "pmid": pmid,
            "source": "pubmed",
        }
        for pmid in _sorted_unique_pmids_from_sections(entities, relations, evidence)
    ]

    if mode.startswith("relation_"):
        records = [
            _relation_record_to_legacy_row(relation, evidence, provenance)
            for relation in relations
        ]
    elif mode.startswith("evidence_"):
        records = [_sentence_record_to_legacy_row(row, entities) for row in evidence]
    else:
        records = [_entity_record_to_legacy_row(row) for row in entities]

    return {
        "schema_version": SCHEMA_VERSION,
        "question": question,
        "task": task,
        "retrieval_mode": mode,
        "status": status,
        "insufficient_evidence": len(rows) == 0,
        "count": len(rows),
        "pmids": _sorted_unique_pmids_from_sections(entities, relations, evidence),
        "filters": agent_result.get("filters", {}),
        "documents": documents,
        "entities": entities,
        "relations": relations,
        "evidence": evidence,
        "provenance": provenance,
        "records": records,
    }
