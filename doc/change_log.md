# Change Log

This file records project-level changes that affect behavior, interfaces,
evaluation interpretation, or operational traceability.

## 2026-06-15

### BioRED 4A relation inference

Commit:
- `e46f83e` `Add BioRED relation inference 4A`

What changed:
- Added `relation_mode=model` to the BioRED pipeline.
- Added `src/extraction/biored_relation_infer.py`.
- BioRED can now:
  - load local PubTator entities,
  - enumerate gene-disease candidate pairs,
  - score them with the trained relation classifier,
  - emit `relations_df` without using gold relation rows.

Behavioral effect:
- `relation_mode=gold` keeps prior behavior and uses PubTator relation
  annotations.
- `relation_mode=model` switches relation generation to classifier predictions.

Boundary:
- This is a local BioRED corpus inference path only.
- It does not perform live BioRED-style NER on newly retrieved PubMed
  abstracts.

Contract change:
- `relations_df` now includes `confidence`.
- Relation provenance in SQLite preserves the actual `relation_source`.

Validation:
- Unit tests passed after the change.
- Verified on `data/raw/biored/BioRED/Test.PubTator` with `--max_docs 1`.
- Verified L5 refresh -> SQLite write -> L4 relation query roundtrip.

### True test split recorded for BioRED baseline

What changed:
- Updated `configs/biored_relations.json` to use
  `data/raw/biored/BioRED/Test.PubTator`.
- Recorded true test metrics in
  `outputs/baselines/biored_relations_v1/README.txt`.

Why:
- Earlier relation metrics were selected from dev-based evaluation.
- The baseline now has an explicit true test reference for reporting.

Recorded true test metrics:
- `eval_f1_macro: 0.5762780398575141`
- `eval_f1_micro: 0.7440677966101695`
- `eval_loss: 2.092841625213623`

### Best/latest relation model pointer fix

Commit:
- `b43d04c` `Fix BioRED best model selection`

What changed:
- Separated:
  - `LATEST_MODEL_PATH.txt`
  - `BEST_MODEL_PATH.txt`
- Added `BEST_MODEL_METRICS.json`.
- Evaluation now resolves a loadable best model instead of blindly using the
  latest run path.
- Training now limits retained checkpoints with `save_total_limit=1`.

Why:
- The previous logic let the latest completed run overwrite the practical
  default, even when it was not the best run.
- Cleanup had removed some per-run weight directories, so pointer validation
  needed to check that real model weights still exist.

Behavioral effect:
- Default evaluation and inference resolve the frozen baseline model
  consistently.

Validation:
- Added unit tests for pointer resolution and tie-breaking.
- Full test suite passed after the change.

### 4A runtime logging

What changed:
- Added `logging` instrumentation for BioRED 4A pipeline and L5 refresh path.
- Added `--log_level` to:
  - `pipelines/run_extract_biored.py`
  - `pipelines/run_ingest_to_sqlite.py`
  - `pipelines/run_agent_query.py`
  - `pipelines/run_l6_summary.py`
  - `pipelines/run_l7_answer.py`

Logged events:
- BioRED pipeline start parameters
- loaded PubTator table sizes
- candidate pair count
- resolved model path and label set
- filtered prediction counts
- L5 refresh start / produced table sizes / final retrieval status

Current output mode:
- Logs are emitted to the console through Python `logging`.
- They are not yet written to persistent log files by default.

Why:
- 4A needed run-time traceability so inference behavior can be explained after
  the fact.

Validation:
- Unit tests passed after log instrumentation.
- Verified on a real one-document 4A run and observed expected INFO logs.

### Automatic log persistence and run manifests

What changed:
- Added `src/logging_utils.py`.
- CLI entrypoints now create per-run log directories under `outputs/logs/`.
- Each run writes:
  - `run.log`
  - `manifest.json`

Covered entrypoints:
- `pipelines/run_extract_biored.py`
- `pipelines/run_ingest_to_sqlite.py`
- `pipelines/run_agent_query.py`
- `pipelines/run_l6_summary.py`
- `pipelines/run_l7_answer.py`

Current log layout:

```text
outputs/logs/<command_name>/<timestamp>/run.log
outputs/logs/<command_name>/<timestamp>/manifest.json
```

Manifest contents:
- command name
- run id
- timestamp
- status
- args
- log path
- summary
- error traceback on failure

Why:
- Console logs alone were not sufficient for post-run quality control.
- Each important run now leaves a durable record that can be reviewed later.

Validation:
- Added unit tests for logging helper setup and manifest finalization.
- Verified a real CLI run creates persistent artifacts.

## 2026-06-16

### Unified evidence-layer contract and refactor plan

What changed:
- Added `doc/unified_evidence_schema.md`.
- Added `doc/evidence_schema_refactor_plan.md`.
- Added `doc/data_flow_architecture.md`.
- Linked the new architecture and schema documents from `doc/system_design_v2.md`.

