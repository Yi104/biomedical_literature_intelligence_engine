# L6 Summarization Logic

This document defines the implemented L6 behavior and its boundary with L5.

## Purpose

L6 consumes deterministic evidence from L5 and produces either:

- an evidence-only payload (`provider=none`), or
- a constrained summary from a selected provider.

L6 must not query databases directly. It only summarizes the evidence bundle it receives.

## Boundary with L5

L5 output (`run_agent_controller`) is the only upstream input source.

L6 conversion path:

```text
L5 agent result
  -> build_evidence_bundle_from_agent_result(...)
  -> summarize_with_provider(...)
```

Source files:

- `src/llm/evidence_bundle.py`
- `src/llm/router.py`
- `pipelines/run_l6_summary.py`

## Implemented Bundle Contract (v1)

Top-level fields:

- `question`
- `task`
- `retrieval_mode`
- `status`
- `insufficient_evidence`
- `count`
- `pmids`
- `records`
- `filters`

Mode-specific `records`:

- Relation modes (`relation_pmid`, `relation_entity_pair`):
  - `relation_type`, entity pair IDs/types/text
  - `evidence_sentence`, `novelty`, `provenance_source`, `confidence`
- Sentence modes (`evidence_pmid`, `evidence_normalized_id`):
  - `sentence_index`, `evidence_sentence`, linked `entities`
- Mention modes (`pmid`, `normalized_id`, `type_keyword`):
  - mention-level entity fields

## Provider Behavior

Supported providers:

- `none`
- `ollama`
- `openai`
- `anthropic`
- `gemini`

Current behavior:

- `none`: returns `mode=evidence_only`, no model call.
- `ollama`: calls local Ollama `/api/generate`.
- `openai|anthropic|gemini`: returns `provider_not_wired` placeholder (BYO integration pending).

## Prompt Constraint

Prompt is deterministic and evidence-grounded:

1. Use only provided evidence.
2. If insufficient evidence, say "insufficient evidence".
3. Attach PMIDs for every claim.

## CLI Entry Point

Use:

```bash
python -m pipelines.run_l6_summary --task biored --mode relation_entity_pair --entity1_normalized_id 672 --entity2_normalized_id D001943 --question "What is the evidence for BRCA1 and breast cancer?" --provider none --db_path data/processed/kb/biomed_kb.db
```

For BioRED 4A model-predicted relation refresh, add:

```bash
--allow_refresh --data_path data/raw/biored/BioRED/Test.PubTator --relation_mode model
```

## Current Limitations

- No claim-level citation validator yet.
- No provider-specific post-processing/guardrails yet.
- No final L7 answer contract enforcement in L6 itself.
