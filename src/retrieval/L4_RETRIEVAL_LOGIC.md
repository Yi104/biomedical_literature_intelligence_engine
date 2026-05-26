# L4 Retrieval Logic (SQLite-backed)

This document describes the current L4 retrieval layer implemented in `src/retrieval/sqlite_service.py`.

## Scope

L4 is responsible for deterministic retrieval from the SQLite knowledge base (`biomed_kb.db`).

- Input source: tables populated by L3 writer (`papers`, `entity_mentions`, `normalized_entities`)
- Output target: structured retrieval payload for L5 agent and L7 output layers

## Entry Point

- Service: `src/retrieval/sqlite_service.py`
- Public function: `query_kb(...)`

The service delegates SQL reads to `src/kb/query.py` and enforces one unified response contract.

## Supported Query Modes

1. `pmid`
- Required arg: `pmid`
- Behavior: returns mention rows for one PMID

2. `normalized_id`
- Required arg: `normalized_id`
- Behavior: returns distinct PMIDs linked to the normalized ID

3. `type_keyword`
- Required args: `entity_type`, `keyword`
- Behavior: case-insensitive keyword search over `entity_text` and `normalized_text`

## Unified Output Contract

All modes return:

```json
{
  "mode": "<pmid|normalized_id|type_keyword>",
  "filters": { "...": "..." },
  "count": 0,
  "results": []
}
```

Design intent:
- keep downstream handling mode-agnostic
- provide explicit filters for traceability
- include `count` for pagination/UX decisions

## CLI Mapping

CLI wrapper:
- `pipelines/run_query_sqlite.py`

Examples:

```bash
python -m pipelines.run_query_sqlite --mode pmid --pmid SMOKE001
python -m pipelines.run_query_sqlite --mode normalized_id --normalized_id HGNC:1100
python -m pipelines.run_query_sqlite --mode type_keyword --entity_type Gene --keyword brca
```

## Validation

Unit tests:
- `tests/unit/test_retrieval_sqlite_service.py`
- `tests/unit/test_kb_sqlite.py`

Smoke dependency:
- run ingestion first (for non-empty query results), e.g.
  - `python -m pipelines.run_ingest_to_sqlite --task bc5cdr --smoke`

## Current Constraints

- No pagination yet (`LIMIT/OFFSET` not exposed).
- No ranking score field yet.
- Query modes are fixed to three deterministic patterns.

## Next Step Candidates

1. Add pagination args (`limit`, `offset`) to `query_kb` and CLI.
2. Add optional lightweight ranking for `type_keyword` mode.
3. Add evidence sentence retrieval mode once sentence-level table is added.
