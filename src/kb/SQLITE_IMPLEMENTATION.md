# SQLite KB Implementation Steps

This document is the implementation checklist for adding the SQLite knowledge base layer after normalization.

## Goal

Persist the currently runnable BC5CDR/JNLPBA outputs into a local SQLite
database so results are queryable and reproducible. The primary BioRED task
requires an additional relation table and is described separately below.

## Phase 1: Minimal Vertical Slice (Original v1 Milestone)

1. Create one SQLite file path convention.
- Default: `data/processed/kb/biomed_kb.db`

2. Create minimal schema (3 tables).
- `papers`
- `entity_mentions`
- `normalized_entities`

3. Wire one write entrypoint from pipeline output.
- Input: `papers_df`, `entities_df` from existing task pipeline
- Behavior: append with idempotent upsert/ignore strategy

4. Add 3 read queries for validation.
- by `pmid`
- by `normalized_id`
- by `entity_type` + keyword

5. Add one CLI smoke command.
- Example target: `python -m pipelines.run_ingest_to_sqlite --task bc5cdr --query "cisplatin kidney diseases" --retmax 5`
- Query CLI target: `python -m pipelines.run_query_sqlite --mode pmid --pmid SMOKE001`

## Schema v1 (Original Minimal Schema)

### papers
- `pmid TEXT PRIMARY KEY`
- `title TEXT`
- `year TEXT`
- `journal TEXT`
- `abstract TEXT`

### entity_mentions
- `mention_id INTEGER PRIMARY KEY AUTOINCREMENT`
- `pmid TEXT NOT NULL`
- `entity_type TEXT NOT NULL`
- `entity_text TEXT NOT NULL`
- `token_start INTEGER`
- `token_end INTEGER`
- `normalized_id TEXT`
- `normalized_text TEXT`
- `normalized_source TEXT`
- `normalized_score REAL`

Recommended unique key:
- `UNIQUE(pmid, entity_type, entity_text, token_start, token_end)`

### normalized_entities
- `normalized_id TEXT PRIMARY KEY`
- `preferred_label TEXT`
- `entity_type TEXT`
- `source_vocab TEXT`

## File Plan

- `src/kb/schema.py`: create tables/indexes
- `src/kb/writer.py`: write `papers_df` + `entities_df` to SQLite
- `src/kb/query.py`: simple query helpers
- `pipelines/run_ingest_to_sqlite.py`: CLI entrypoint
- `pipelines/run_query_sqlite.py`: read/query CLI entrypoint
- `tests/unit/test_kb_sqlite.py`: schema/writer/query smoke tests

## Suggested Build Order

1. `schema.py` + unit test for table creation.
2. `writer.py` + unit test for upsert/idempotency.
3. `query.py` + unit test for 3 query shapes.
4. `run_ingest_to_sqlite.py` + end-to-end smoke on `--smoke`.

## Definition of Done (v1)

- Running pipeline + writer creates a queryable SQLite DB.
- Re-running the same query does not duplicate mention rows.
- You can fetch:
  - all normalized mentions for one PMID
  - all PMIDs for one normalized ID
  - all mentions for an entity type filter
- Unit tests pass for `src/kb` core functions.

## Sentence-Level Evidence Upgrade (L3 v1.1)

The original v1 schema stores entity mentions and normalized identifiers. This
upgrade adds the source-text evidence needed for later citation-grounded
responses.

New tables:

| Table | Purpose |
| --- | --- |
| `evidence_sentences` | Stores abstract sentences with `pmid`, `task`, sentence order, text, and source |
| `evidence_sentence_mentions` | Links each stored sentence to normalized mentions it contains |

Write flow:

```text
papers_df.abstract
  -> split_abstract_into_sentences(...)
  -> evidence_sentences

entities_df.entity_text + stored sentences
  -> surface-text link
  -> evidence_sentence_mentions
```

Implementation files:

- `src/kb/evidence.py`: deterministic sentence splitting and current
  surface-text linking rule
- `src/kb/schema.py`: new evidence tables and indexes
- `src/kb/writer.py`: sentence and link persistence
- `src/kb/query.py`: evidence retrieval by PMID or normalized ID

## BioRED Primary Relation Extension (Next)

`BioRED` is the primary target for gene/protein-disease evidence. Unlike the
two existing NER paths, it must retain curated or predicted relation records:

```text
papers_df + entities_df + relations_df
```

The existing SQLite tables remain useful for normalized mentions and selected
source sentences. Before BioRED can be exposed through L4/L5, add:

| Addition | Purpose |
| --- | --- |
| `entity_relations` table | Persist disease-gene relation pairs and relation source |
| Relation-to-sentence linkage | Record the application-selected supporting sentence |
| Relation query helpers | Retrieve gene-disease evidence with PMID provenance |

The current smoke contract is defined in `src/extraction/biored_pipeline.py`.

Current linking decision:

- use extracted mention text to identify the containing sentence
- defer precise character-span linking until extraction outputs preserve exact
  source character offsets

Full cross-layer upgrade record:

- `doc/sentence_level_evidence_upgrade.md`
