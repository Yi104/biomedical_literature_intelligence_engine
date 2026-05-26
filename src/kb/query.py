from __future__ import annotations

import sqlite3
from typing import List, Dict

from src.kb.schema import DEFAULT_DB_PATH, init_sqlite_schema


def _rows_to_dicts(cursor: sqlite3.Cursor) -> List[Dict]:
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def get_mentions_by_pmid(pmid: str, db_path: str = DEFAULT_DB_PATH) -> List[Dict]:
    resolved_db_path = init_sqlite_schema(db_path)
    conn = sqlite3.connect(resolved_db_path)
    try:
        cur = conn.execute(
            """
            SELECT pmid, entity_type, entity_text, token_start, token_end,
                   normalized_id, normalized_text, normalized_source, normalized_score
            FROM entity_mentions
            WHERE pmid = ?
            ORDER BY token_start, token_end
            """,
            (pmid,),
        )
        return _rows_to_dicts(cur)
    finally:
        conn.close()


def get_pmids_by_normalized_id(normalized_id: str, db_path: str = DEFAULT_DB_PATH) -> List[str]:
    resolved_db_path = init_sqlite_schema(db_path)
    conn = sqlite3.connect(resolved_db_path)
    try:
        cur = conn.execute(
            """
            SELECT DISTINCT pmid
            FROM entity_mentions
            WHERE normalized_id = ?
            ORDER BY pmid
            """,
            (normalized_id,),
        )
        return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


def find_mentions_by_type_and_keyword(
    entity_type: str,
    keyword: str,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict]:
    resolved_db_path = init_sqlite_schema(db_path)
    conn = sqlite3.connect(resolved_db_path)
    try:
        cur = conn.execute(
            """
            SELECT pmid, entity_type, entity_text, normalized_id, normalized_text
            FROM entity_mentions
            WHERE lower(entity_type) = lower(?)
              AND (
                    lower(entity_text) LIKE '%' || lower(?) || '%'
                 OR lower(normalized_text) LIKE '%' || lower(?) || '%'
              )
            ORDER BY pmid
            """,
            (entity_type, keyword, keyword),
        )
        return _rows_to_dicts(cur)
    finally:
        conn.close()


def _get_sentence_entities(conn: sqlite3.Connection, evidence_id: int) -> List[Dict]:
    cur = conn.execute(
        """
        SELECT em.entity_type, em.entity_text, em.normalized_id, em.normalized_text,
               em.normalized_source, em.normalized_score
        FROM entity_mentions em
        JOIN evidence_sentence_mentions esm ON esm.mention_id = em.mention_id
        WHERE esm.evidence_id = ?
        ORDER BY em.token_start, em.token_end
        """,
        (evidence_id,),
    )
    return _rows_to_dicts(cur)


def get_evidence_sentences_by_pmid(
    pmid: str,
    *,
    task: str | None = None,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict]:
    """Return sentence evidence and linked normalized mentions for one paper."""
    resolved_db_path = init_sqlite_schema(db_path)
    conn = sqlite3.connect(resolved_db_path)
    try:
        params: tuple[str, ...]
        where = "WHERE es.pmid = ?"
        params = (pmid,)
        if task:
            where += " AND es.task = ?"
            params = (pmid, task)
        cur = conn.execute(
            f"""
            SELECT es.evidence_id, es.pmid, es.task, es.sentence_index,
                   es.sentence_text, es.source
            FROM evidence_sentences es
            {where}
            ORDER BY es.task, es.sentence_index
            """,
            params,
        )
        results = _rows_to_dicts(cur)
        for result in results:
            result["entities"] = _get_sentence_entities(conn, result["evidence_id"])
        return results
    finally:
        conn.close()


def get_evidence_sentences_by_normalized_id(
    normalized_id: str,
    *,
    task: str | None = None,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict]:
    """Return sentences linked to a specified canonical entity identifier."""
    resolved_db_path = init_sqlite_schema(db_path)
    conn = sqlite3.connect(resolved_db_path)
    try:
        params: tuple[str, ...]
        task_filter = ""
        params = (normalized_id,)
        if task:
            task_filter = " AND es.task = ?"
            params = (normalized_id, task)
        cur = conn.execute(
            f"""
            SELECT DISTINCT es.evidence_id, es.pmid, es.task, es.sentence_index,
                   es.sentence_text, es.source
            FROM evidence_sentences es
            JOIN evidence_sentence_mentions esm ON esm.evidence_id = es.evidence_id
            JOIN entity_mentions em ON em.mention_id = esm.mention_id
            WHERE em.normalized_id = ?{task_filter}
            ORDER BY es.pmid, es.task, es.sentence_index
            """,
            params,
        )
        results = _rows_to_dicts(cur)
        for result in results:
            result["entities"] = _get_sentence_entities(conn, result["evidence_id"])
        return results
    finally:
        conn.close()