Why:
- The repository had extraction contracts, SQLite tables, and L6/L7 wrappers,
  but did not yet define one stable platform-level evidence contract.
- The repository also lacked one document that explicitly shows where
  extraction, storage, retrieval, agent, and evidence contracts change across
  the pipeline.
- The new documents make the project boundary explicit:
  - current state: extraction + normalization + SQLite + partial provenance
  - target state: reusable `Document / Entity / Relation / Evidence / Provenance`
    contract for `bioAI-target` and other downstream KB integrations

Behavioral effect:
- No runtime behavior changed.
- Project documentation now distinguishes:
  - extraction-layer outputs
  - evidence-layer objects
  - the migration path between them

Operational effect:
- Future code changes can now be evaluated against a written schema target
  instead of ad hoc bundle shapes.

### Unified evidence contract code scaffolding

What changed:
- Added `src/contracts/unified_evidence_schema.py`.
- Added `src/contracts/evidence_adapters.py`.
- Added `src/contracts/__init__.py`.
- Updated `src/llm/evidence_bundle.py` to build L6 bundles through the unified
  adapter layer instead of direct ad hoc row flattening.
- Added focused tests for schema versioning and adapter behavior.

Why:
- The repository needed the evidence-layer contract to exist in code, not only
  in documentation.
- The adapter layer is the lowest-risk bridge between current retrieval output
  and the future reusable evidence bundle consumed by L6/L7 and downstream
  systems.

Behavioral effect:
- L6 evidence bundle construction now flows through a unified schema-oriented
  adapter path while preserving the current `records` field shape for backward
  compatibility.

Validation:
- New modules compiled successfully with `python -m py_compile`.
- Direct adapter smoke validation passed through a Python import/assert script.
- Full `pytest` execution could not be completed in the current environment due
  to an external Python 3.13 `pytest` segmentation fault during debugger/plugin
  import.

### Retrieval and agent unified bundle integration

What changed:
- Updated `src/retrieval/sqlite_service.py` to attach unified evidence-layer
  payload sections alongside the existing `results` contract.
- Updated `src/agent/controller.py` to return:
  - `schema_version`
  - `documents`
  - `entities`
  - `relations`
  - `evidence_records`
  - `provenance`
  - `bundle`
- Extended retrieval and agent unit tests to assert the new integration fields
  while preserving legacy fields.

Why:
- The unified contract needed to move downward from L6-only wrapping into the
  L4/L5 integration boundary where downstream systems will actually consume it.
- This keeps existing callers working while making retrieval and agent outputs
  directly usable by `bioAI-target` and other KB consumers.

Behavioral effect:
- Retrieval and agent responses now expose both:
  - legacy mode-specific rows
  - unified evidence-layer object sections

Validation:
- Updated files compiled successfully with `python -m py_compile`.
- Environment-level runtime verification remains limited by the same external
  Python instability observed during `pytest` execution in this session.

### Domain-agnostic evidence schema clarification

What changed:
- Updated `src/contracts/unified_evidence_schema.py` comments to make entity
  types and relation endpoints explicitly open-ended.
- Updated `doc/unified_evidence_schema.md` with subject/object examples beyond
  gene-disease, including drug-disease and variant-disease style relations.
- Updated `doc/data_flow_architecture.md` to state that the unified bundle
  should remain reusable across multiple biomedical relation domains.

Why:
- The schema should not read as BioRED-only or gene-disease-only if it is
  intended to support future integration into other knowledge base settings.

Behavioral effect:
- No runtime behavior changed.
- The contract definition is now clearer about how `subject` and `object`
  should be interpreted in non-BioRED domains.

### Provenance v1 storage and retrieval upgrade

What changed:
- Updated `src/kb/schema.py` so `relation_provenance` now supports:
  - `evidence_id`
  - `sentence_index`
  - `link_method`
  - `char_start`
  - `char_end`
- Updated `src/kb/writer.py` to populate those provenance fields when writing
  relation outputs.
- Updated `src/kb/query.py` to return the new provenance fields.
- Updated `src/contracts/evidence_adapters.py` so unified provenance objects
  can carry the stronger provenance payload.
- Extended KB and retrieval tests for provenance roundtrip assertions.

Why:
- The repository already had relation provenance as text plus confidence, but
  the integration layer needed explicit provenance structure rather than only a
  sentence string.

Behavioral effect:
- Relation evidence now carries sentence-level provenance metadata through
  SQLite, query, and unified bundle adaptation.
- Offsets remain nullable in V1, but the fields now exist end to end.

Validation:
- Updated modules compiled successfully with `python -m py_compile`.
- Direct SQLite roundtrip validation passed with a focused Python script:
  relation provenance now returns `sentence_index`, `link_method`, and
  `evidence_id` as expected.

