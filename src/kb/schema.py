from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = "data/processed/kb/biomed_kb.db"


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / "configs").is_dir() and (candidate / "src").is_dir():
            return candidate
    raise RuntimeError(f"Could not locate repo root from: {start}")


def _ensure_column(
    conn: sqlite3.Connection,
    *,
    table: str,
    column: str,
    definition: str,
) -> None:
    existing = {
        str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_sqlite_schema(db_path: str = DEFAULT_DB_PATH) -> str:
    """
    Create SQLite database file and minimal v1 tables if they do not exist.

    Returns the resolved database path string for logging/CLI output.
    """
    path = Path(db_path)
    if not path.is_absolute():
        repo_root = _find_repo_root(Path(__file__).parent)
        path = repo_root / path
    resolved = path.resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(resolved))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS papers (
                pmid TEXT PRIMARY KEY,
                title TEXT,
                year TEXT,
                journal TEXT,
                abstract TEXT
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entity_mentions (
                mention_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pmid TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_text TEXT NOT NULL,
                token_start INTEGER,
                token_end INTEGER,
                normalized_id TEXT,
                normalized_text TEXT,
                normalized_source TEXT,
                normalized_score REAL,
                UNIQUE(pmid, entity_type, entity_text, token_start, token_end)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS normalized_entities (
                normalized_id TEXT PRIMARY KEY,
                preferred_label TEXT,
                entity_type TEXT,
                source_vocab TEXT
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evidence_sentences (
                evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pmid TEXT NOT NULL,
                task TEXT NOT NULL,
                sentence_index INTEGER NOT NULL,
                sentence_text TEXT NOT NULL,
                source TEXT NOT NULL,
                UNIQUE(pmid, task, sentence_index),
                FOREIGN KEY(pmid) REFERENCES papers(pmid)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evidence_sentence_mentions (
                evidence_id INTEGER NOT NULL,
                mention_id INTEGER NOT NULL,
                PRIMARY KEY(evidence_id, mention_id),
                FOREIGN KEY(evidence_id) REFERENCES evidence_sentences(evidence_id),
                FOREIGN KEY(mention_id) REFERENCES entity_mentions(mention_id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entity_relations (
                relation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pmid TEXT NOT NULL,
                task TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                entity1_text TEXT,
                entity1_type TEXT,
                entity1_normalized_id TEXT,
                entity2_text TEXT,
                entity2_type TEXT,
                entity2_normalized_id TEXT,
                relation_source TEXT NOT NULL,
                UNIQUE(
                    pmid,
                    task,
                    relation_type,
                    entity1_normalized_id,
                    entity2_normalized_id,
                    relation_source
                ),
                FOREIGN KEY(pmid) REFERENCES papers(pmid)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relation_provenance (
                provenance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                relation_id INTEGER NOT NULL,
                evidence_id INTEGER,
                evidence_sentence TEXT,
                sentence_index INTEGER,
                novelty TEXT,
                link_method TEXT,
                char_start INTEGER,
                char_end INTEGER,
                provenance_source TEXT NOT NULL,
                confidence REAL,
                UNIQUE(relation_id, evidence_sentence, provenance_source),
                FOREIGN KEY(relation_id) REFERENCES entity_relations(relation_id)
            )
            """
        )
        _ensure_column(
            conn,
            table="relation_provenance",
            column="evidence_id",
            definition="INTEGER",
        )
        _ensure_column(
            conn,
            table="relation_provenance",
            column="sentence_index",
            definition="INTEGER",
        )
        _ensure_column(
            conn,
            table="relation_provenance",
            column="link_method",
            definition="TEXT",
        )
        _ensure_column(
            conn,
            table="relation_provenance",
            column="char_start",
            definition="INTEGER",
        )
        _ensure_column(
            conn,
            table="relation_provenance",
            column="char_end",
            definition="INTEGER",
        )

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_entity_mentions_pmid ON entity_mentions(pmid)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_entity_mentions_norm_id ON entity_mentions(normalized_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_entity_mentions_type ON entity_mentions(entity_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_evidence_sentences_pmid ON evidence_sentences(pmid)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_evidence_sentences_task ON evidence_sentences(task)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_entity_relations_pmid_task ON entity_relations(pmid, task)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_entity_relations_pair ON entity_relations(entity1_normalized_id, entity2_normalized_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_relation_provenance_relation_id ON relation_provenance(relation_id)"
        )
        conn.commit()
    finally:
        conn.close()

    return str(resolved)
