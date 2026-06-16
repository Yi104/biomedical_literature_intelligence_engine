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

## 2026-06-16

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

## Recording rule

Add an entry here when a change does at least one of the following:
- changes a task contract,
- changes baseline metrics or evaluation interpretation,
- changes default model selection,
- changes runtime behavior for BioRED / BC5CDR / JNLPBA task paths,
- adds or removes operational traceability such as logs or manifests.
