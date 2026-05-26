from __future__ import annotations

import sqlite3
from typing import Tuple

import pandas as pd

from src.kb.evidence import mention_appears_in_sentence, split_abstract_into_sentences
from src.kb.schema import DEFAULT_DB_PATH, init_sqlite_schema


def write_pipeline_outputs_to_sqlite(
    papers_df: pd.DataFrame,
    entities_df: pd.DataFrame,
    db_path: str = DEFAULT_DB_PATH,
    task: str = "unknown",
) -> Tuple[int, int, int, int]:
    """
    Persist pipeline outputs into SQLite with idempotent insert behavior.

    Returns:
    - inserted_papers
    - inserted_mentions
    - inserted_normalized_entities
    - inserted_evidence_sentences
    """
    resolved_db_path = init_sqlite_schema(db_path)
    conn = sqlite3.connect(resolved_db_path)
    try:
        before_papers = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        before_mentions = conn.execute("SELECT COUNT(*) FROM entity_mentions").fetchone()[0]
        before_norm = conn.execute("SELECT COUNT(*) FROM normalized_entities").fetchone()[0]
        before_sentences = conn.execute("SELECT COUNT(*) FROM evidence_sentences").fetchone()[0]

        for _, row in papers_df.iterrows():
            pmid = str(row.get("pmid", ""))
            abstract = str(row.get("abstract", ""))
            conn.execute(
                """
                INSERT OR IGNORE INTO papers (pmid, title, year, journal, abstract)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    pmid,
                    str(row.get("title", "")),
                    str(row.get("year", "")),
                    str(row.get("journal", "")),
                    abstract,
                ),
            )
            for sentence_index, sentence_text in enumerate(
                split_abstract_into_sentences(abstract)
            ):
                conn.execute(
                    """
                    INSERT OR IGNORE INTO evidence_sentences
                    (pmid, task, sentence_index, sentence_text, source)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (pmid, task, sentence_index, sentence_text, "pubmed_abstract"),
                )

        for _, row in entities_df.iterrows():
            normalized_id = str(row.get("normalized_id", "UNRESOLVED"))
            normalized_text = str(row.get("normalized_text", ""))
            entity_type = str(row.get("entity_type", ""))
            if normalized_id and normalized_id != "UNRESOLVED":
                conn.execute(
                    """
                    INSERT OR IGNORE INTO normalized_entities
                    (normalized_id, preferred_label, entity_type, source_vocab)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        normalized_id,
                        normalized_text,
                        entity_type,
                        "rule_based_v1",
                    ),
                )

            conn.execute(
                """
                INSERT OR IGNORE INTO entity_mentions
                (
                    pmid, entity_type, entity_text, token_start, token_end,
                    normalized_id, normalized_text, normalized_source, normalized_score
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(row.get("pmid", "")),
                    entity_type,
                    str(row.get("entity_text", "")),
                    int(row.get("token_start", -1)),
                    int(row.get("token_end", -1)),
                    normalized_id,
                    normalized_text,
                    str(row.get("normalized_source", "")),
                    float(row.get("normalized_score", 0.0)),
                ),
            )

        # Link each stored mention to source sentences containing its extracted
        # surface form. Char-offset linking can replace this once extraction
        # outputs expose exact source-text offsets.
        for _, row in entities_df.iterrows():
            pmid = str(row.get("pmid", ""))
            entity_type = str(row.get("entity_type", ""))
            entity_text = str(row.get("entity_text", ""))
            token_start = int(row.get("token_start", -1))
            token_end = int(row.get("token_end", -1))
            mention_row = conn.execute(
                """
                SELECT mention_id
                FROM entity_mentions
                WHERE pmid = ? AND entity_type = ? AND entity_text = ?
                  AND token_start = ? AND token_end = ?
                """,
                (pmid, entity_type, entity_text, token_start, token_end),
            ).fetchone()
            if not mention_row:
                continue
            mention_id = mention_row[0]
            sentences = conn.execute(
                """
                SELECT evidence_id, sentence_text
                FROM evidence_sentences
                WHERE pmid = ? AND task = ?
                """,
                (pmid, task),
            ).fetchall()
            for evidence_id, sentence_text in sentences:
                if mention_appears_in_sentence(entity_text, sentence_text):
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO evidence_sentence_mentions
                        (evidence_id, mention_id)
                        VALUES (?, ?)
                        """,
                        (evidence_id, mention_id),
                    )

        conn.commit()

        after_papers = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        after_mentions = conn.execute("SELECT COUNT(*) FROM entity_mentions").fetchone()[0]
        after_norm = conn.execute("SELECT COUNT(*) FROM normalized_entities").fetchone()[0]
        after_sentences = conn.execute("SELECT COUNT(*) FROM evidence_sentences").fetchone()[0]
    finally:
        conn.close()

    return (
        int(after_papers - before_papers),
        int(after_mentions - before_mentions),
        int(after_norm - before_norm),
        int(after_sentences - before_sentences),
    )
