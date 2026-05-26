from __future__ import annotations

import sqlite3
from typing import Dict, Tuple

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


def write_pipeline_outputs_with_relations_to_sqlite(
    papers_df: pd.DataFrame,
    entities_df: pd.DataFrame,
    relations_df: pd.DataFrame,
    db_path: str = DEFAULT_DB_PATH,
    task: str = "biored",
) -> Dict[str, int]:
    """
    Persist pipeline outputs including relation/provenance rows.

    This function keeps backward compatibility by building on the existing
    mention/sentence writer, then appending BioRED-style relations.
    """
    added_papers, added_mentions, added_normalized, added_sentences = (
        write_pipeline_outputs_to_sqlite(
            papers_df,
            entities_df,
            db_path=db_path,
            task=task,
        )
    )

    resolved_db_path = init_sqlite_schema(db_path)
    conn = sqlite3.connect(resolved_db_path)
    try:
        before_relations = conn.execute("SELECT COUNT(*) FROM entity_relations").fetchone()[0]
        before_provenance = conn.execute("SELECT COUNT(*) FROM relation_provenance").fetchone()[0]

        for _, row in relations_df.iterrows():
            relation_source = str(row.get("relation_source", "unknown_relation_source"))
            pmid = str(row.get("pmid", ""))
            relation_type = str(row.get("relation_type", ""))
            e1_norm = str(row.get("entity1_normalized_id", ""))
            e2_norm = str(row.get("entity2_normalized_id", ""))
            conn.execute(
                """
                INSERT OR IGNORE INTO entity_relations
                (
                    pmid, task, relation_type,
                    entity1_text, entity1_type, entity1_normalized_id,
                    entity2_text, entity2_type, entity2_normalized_id,
                    relation_source
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pmid,
                    task,
                    relation_type,
                    str(row.get("entity1_text", "")),
                    str(row.get("entity1_type", "")),
                    e1_norm,
                    str(row.get("entity2_text", "")),
                    str(row.get("entity2_type", "")),
                    e2_norm,
                    relation_source,
                ),
            )
            relation_row = conn.execute(
                """
                SELECT relation_id
                FROM entity_relations
                WHERE pmid = ? AND task = ? AND relation_type = ?
                  AND entity1_normalized_id = ? AND entity2_normalized_id = ?
                  AND relation_source = ?
                """,
                (pmid, task, relation_type, e1_norm, e2_norm, relation_source),
            ).fetchone()
            if not relation_row:
                continue
            relation_id = int(relation_row[0])
            conn.execute(
                """
                INSERT OR IGNORE INTO relation_provenance
                (
                    relation_id, evidence_sentence, novelty,
                    provenance_source, confidence
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    relation_id,
                    str(row.get("evidence_sentence", "")),
                    str(row.get("novelty", "")),
                    "biored_relation_v1",
                    float(row.get("confidence", 1.0)),
                ),
            )

        conn.commit()

        after_relations = conn.execute("SELECT COUNT(*) FROM entity_relations").fetchone()[0]
        after_provenance = conn.execute("SELECT COUNT(*) FROM relation_provenance").fetchone()[0]
    finally:
        conn.close()

    return {
        "papers_added": int(added_papers),
        "mentions_added": int(added_mentions),
        "normalized_entities_added": int(added_normalized),
        "evidence_sentences_added": int(added_sentences),
        "relations_added": int(after_relations - before_relations),
        "relation_provenance_added": int(after_provenance - before_provenance),
    }
