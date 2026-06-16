from __future__ import annotations

from typing import Any, Dict

from src.contracts.evidence_adapters import (
    build_unified_evidence_bundle_from_agent_result,
)
from src.kb.query import (
    find_mentions_by_type_and_keyword,
    get_evidence_sentences_by_normalized_id,
    get_evidence_sentences_by_pmid,
    get_mentions_by_pmid,
    get_pmids_by_normalized_id,
    get_relations_by_entity_pair,
    get_relations_by_pmid,
)
from src.kb.schema import DEFAULT_DB_PATH, init_sqlite_schema


def query_kb(
    mode: str,
    *,
    pmid: str | None = None,
    normalized_id: str | None = None,
    entity_type: str | None = None,
    keyword: str | None = None,
    entity1_normalized_id: str | None = None,
    entity2_normalized_id: str | None = None,
    task: str | None = None,
    db_path: str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    """
    Unified L4 retrieval service over SQLite KB.

    Returns a contract-stable payload:
    {
      "mode": <mode>,
      "filters": {...},
      "count": <int>,
      "results": <list>
    }
    """
    resolved_db_path = init_sqlite_schema(db_path)

    if mode == "pmid":
        if not pmid:
            raise ValueError("pmid is required when mode='pmid'")
        results = get_mentions_by_pmid(pmid, db_path=resolved_db_path)
        filters = {"pmid": pmid}
    elif mode == "normalized_id":
        if not normalized_id:
            raise ValueError("normalized_id is required when mode='normalized_id'")
        pmids = get_pmids_by_normalized_id(normalized_id, db_path=resolved_db_path)
        results = [{"pmid": p} for p in pmids]
        filters = {"normalized_id": normalized_id}
    elif mode == "type_keyword":
        if not entity_type or not keyword:
            raise ValueError("entity_type and keyword are required when mode='type_keyword'")
        results = find_mentions_by_type_and_keyword(
            entity_type, keyword, db_path=resolved_db_path
        )
        filters = {"entity_type": entity_type, "keyword": keyword}
    elif mode == "evidence_pmid":
        if not pmid:
            raise ValueError("pmid is required when mode='evidence_pmid'")
        results = get_evidence_sentences_by_pmid(pmid, task=task, db_path=resolved_db_path)
        filters = {"pmid": pmid}
        if task:
            filters["task"] = task
    elif mode == "evidence_normalized_id":
        if not normalized_id:
            raise ValueError(
                "normalized_id is required when mode='evidence_normalized_id'"
            )
        results = get_evidence_sentences_by_normalized_id(
            normalized_id, task=task, db_path=resolved_db_path
        )
        filters = {"normalized_id": normalized_id}
        if task:
            filters["task"] = task
    elif mode == "relation_pmid":
        if not pmid:
            raise ValueError("pmid is required when mode='relation_pmid'")
        results = get_relations_by_pmid(pmid, task=task, db_path=resolved_db_path)
        filters = {"pmid": pmid}
        if task:
            filters["task"] = task
    elif mode == "relation_entity_pair":
        if not entity1_normalized_id or not entity2_normalized_id:
            raise ValueError(
                "entity1_normalized_id and entity2_normalized_id are required when mode='relation_entity_pair'"
            )
        results = get_relations_by_entity_pair(
            entity1_normalized_id,
            entity2_normalized_id,
            task=task,
            db_path=resolved_db_path,
        )
        filters = {
            "entity1_normalized_id": entity1_normalized_id,
            "entity2_normalized_id": entity2_normalized_id,
        }
        if task:
            filters["task"] = task
    else:
        raise ValueError(
            "mode must be one of: pmid, normalized_id, type_keyword, "
            "evidence_pmid, evidence_normalized_id, relation_pmid, relation_entity_pair"
        )

    return {
        **build_unified_evidence_bundle_from_agent_result(
            "",
            {
                "status": "",
                "task": str(task or ""),
                "retrieval_mode": mode,
                "filters": filters,
                "count": len(results),
                "evidence": results,
            },
        ),
        "mode": mode,
        "filters": filters,
        "count": len(results),
        "results": results,
    }
