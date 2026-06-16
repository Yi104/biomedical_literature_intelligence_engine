from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Tuple

import pandas as pd

from src.contracts.evidence_adapters import (
    build_unified_evidence_bundle_from_agent_result,
)
from src.kb.schema import DEFAULT_DB_PATH
from src.kb.writer import (
    write_pipeline_outputs_to_sqlite,
    write_pipeline_outputs_with_relations_to_sqlite,
)
from src.retrieval.sqlite_service import query_kb
from src.retrieval.task_router import run_task

logger = logging.getLogger(__name__)

RefreshRunner = Callable[..., Tuple[pd.DataFrame, ...]]

SUPPORTED_TASKS = {"bc5cdr", "jnlpba", "biored"}
SUPPORTED_RETRIEVAL_MODES = {
    "pmid",
    "normalized_id",
    "type_keyword",
    "evidence_pmid",
    "evidence_normalized_id",
    "relation_pmid",
    "relation_entity_pair",
}


def _validate_request(
    task: str,
    retrieval_mode: str,
    *,
    pmid: str | None,
    normalized_id: str | None,
    entity_type: str | None,
    keyword: str | None,
    entity1_normalized_id: str | None,
    entity2_normalized_id: str | None,
    search_query: str | None,
    allow_refresh: bool,
) -> Tuple[str, str]:
    """Validate inputs before any task pipeline is allowed to run."""
    resolved_task = task.lower().strip()
    if resolved_task not in SUPPORTED_TASKS:
        raise ValueError("task must be one of: bc5cdr, jnlpba, biored")

    resolved_mode = retrieval_mode.lower().strip()
    if resolved_mode not in SUPPORTED_RETRIEVAL_MODES:
        raise ValueError(
            "retrieval_mode must be one of: pmid, normalized_id, type_keyword, "
            "evidence_pmid, evidence_normalized_id, relation_pmid, relation_entity_pair"
        )

    if resolved_mode in {"pmid", "evidence_pmid"} and not pmid:
        raise ValueError("pmid is required for PMID retrieval modes")
    if resolved_mode in {"normalized_id", "evidence_normalized_id"} and not normalized_id:
        raise ValueError("normalized_id is required for normalized-ID retrieval modes")
    if resolved_mode == "type_keyword" and (not entity_type or not keyword):
        raise ValueError(
            "entity_type and keyword are required when retrieval_mode='type_keyword'"
        )
    if resolved_mode == "relation_entity_pair" and (
        not entity1_normalized_id or not entity2_normalized_id
    ):
        raise ValueError(
            "entity1_normalized_id and entity2_normalized_id are required when retrieval_mode='relation_entity_pair'"
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
    entity1_normalized_id: str | None,
    entity2_normalized_id: str | None,
) -> Dict[str, str]:
    """Build response filters for failure paths where L4 is not reached."""
    if retrieval_mode in {"pmid", "evidence_pmid", "relation_pmid"}:
        return {"pmid": str(pmid)}
    if retrieval_mode in {"normalized_id", "evidence_normalized_id"}:
        return {"normalized_id": str(normalized_id)}
    if retrieval_mode == "relation_entity_pair":
        return {
            "entity1_normalized_id": str(entity1_normalized_id),
            "entity2_normalized_id": str(entity2_normalized_id),
        }
    return {"entity_type": str(entity_type), "keyword": str(keyword)}


def _default_refresh_runner(
    task: str,
    *,
    search_query: str,
    retmax: int,
    max_length: int,
    model_path: str | None,
    smoke: bool,
    data_path: str | None,
    relation_mode: str,
    confidence_threshold: float,
) -> Tuple[pd.DataFrame, ...]:
    """Run an existing extraction/normalization task without duplicating task logic."""
    pipeline_args: Dict[str, Any] = {
        "query": search_query,
        "retmax": retmax,
        "max_length": max_length,
        "smoke": smoke,
    }
    if task == "biored":
        pipeline_args["relation_mode"] = relation_mode
        pipeline_args["confidence_threshold"] = confidence_threshold
        if model_path is not None:
            pipeline_args["relation_model_path"] = model_path
    elif model_path is not None:
        pipeline_args["model_path"] = model_path
    if data_path is not None:
        pipeline_args["data_path"] = data_path
    logger.info(
        "L5 refresh runner start: task=%s relation_mode=%s retmax=%d smoke=%s data_path=%s",
        task,
        relation_mode,
        retmax,
        smoke,
        data_path,
    )
    return run_task(task, **pipeline_args)


def _empty_unified_payload(
    *,
    task: str,
    retrieval_mode: str,
    filters: Dict[str, str],
    status: str,
) -> Dict[str, Any]:
    bundle = build_unified_evidence_bundle_from_agent_result(
        "",
        {
            "status": status,
            "task": task,
            "retrieval_mode": retrieval_mode,
            "filters": filters,
            "count": 0,
            "evidence": [],
        },
    )
    return {
        "schema_version": bundle["schema_version"],
        "documents": bundle["documents"],
        "entities": bundle["entities"],
        "relations": bundle["relations"],
        "evidence_records": bundle["evidence"],
        "provenance": bundle["provenance"],
        "bundle": bundle,
    }


