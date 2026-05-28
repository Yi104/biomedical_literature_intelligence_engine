# L7 Output Contract (v1)

This document defines the current L7 JSON output contract.

## Purpose

L7 is the final packaging layer for user-facing output. It does not run
retrieval itself and does not modify evidence. It wraps L5/L6 results into one
stable object for CLI, UI, and API usage.

## Input Boundary

L7 consumes:

- L5 result from `run_agent_controller(...)`
- L6 result from `summarize_agent_result_with_provider(...)`

L7 implementation:

- `src/output/l7_answer.py`
- `pipelines/run_l7_answer.py`

## Contract

```json
{
  "question": "What is the evidence for BRCA1 and breast cancer?",
  "status": "evidence_found",
  "task": "biored",
  "answer": "evidence bundle returned",
  "claims": [
    {
      "text": "BRCA1 -[Association]-> breast cancer",
      "pmids": ["10788334"],
      "evidence_type": "relation"
    }
  ],
  "citations": ["10788334"],
  "evidence_bundle": {},
  "limitations": [
    "L7 v1 is deterministic wrapper output; claim-level citation validation is pending.",
    "L6 provider used: none."
  ]
}
```

## Status Mapping

- `status` comes directly from L5.
- `answer` comes from L6 summary when available.
- If L6 summary is empty:
  - `insufficient evidence` when no records exist
  - `evidence bundle returned` when records exist

## Current Limitations

- Claim text generation is deterministic and shallow in v1.
- Claim-level citation validation is not yet enforced.
- No L7-specific ranking or conflict-resolution policy yet.
