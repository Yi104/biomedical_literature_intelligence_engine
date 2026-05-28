from __future__ import annotations

from typing import Any, Dict, List


def _build_claims_from_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    claims: List[Dict[str, Any]] = []
    for row in records:
        evidence_type = str(row.get("evidence_type", ""))
        pmid = str(row.get("pmid", ""))
        if evidence_type == "relation":
            relation_type = str(row.get("relation_type", ""))
            e1 = str(row.get("entity1_text", ""))
            e2 = str(row.get("entity2_text", ""))
            text = f"{e1} -[{relation_type}]-> {e2}".strip()
            claims.append(
                {
                    "text": text,
                    "pmids": [pmid] if pmid else [],
                    "evidence_type": "relation",
                }
            )
        elif evidence_type == "sentence":
            sentence = str(row.get("evidence_sentence", ""))
            claims.append(
                {
                    "text": sentence,
                    "pmids": [pmid] if pmid else [],
                    "evidence_type": "sentence",
                }
            )
        elif evidence_type == "mention":
            mention = str(row.get("entity_text", ""))
            ent_type = str(row.get("entity_type", ""))
            text = f"{ent_type}: {mention}".strip()
            claims.append(
                {
                    "text": text,
                    "pmids": [pmid] if pmid else [],
                    "evidence_type": "mention",
                }
            )
    return claims


def build_l7_answer(
    *,
    question: str,
    agent_result: Dict[str, Any],
    l6_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build a stable L7 JSON contract from L5 and L6 outputs.
    """
    bundle = l6_result.get("bundle") or l6_result.get("evidence") or {}
    records = bundle.get("records", []) if isinstance(bundle, dict) else []
    pmids = bundle.get("pmids", []) if isinstance(bundle, dict) else []
    claims = _build_claims_from_records(records if isinstance(records, list) else [])

    provider = str(l6_result.get("provider", "none"))
    summary = str(l6_result.get("summary", "") or "")
    if not summary:
        summary = "insufficient evidence" if len(records) == 0 else "evidence bundle returned"

    return {
        "question": question,
        "status": str(agent_result.get("status", "")),
        "task": str(agent_result.get("task", "")),
        "answer": summary,
        "claims": claims,
        "citations": pmids if isinstance(pmids, list) else [],
        "evidence_bundle": bundle,
        "limitations": [
            "L7 v1 is deterministic wrapper output; claim-level citation validation is pending.",
            f"L6 provider used: {provider}.",
        ],
    }
