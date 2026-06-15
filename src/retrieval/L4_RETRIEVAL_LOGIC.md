# L4 Retrieval Logic (SQLite-backed)

This document describes the current L4 retrieval layer implemented in `src/retrieval/sqlite_service.py`.

## Scope

L4 is responsible for deterministic retrieval from the SQLite knowledge base (`biomed_kb.db`).

- Input source: tables populated by L3 writer (`papers`, `entity_mentions`,
  `normalized_entities`, `evidence_sentences`, `evidence_sentence_mentions`,
  `entity_relations`, `relation_provenance`)
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

4. `evidence_pmid`
- Required arg: `pmid`
- Optional arg: `task`
- Behavior: returns source sentences for one PMID with linked normalized mentions

5. `evidence_normalized_id`
- Required arg: `normalized_id`
- Optional arg: `task`
- Behavior: returns source sentences containing a linked normalized entity

6. `relation_pmid`
- Required arg: `pmid`
- Optional arg: `task`
- Behavior: returns BioRED relation rows for one PMID with provenance records

7. `relation_entity_pair`
- Required args: `entity1_normalized_id`, `entity2_normalized_id`
- Optional arg: `task`
- Behavior: returns BioRED relation rows for one normalized entity pair

## Unified Output Contract

All modes return:

```json
{
  "mode": "<pmid|normalized_id|type_keyword|evidence_pmid|evidence_normalized_id|relation_pmid|relation_entity_pair>",
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
python -m pipelines.run_query_sqlite --mode normalized_id --normalized_id CHEBI:27899
python -m pipelines.run_query_sqlite --mode type_keyword --entity_type Chemical --keyword cisplatin
python -m pipelines.run_query_sqlite --mode evidence_pmid --pmid SMOKE001 --task bc5cdr
python -m pipelines.run_query_sqlite --mode evidence_normalized_id --normalized_id CHEBI:27899 --task bc5cdr
python -m pipelines.run_query_sqlite --mode relation_pmid --pmid SMOKE-BIORED-001 --task biored
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
- Sentence linking currently uses extracted surface-text occurrence, pending
  exact character offsets from extraction output.

## Sentence-Level Evidence Upgrade (L4 v1.1)

L4 now exposes stored source sentences without replacing the existing
mention-level query modes. Evidence queries return:

```python
{
    "pmid": "SMOKE001",
    "task": "bc5cdr",
    "sentence_text": "Cisplatin is associated with kidney diseases.",
    "entities": [
        {"entity_text": "Cisplatin", "normalized_id": "CHEBI:27899"}
    ]
}
```

This is the retrieval input required for citation-bound L6 answers. It is
implemented as an explicit mode so older consumers can continue requesting
mention rows or PMID lists.

Full cross-layer upgrade record:

- `doc/sentence_level_evidence_upgrade.md`

## Next Step Candidates

1. Add pagination args (`limit`, `offset`) to `query_kb` and CLI.
2. Add optional lightweight ranking for `type_keyword` mode.
3. Add ingestion provenance and character-offset evidence linking.