def run_agent_controller(
    *,
    task: str,
    retrieval_mode: str,
    pmid: str | None = None,
    normalized_id: str | None = None,
    entity_type: str | None = None,
    keyword: str | None = None,
    entity1_normalized_id: str | None = None,
    entity2_normalized_id: str | None = None,
    search_query: str | None = None,
    retmax: int = 5,
    max_length: int = 256,
    model_path: str | None = None,
    allow_refresh: bool = False,
    smoke: bool = False,
    data_path: str | None = None,
    relation_mode: str = "gold",
    confidence_threshold: float = 0.5,
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
        entity1_normalized_id=entity1_normalized_id,
        entity2_normalized_id=entity2_normalized_id,
        search_query=search_query,
        allow_refresh=allow_refresh,
    )

    refresh_summary = None
    if allow_refresh:
        runner = refresh_runner or _default_refresh_runner
        try:
            logger.info(
                "L5 refresh requested: task=%s retrieval_mode=%s relation_mode=%s",
                resolved_task,
                resolved_mode,
                relation_mode,
            )
            runner_output = runner(
                resolved_task,
                search_query=str(search_query),
                retmax=retmax,
                max_length=max_length,
                model_path=model_path,
                smoke=smoke,
                data_path=data_path,
                relation_mode=relation_mode,
                confidence_threshold=confidence_threshold,
            )
            if resolved_task == "biored":
                papers_df, entities_df, relations_df = runner_output
                logger.info(
                    "L5 refresh produced BioRED tables: papers=%d entities=%d relations=%d",
                    len(papers_df),
                    len(entities_df),
                    len(relations_df),
                )
                refresh_summary = write_pipeline_outputs_with_relations_to_sqlite(
                    papers_df,
                    entities_df,
                    relations_df,
                    db_path=db_path,
                    task=resolved_task,
                )
                refresh_summary["search_query"] = search_query
            else:
                papers_df, entities_df = runner_output
                added_papers, added_mentions, added_normalized, added_sentences = (
                    write_pipeline_outputs_to_sqlite(
                        papers_df, entities_df, db_path=db_path, task=resolved_task
                    )
                )
                refresh_summary = {
                    "search_query": search_query,
                    "papers_added": added_papers,
                    "mentions_added": added_mentions,
                    "normalized_entities_added": added_normalized,
                    "evidence_sentences_added": added_sentences,
                }
        except Exception as exc:
            logger.exception("L5 refresh failed: task=%s retrieval_mode=%s", resolved_task, resolved_mode)
            filters = _filters_for_request(
                resolved_mode,
                pmid=pmid,
                normalized_id=normalized_id,
                entity_type=entity_type,
                keyword=keyword,
                entity1_normalized_id=entity1_normalized_id,
                entity2_normalized_id=entity2_normalized_id,
            )
            return {
                **_empty_unified_payload(
                    task=resolved_task,
                    retrieval_mode=resolved_mode,
                    filters=filters,
                    status="refresh_failed",
                ),
                "status": "refresh_failed",
                "task": resolved_task,
                "retrieval_mode": resolved_mode,
                "filters": filters,
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
        entity1_normalized_id=entity1_normalized_id,
        entity2_normalized_id=entity2_normalized_id,
        task=resolved_task
        if (resolved_mode.startswith("evidence_") or resolved_mode.startswith("relation_"))
        else None,
        db_path=db_path,
    )
    if allow_refresh:
        status = "refreshed_and_found" if retrieval["count"] else "refreshed_no_evidence"
    else:
        status = "evidence_found" if retrieval["count"] else "insufficient_evidence"
    logger.info(
        "L5 retrieval complete: task=%s retrieval_mode=%s status=%s count=%d refreshed=%s",
        resolved_task,
        retrieval["mode"],
        status,
        retrieval["count"],
        allow_refresh,
    )
    bundle = build_unified_evidence_bundle_from_agent_result(
        "",
        {
            "status": status,
            "task": resolved_task,
            "retrieval_mode": retrieval["mode"],
            "filters": retrieval["filters"],
            "count": retrieval["count"],
            "evidence": retrieval["results"],
        },
    )

    return {
        "schema_version": bundle["schema_version"],
        "status": status,
        "task": resolved_task,
        "retrieval_mode": retrieval["mode"],
        "filters": retrieval["filters"],
        "refreshed": allow_refresh,
        "count": retrieval["count"],
        "evidence": retrieval["results"],
        "documents": bundle["documents"],
        "entities": bundle["entities"],
        "relations": bundle["relations"],
        "evidence_records": bundle["evidence"],
        "provenance": bundle["provenance"],
        "bundle": bundle,
        "refresh": refresh_summary,
        "message": None,
    }
