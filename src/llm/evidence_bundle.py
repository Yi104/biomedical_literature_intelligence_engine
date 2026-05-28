from __future__ import annotations

from typing import Any, Dict, List


def _sorted_unique_pmids(records: List[Dict[str, Any]]) -> List[str]:
    return sorted({str(r.get("pmid", "")).strip() for r in records if str(r.get("pmid", "")).strip()})


def _relation_record_to_bundle_row(row: Dict[str, Any]) -> Dict[str, Any]:
    provenance = row.get("provenance", [])
    first_provenance = provenance[0] if provenance else {}
    return {
        "evidence_type": "relation",
        "pmid": str(row.get("pmid", "")),
        "relation_type": str(row.get("relation_type", "")),
        "entity1_text": str(row.get("entity1_text", "")),
        "entity1_type": str(row.get("entity1_type", "")),
        "entity1_normalized_id": str(row.get("entity1_normalized_id", "")),
        "entity2_text": str(row.get("entity2_text", "")),
        "entity2_type": str(row.get("entity2_type", "")),
        "entity2_normalized_id": str(row.get("entity2_normalized_id", "")),
        "evidence_sentence": str(first_provenance.get("evidence_sentence", "")),
        "novelty": str(first_provenance.get("novelty", "")),
        "provenance_source": str(first_provenance.get("provenance_source", "")),
        "confidence": float(first_provenance.get("confidence", 0.0) or 0.0),
    }


def _sentence_record_to_bundle_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "evidence_type": "sentence",
        "pmid": str(row.get("pmid", "")),
        "task": str(row.get("task", "")),
        "sentence_index": int(row.get("sentence_index", -1)),
        "evidence_sentence": str(row.get("sentence_text", "")),
        "entities": row.get("entities", []),
        "source": str(row.get("source", "")),
    }


def _mention_record_to_bundle_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "evidence_type": "mention",
        "pmid": str(row.get("pmid", "")),
        "entity_type": str(row.get("entity_type", "")),
        "entity_text": str(row.get("entity_text", "")),
        "normalized_id": str(row.get("normalized_id", "")),
        "normalized_text": str(row.get("normalized_text", "")),
    }


def build_evidence_bundle_from_agent_result(
    question: str,
    agent_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Normalize L5 output into a stable L6 input contract.
    """
    mode = str(agent_result.get("retrieval_mode", ""))
    task = str(agent_result.get("task", ""))
    status = str(agent_result.get("status", ""))
    evidence = agent_result.get("evidence", [])
    if not isinstance(evidence, list):
        evidence = []

    rows: List[Dict[str, Any]] = []
    if mode.startswith("relation_"):
        rows = [_relation_record_to_bundle_row(r) for r in evidence]
    elif mode.startswith("evidence_"):
        rows = [_sentence_record_to_bundle_row(r) for r in evidence]
    else:
        rows = [_mention_record_to_bundle_row(r) for r in evidence]

    return {
        "question": question,
        "task": task,
        "retrieval_mode": mode,
        "status": status,
        "insufficient_evidence": len(rows) == 0,
        "count": len(rows),
        "pmids": _sorted_unique_pmids(rows),
        "records": rows,
        "filters": agent_result.get("filters", {}),
    }
