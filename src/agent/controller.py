from __future__ import annotations

from typing import Any, Callable, Dict, Tuple

import pandas as pd

from src.kb.schema import DEFAULT_DB_PATH
from src.kb.writer import write_pipeline_outputs_to_sqlite
from src.retrieval.sqlite_service import query_kb
from src.retrieval.task_router import run_task

RefreshRunner = Callable[..., Tuple[pd.DataFrame, pd.DataFrame]]

SUPPORTED_TASKS = {"bc5cdr", "jnlpba"}
SUPPORTED_RETRIEVAL_MODES = {"pmid", "normalized_id", "type_keyword"}


def _validate_request(
    task: str,
    retrieval_mode: str,
    *,
    pmid: str | None,
    normalized_id: str | None,
    entity_type: str | None,
    keyword: str | None,
    search_query: str | None,
    allow_refresh: bool,
) -> Tuple[str, str]:
    """Validate inputs before any task pipeline is allowed to run."""
    resolved_task = task.lower().strip()
    if resolved_task not in SUPPORTED_TASKS:
        raise ValueError("task must be one of: bc5cdr, jnlpba")

    resolved_mode = retrieval_mode.lower().strip()
    if resolved_mode not in SUPPORTED_RETRIEVAL_MODES:
        raise ValueError("retrieval_mode must be one of: pmid, normalized_id, type_keyword")

    if resolved_mode == "pmid" and not pmid:
        raise ValueError("pmid is required when retrieval_mode='pmid'")
    if resolved_mode == "normalized_id" and not normalized_id:
        raise ValueError("normalized_id is required when retrieval_mode='normalized_id'")
    if resolved_mode == "type_keyword" and (not entity_type or not keyword):
        raise ValueError(
            "entity_type and keyword are required when retrieval_mode='type_keyword'"
        )

    # In v1, refresh is an explicit operation, not a guess based on an empty lookup.
    if allow_refresh and not search_query:
        raise ValueError("search_query is required when allow_refresh=True")

    return resolved_task, resolved_mode


def _filters_for_request(
    retrieval_mode: str,
    *,
    pmid: str | None,
    normalized_id: str | None,
    entity_type: str | None,
    keyword: str | None,
) -> Dict[str, str]:
    """Build response filters for failure paths where L4 is not reached."""
    if retrieval_mode == "pmid":
        return {"pmid": str(pmid)}
    if retrieval_mode == "normalized_id":
        return {"normalized_id": str(normalized_id)}
    return {"entity_type": str(entity_type), "keyword": str(keyword)}


def _default_refresh_runner(
    task: str,
    *,
    search_query: str,
    retmax: int,
    max_length: int,
    model_path: str | None,
    smoke: bool,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Run an existing extraction/normalization task without duplicating task logic."""
    pipeline_args: Dict[str, Any] = {
        "query": search_query,
        "retmax": retmax,
        "max_length": max_length,
        "smoke": smoke,
    }
    if model_path is not None:
        pipeline_args["model_path"] = model_path
    return run_task(task, **pipeline_args)


def run_agent_controller(
    *,
    task: str,
    retrieval_mode: str,
    pmid: str | None = None,
    normalized_id: str | None = None,
    entity_type: str | None = None,
    keyword: str | None = None,
    search_query: str | None = None,
    retmax: int = 5,
    max_length: int = 256,
    model_path: str | None = None,
    allow_refresh: bool = False,
    smoke: bool = False,
    db_path: str = DEFAULT_DB_PATH,
    refresh_runner: RefreshRunner | None = None,
) -> Dict[str, Any]:
    """
    Execute the deterministic L5 v1 decision flow.

    - Query-only requests call L4 without modifying the knowledge base.
    - Refresh-authorized requests explicitly run L0-L3 first, then call L4.
    - L5 returns evidence records; it does not produce biomedical conclusions.
    """
    resolved_task, resolved_mode = _validate_request(
        task,
        retrieval_mode,
        pmid=pmid,
        normalized_id=normalized_id,
        entity_type=entity_type,
        keyword=keyword,
        search_query=search_query,
        allow_refresh=allow_refresh,
    )

    refresh_summary = None
    if allow_refresh:
        runner = refresh_runner or _default_refresh_runner
        try:
            papers_df, entities_df = runner(
                resolved_task,
                search_query=str(search_query),
                retmax=retmax,
                max_length=max_length,
                model_path=model_path,
                smoke=smoke,
            )
            added_papers, added_mentions, added_normalized = (
                write_pipeline_outputs_to_sqlite(papers_df, entities_df, db_path=db_path)
            )
            refresh_summary = {
                "search_query": search_query,
                "papers_added": added_papers,
                "mentions_added": added_mentions,
                "normalized_entities_added": added_normalized,
            }
        except Exception as exc:
            return {
                "status": "refresh_failed",
                "task": resolved_task,
                "retrieval_mode": resolved_mode,
                "filters": _filters_for_request(
                    resolved_mode,
                    pmid=pmid,
                    normalized_id=normalized_id,
                    entity_type=entity_type,
                    keyword=keyword,
                ),
                "refreshed": False,
                "count": 0,
                "evidence": [],
                "refresh": None,
                "message": str(exc),
            }

    retrieval = query_kb(
        mode=resolved_mode,
        pmid=pmid,
        normalized_id=normalized_id,
        entity_type=entity_type,
        keyword=keyword,
        db_path=db_path,
    )
    if allow_refresh:
        status = "refreshed_and_found" if retrieval["count"] else "refreshed_no_evidence"
    else:
        status = "evidence_found" if retrieval["count"] else "insufficient_evidence"

    return {
        "status": status,
        "task": resolved_task,
        "retrieval_mode": retrieval["mode"],
        "filters": retrieval["filters"],
        "refreshed": allow_refresh,
        "count": retrieval["count"],
        "evidence": retrieval["results"],
        "refresh": refresh_summary,
        "message": None,
    }
