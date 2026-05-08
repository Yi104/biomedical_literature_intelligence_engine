from __future__ import annotations

from typing import Any, Dict

from src.kb.query import (
    find_mentions_by_type_and_keyword,
    get_mentions_by_pmid,
    get_pmids_by_normalized_id,
)
from src.kb.schema import DEFAULT_DB_PATH, init_sqlite_schema


def query_kb(
    mode: str,
    *,
    pmid: str | None = None,
    normalized_id: str | None = None,
    entity_type: str | None = None,
    keyword: str | None = None,
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
    else:
        raise ValueError("mode must be one of: pmid, normalized_id, type_keyword")

    return {
        "mode": mode,
        "filters": filters,
        "count": len(results),
        "results": results,
    }