### Repository structure documentation refresh

What changed:
- Updated `README.md` to describe the current repository structure and module
  roles after the unified evidence contract and integration work.
- Marked the old repository structure block in `doc/system_design_v2.md` as an
  archived proposal instead of leaving it looking current.

Why:
- The project structure has shifted enough that older directory descriptions
  were misleading and made the repository harder to navigate.

Behavioral effect:
- No runtime behavior changed.
- Repository navigation guidance now aligns with the current code layout.

### Historical documents moved under `doc/historical/`

What changed:
- Moved `doc/sentence_level_evidence_upgrade.md` to
  `doc/historical/sentence_level_evidence_upgrade.md`.
- Moved `doc/biored_primary_task_transition.md` to
  `doc/historical/biored_primary_task_transition.md`.
- Updated repository and design-document references to point to the new paths.

Why:
- These documents remain useful background context, but they should not sit in
  the main design-document path as if they were current architecture specs.

Behavioral effect:
- No runtime behavior changed.
- Historical design context is now separated more clearly from current
  architecture documents.

### Document timestamp convention for major design files

What changed:
- Added `Last updated on: 2026-06-16 (America/Los_Angeles)` under the title of
  major current design documents and the main README:
  - `README.md`
  - `SYSTEM_DESIGN.md`
  - `doc/system_design_v2.md`
  - `doc/data_flow_architecture.md`
  - `doc/end_to_end_data_flow.md`
  - `doc/unified_evidence_schema.md`
  - `doc/system_architecture_diagram.md`

Why:
- Large design documents become hard to trust when their freshness is unclear.
- A visible timestamp makes it easier to know which documents reflect the
  latest architecture and contract state.

Behavioral effect:
- No runtime behavior changed.
- Major design documents now expose their recency directly at the top.

### Historical document obsolescence timestamps

What changed:
- Added `Obsoleted on: 2026-06-16 (America/Los_Angeles)` to:
  - `doc/historical/sentence_level_evidence_upgrade.md`
  - `doc/historical/biored_primary_task_transition.md`

Why:
- Historical documents should make their status obvious at the top, not only by
  directory placement.

Behavioral effect:
- No runtime behavior changed.
- Historical documents now explicitly mark when they stopped being current
  architecture references.

### Clarified BioRED benchmark role versus future PubTator coverage role

What changed:
- Updated `doc/system_design_v2.md` to explicitly distinguish:
  - `BioRED` as the current gold benchmark and training/evaluation anchor
  - `PubTator` / `PubTator 3` as a future coverage/reference source
  - runtime new-abstract inference versus gold evaluation semantics
- Updated `SYSTEM_DESIGN.md` with the same short-form clarification.
- Updated touched document timestamps to `2026-06-17`.

Why:
- The previous wording did not clearly explain whether new abstract inference
  should be judged against PubTator, or what role PubTator should play in the
  architecture.
- The architecture now states that BioRED calibrates quality, while PubTator
  is a future non-gold coverage layer.

Behavioral effect:
- No runtime behavior changed.
- The design docs now better match the actual current system boundary and the
  intended next-stage architecture.

### System design terminology corrected from NER-only to extraction-layer wording

What changed:
- Updated `doc/system_design_v2.md` so L1 is described as entity and relation
  extraction rather than as a BioBERT-NER-only layer.
- Updated the task status table in `doc/system_design_v2.md` to reflect the
  current BioRED relation path.
- Updated `SYSTEM_DESIGN.md` diagram text so BC5CDR and JNLPBA are described as
  entity-extraction paths rather than "PubMed + BioBERT NER" only.

Why:
- The project has already moved beyond an NER-only framing.
- Keeping system design language at the NER-only level would misdescribe the
  current primary-task architecture and mislead later quality work.

Behavioral effect:
- No runtime behavior changed.
- System design wording now better reflects the current extraction scope.

### Project naming updated to Biomedical Literature Intelligence Engine

What changed:
- Updated primary document titles to use `Biomedical Literature Intelligence Engine`.
- Updated the README shell example path to
  `biomedical_literature_intelligence_engine`.

Why:
- The previous project naming overemphasized `BioBERT`, `biomarker`, and
  `NER`, which no longer reflects the actual project scope.
- The new name better matches the current architecture: literature retrieval,
  extraction, evidence objects, provenance, retrieval, and downstream
  assessment support.

Behavioral effect:
- No runtime behavior changed.
- Repository-facing documentation now reflects the intended new project name.


## Recording rule

Add an entry here when a change does at least one of the following:
- changes a task contract,
- changes baseline metrics or evaluation interpretation,
- changes default model selection,
- changes runtime behavior for BioRED / BC5CDR / JNLPBA task paths,
- adds or removes operational traceability such as logs or manifests.
