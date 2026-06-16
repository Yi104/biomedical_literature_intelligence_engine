# Evidence Schema Refactor Plan

## Goal

Refactor the repository toward a unified evidence-layer contract without
discarding the current SQLite-first implementation.

Target outcome:

- one stable evidence bundle contract
- backend-agnostic extraction adapters
- cleaner separation between raw extraction, evidence grounding, and
  downstream answer generation

This plan is intentionally file-level and scoped to the current codebase.

## Current State Summary

The repository already has:

- task-specific extraction outputs
- SQLite persistence
- retrieval modes
- L6 evidence bundle construction
- L7 answer wrapping

What is missing is the contract unification layer:

- `Entity`, `Relation`, `Evidence`, `Provenance`
- stable adapter from current tables to that object model
- evidence scoring abstraction
- stronger provenance semantics

## Phase 1: Define the Contract in Code

Objective:

- make the unified evidence schema importable, not just documented

Primary files:

- new: `src/contracts/unified_evidence_schema.py`
- update: `src/contracts/__init__.py`

Tasks:

1. Add typed structures for:
   - `DocumentRecord`
   - `EntityRecord`
   - `RelationRecord`
   - `EvidenceRecord`
   - `ProvenanceRecord`
   - `EvidenceBundleV1`
2. Keep fields aligned with [unified_evidence_schema.md](unified_evidence_schema.md).
3. Do not replace existing dataframe column constants yet.

Recommended implementation:

- use `TypedDict` first for low-friction adoption
- keep a top-level `SCHEMA_VERSION = "evidence-v1"`

Why this phase first:

- downstream adapters and tests need one canonical import target

## Phase 2: Build Adapters from Current Storage and Task Outputs

Objective:

- convert current outputs into unified evidence objects without breaking
  existing CLI behavior

Primary files:

- new: `src/contracts/evidence_adapters.py`
- update: `src/llm/evidence_bundle.py`
- update: `src/output/l7_answer.py`

Tasks:

1. Add adapter functions:
   - `entity_row_to_entity_record(...)`
   - `relation_row_to_relation_record(...)`
   - `sentence_row_to_evidence_record(...)`
   - `provenance_row_to_provenance_record(...)`
2. Add one bundle constructor:
   - `build_unified_evidence_bundle_from_agent_result(...)`
3. Keep the current L6 return shape compatible, but make `records` internally
   derive from the unified objects.
4. Update L7 to read from unified bundle fields instead of flattened ad hoc
   row logic.

Why:

- this is the lowest-risk way to introduce the new contract

## Phase 3: Make Retrieval Return Schema-Oriented Objects

Objective:

- reduce flattening logic in upper layers

Primary files:

- update: `src/retrieval/sqlite_service.py`
- update: `src/kb/query.py`
- update: `src/agent/controller.py`

Tasks:

1. Keep current retrieval modes:
   - `pmid`
   - `normalized_id`
   - `type_keyword`
   - `evidence_pmid`
   - `evidence_normalized_id`
   - `relation_pmid`
   - `relation_entity_pair`
2. Change return internals so each mode can produce:
   - raw rows if needed for backward compatibility
   - unified object lists for downstream use
3. Add explicit payload sections where appropriate:
   - `documents`
   - `entities`
   - `relations`
   - `evidence`
   - `provenance`

Recommended approach:

- preserve existing top-level status keys
- add a `schema_version`
- add a `bundle` or `evidence_bundle` object instead of replacing everything at once

Why:

- retrieval is the real boundary between persistence and downstream systems

## Phase 4: Strengthen Provenance Semantics

Objective:

- move from string-only provenance toward auditable grounding

Primary files:

- update: `src/kb/schema.py`
- update: `src/kb/writer.py`
- update: `src/kb/evidence.py`
- update: `src/extraction/biored_loader.py`
- update: `src/extraction/biored_relation_infer.py`

Tasks:

1. Extend provenance representation to include:
   - `sentence_index`
   - linking `method`
   - optional `char_start`
   - optional `char_end`
2. Improve mention-to-sentence linkage:
   - current: surface-form matching
   - next: deterministic sentence index where available
   - later: char offsets from extraction outputs
3. Distinguish:
   - evidence text
   - provenance method
   - provenance source system

Suggested schema changes:

- `relation_provenance`:
  - add `sentence_index`
  - add `link_method`
  - add `char_start`
  - add `char_end`
- possibly add `evidence_id` linkage for relations

Why:

- provenance quality is one of the major current gaps documented by the repo

## Phase 5: Introduce Evidence Scoring V1

Objective:

- create a reusable ranking field for downstream retrieval and QA

Primary files:

- new: `src/scoring/evidence_scoring.py`
- update: `src/retrieval/sqlite_service.py`
- update: `src/llm/evidence_bundle.py`

Tasks:

1. Define a simple scoring function:
   - relation confidence
   - normalization quality
   - sentence support quality
2. Emit:
   - `evidence_rank_score`
3. Keep the scoring logic deterministic and transparent in V1.

Initial formula suggestion:

```text
evidence_rank_score =
  0.6 * relation_confidence +
  0.2 * subject_normalization_score +
  0.2 * object_normalization_score
```

Fallback if normalization score missing:

- use a reduced formula with available terms

Why:

- this gives the platform a real evidence-layer ranking primitive without
  introducing premature model complexity

## Phase 6: Align Task Contracts to the Unified Layer

Objective:

- reduce fragmentation between dataframe contracts and downstream bundle shape

Primary files:

- update: `src/contracts/task_output_schemas.py`
- update: `src/extraction/biored_pipeline.py`
- update: `src/extraction/bc5cdr_pipeline.py`
- update: `src/extraction/jnlpba_pipeline.py`

Tasks:

1. Keep existing dataframe contracts for training and persistence.
2. Add explicit documentation that these are extraction-layer contracts, not
   final evidence-layer contracts.
3. Provide adapter entrypoints from task output tables to unified objects.

Why:

- extraction outputs and evidence-layer outputs serve different purposes

## Phase 7: Test Coverage

Objective:

- ensure the migration is safe and observable

Primary files:

- new: `tests/unit/test_unified_evidence_schema.py`
- new: `tests/unit/test_evidence_adapters.py`
- update: `tests/unit/test_llm_evidence_bundle.py`
- update: `tests/unit/test_l7_answer.py`
- update: `tests/unit/test_kb_sqlite.py`
- update: `tests/unit/test_retrieval_sqlite_service.py`

Tests to add:

1. schema object validation for required fields
2. adapter roundtrip from current relation query results
3. provenance object emission with nullable offsets
4. evidence score emission and sorting
5. backward compatibility of current L6/L7 outputs

## Recommended Implementation Order

Do the work in this order:

1. `src/contracts/unified_evidence_schema.py`
2. `src/contracts/evidence_adapters.py`
3. `src/llm/evidence_bundle.py`
4. `src/output/l7_answer.py`
5. retrieval service updates
6. provenance schema updates
7. scoring module
8. tests

This order keeps changes incremental and preserves the current CLI paths.

## Deliverables by Milestone

### Milestone A: Contract Defined

Done when:

- schema doc exists
- typed schema exists in `src/contracts`
- adapters compile

### Milestone B: Contract Emitted

Done when:

- L5/L6 can return unified bundle payloads
- L7 reads from the unified bundle

### Milestone C: Provenance Strengthened

Done when:

- relation evidence includes sentence index
- provenance method is explicit
- char offset fields exist, even if nullable

### Milestone D: Evidence Ranking Available

Done when:

- `evidence_rank_score` is emitted consistently
- retrieval can rank evidence records deterministically

## Explicit Non-Goals

This refactor plan does not require:

- replacing SQLite with a graph database
- removing existing dataframe outputs
- building a full biomarker ontology first
- solving live BioRED NER on all new PubMed abstracts first

The immediate objective is contract unification and downstream reuse.
