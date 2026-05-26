# L5 Agent Controller Logic

This document defines the first implemented version of the L5 agent layer and
records the planned v2 improvements.

## Purpose

L5 is the orchestration layer between deterministic retrieval and later natural
language generation. Its first responsibility is to decide which existing
system operation to run, not to invent biomedical conclusions.

In the first version, L5 should be a deterministic controller:

```text
request
  -> query the existing knowledge base through L4
  -> optionally refresh the knowledge base through L0-L3
  -> query again after refresh
  -> return a structured evidence bundle
```

This keeps retrieval and ingestion testable before an LLM is allowed to
summarize any result.

## Layer Boundaries

L5 may:

- Receive an explicit task and retrieval request.
- Call L4 retrieval functions.
- Decide whether a caller-authorized refresh is required.
- Trigger an existing task pipeline and SQLite writer when refresh is enabled.
- Return a structured evidence bundle and operation status.

L5 should not:

- Claim that an entity causes, predicts, or treats a disease.
- Create evidence not present in stored or newly retrieved records.
- Use an LLM to choose database operations in the first version.
- Generate a final user-facing biomedical answer.

Natural language generation belongs to L6 and must use evidence returned by
L5.

## Existing Dependencies

L5 builds on these completed layers:

| Layer | Existing component | Role in the L5 workflow |
| --- | --- | --- |
| L1 / L2 | task pipelines with normalization | Extract and normalize entities from retrieved abstracts |
| L3 | `src/kb/writer.py` | Persist pipeline results in SQLite |
| L4 | `src/retrieval/sqlite_service.py` | Query the local knowledge base with a stable response contract |

The SQLite knowledge base is stored by default at:

```text
data/processed/kb/biomed_kb.db
```

## Version 1 Request Contract

The controller should begin with explicit request parameters instead of
attempting to parse arbitrary natural language.

Example: retrieve existing evidence by normalized entity ID.

```python
{
    "task": "bc5cdr",
    "retrieval_mode": "normalized_id",
    "normalized_id": "HGNC:1100",
    "allow_refresh": False
}
```

Example: allow a new PubMed-backed ingestion operation when the caller
explicitly requests it.

```python
{
    "task": "bc5cdr",
    "search_query": "BRCA1 breast cancer",
    "retmax": 5,
    "allow_refresh": True
}
```

Recommended initial fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `task` | Yes | Extraction task to use when refresh is run, such as `bc5cdr` or `jnlpba` |
| `retrieval_mode` | For existing KB reads | L4 mode: `pmid`, `normalized_id`, or `type_keyword` |
| `pmid` | Conditional | Lookup key for `pmid` mode |
| `normalized_id` | Conditional | Lookup key for `normalized_id` mode |
| `entity_type` | Conditional | Filter for `type_keyword` mode |
| `keyword` | Conditional | Filter for `type_keyword` mode |
| `search_query` | For refresh | PubMed query used to run a new extraction/ingestion workflow |
| `retmax` | Optional | Maximum papers retrieved during refresh |
| `allow_refresh` | Yes | Whether L5 is allowed to modify the local knowledge base |

## Version 1 Decision Flow

### Case A: Query Existing Knowledge Only

When `allow_refresh=False`, L5 must only call L4.

```text
explicit retrieval request
  -> query_kb(...)
  -> if results exist: return evidence_found
  -> if no results exist: return insufficient_evidence
```

This case is read-only and reproducible.

### Case B: Explicit Knowledge Base Refresh

When `allow_refresh=True` and a `search_query` is provided, L5 may run an
ingestion workflow:

```text
search query
  -> run task-specific extraction and normalization pipeline
  -> write papers and normalized mentions to SQLite
  -> run L4 retrieval using the requested lookup
  -> return refreshed evidence bundle
```

In version 1, refresh should be explicit. The controller should not infer that
the database is incomplete merely because a search returns no rows; an empty
result can also be a valid outcome.

## Version 1 Response Contract

L5 should provide one stable structure for downstream UI and L6 consumers:

```python
{
    "status": "evidence_found",
    "task": "bc5cdr",
    "retrieval_mode": "normalized_id",
    "filters": {"normalized_id": "HGNC:1100"},
    "refreshed": False,
    "count": 1,
    "evidence": [],
    "refresh": None,
    "message": None
}
```

Recommended status values:

| Status | Meaning |
| --- | --- |
| `evidence_found` | Existing KB query returned evidence without refresh |
| `insufficient_evidence` | No evidence was returned and no refresh was run |
| `refreshed_and_found` | Refresh completed and follow-up query returned evidence |
| `refreshed_no_evidence` | Refresh completed but follow-up query returned no evidence |
| `refresh_failed` | Requested refresh failed before a valid response could be built |

The response should preserve L4 filters and raw retrieval results. Later
layers need to distinguish the stored evidence from generated explanation.
When refresh is executed successfully, `refresh` records the source query and
the row counts added to SQLite.

## Original v1 Evidence Limitation

The first L5 v1 milestone was mention-oriented. It supported queries such as:

```text
PMID -> BRCA1 -> HGNC:1100
```

It did not yet provide a stable sentence-level evidence record such as:

```text
PMID -> sentence text -> entity mention -> normalized ID -> citation context
```

L3-L5 v1.1 addresses this limitation with explicit sentence evidence modes,
described below. L6 summarization is still not enabled until its evidence-only
contract is implemented and validated.

## Sentence-Level Evidence Upgrade (L5 v1.1)

L5 remains a deterministic controller, but it can now request richer L4
evidence through two additional retrieval modes:

| Retrieval mode | Meaning |
| --- | --- |
| `evidence_pmid` | Retrieve stored source sentences and linked entities for one PMID |
| `evidence_normalized_id` | Retrieve stored source sentences linked to one normalized entity ID |

Example request:

```python
{
    "task": "bc5cdr",
    "retrieval_mode": "evidence_pmid",
    "pmid": "SMOKE001",
    "search_query": "BRCA1 breast cancer",
    "allow_refresh": True
}
```

Example `evidence` content:

```python
[
    {
        "sentence_text": "BRCA1 is associated with breast cancer.",
        "entities": [
            {"entity_text": "BRCA1", "normalized_id": "HGNC:1100"},
            {"entity_text": "breast cancer", "normalized_id": "MESH:D001943"}
        ]
    }
]
```

When a refresh runs, the `refresh` summary now includes
`evidence_sentences_added`. This makes it visible whether new source-text
evidence was persisted during the update.

This upgrade is not the complete L5 v2. It provides sentence evidence required
for future summarization; natural-language request planning, provenance-aware
refresh decisions, and decision traces remain v2 work.

Full cross-layer upgrade record:

- `doc/sentence_level_evidence_upgrade.md`

## Implementation Files

| File | Responsibility |
| --- | --- |
| `src/agent/controller.py` | Validate requests, run the deterministic decision flow, return the evidence bundle |
| `tests/unit/test_agent_controller.py` | Cover read-only lookup, explicit refresh, no-evidence, refresh failure, and local smoke refresh |
| `pipelines/run_agent_query.py` | CLI wrapper for controller queries and explicit refresh |

## Testing Targets

Initial regression tests should verify:

1. A read-only request returns existing L4 evidence without invoking refresh.
2. A read-only empty lookup returns `insufficient_evidence`.
3. A refresh-authorized request writes pipeline results and re-queries SQLite.
4. A failed refresh returns `refresh_failed` without fabricating evidence.
5. Returned evidence preserves the original retrieval filters and result rows.

## Implementation Order

1. Add `src/agent/controller.py` with explicit typed request/response handling.
2. Use existing L4 retrieval as the only read path.
3. Add an injectable refresh function so unit tests do not require PubMed or
   model inference.
4. Add regression tests for decision states and evidence integrity.
5. Add sentence-level evidence support before enabling L6-generated answers.
   Completed in the L3-L5 v1.1 upgrade documented below.

## Definition of Done for L5 v1

- L5 can execute a deterministic read-only KB query.
- L5 can execute an explicitly authorized refresh followed by a KB query.
- Every result is returned in a stable evidence bundle.
- No LLM is required to decide data operations.
- Unit tests cover successful, empty, and failed controller paths.

## Version 2 Improvements

Version 1 establishes a reliable controller around entity-level evidence.
Version 2 should improve evidence quality and request convenience without
removing the deterministic control boundary.

### Current v1.1 Versus v2 Scope

| Capability | Current v1.1 | v2 improvement |
| --- | --- | --- |
| Request input | Explicit query mode and filters | Accept a user question and map it to validated retrieval actions |
| Refresh behavior | Refresh only when explicitly authorized with a search query | Recommend or execute controlled refresh based on coverage/provenance checks and user settings |
| Evidence unit | Sentence-level source evidence linked to normalized mentions | Add exact character-span links and ingestion provenance for stronger traceability |
| Retrieval strategy | One L4 lookup mode per request, including explicit evidence modes | Multi-step retrieval across normalized IDs, PMIDs, entity types, and evidence sentences |
| Result ordering | Preserve deterministic L4 query output | Rank evidence using transparent rules such as entity match, source, date, and duplicate removal |
| LLM involvement | None in operation selection | Optional LLM parsing or summarization only behind validated actions and evidence constraints |
| Observability | Status, raw evidence bundle, and refresh counts | Decision trace showing selected actions, refresh reason, evidence sources, and unresolved gaps |

### Improvement 1: Natural Language Request Planning

In v1, the caller must already know whether to query by `pmid`,
`normalized_id`, or `type_keyword`.

In v2, L5 may accept a question such as:

```text
What papers mention BRCA1 in breast cancer?
```

and produce a validated internal plan:

```python
{
    "task": "bc5cdr",
    "actions": [
        {
            "tool": "query_kb",
            "mode": "type_keyword",
            "entity_type": "Gene",
            "keyword": "BRCA1"
        },
        {
            "tool": "query_evidence_sentences",
            "disease_keyword": "breast cancer"
        }
    ]
}
```

This is not permission for an LLM to run arbitrary code or SQL. The planned
actions must be validated against an allowlisted set of controller actions
before execution.

### Improvement 2: More Precise Sentence-Level Evidence Bundles

Version 1.1 now returns sentence-level evidence. Version 2 should improve
traceability by adding exact character spans and ingestion provenance.

The current evidence item shape is designed for content such as:

```python
{
    "pmid": "12345678",
    "sentence_text": "BRCA1 mutations were observed in breast cancer cases.",
    "entities": [
        {"text": "BRCA1", "normalized_id": "HGNC:1100"},
        {"text": "breast cancer", "normalized_id": "MESH:D001943"}
    ],
    "source": "pubmed_abstract"
}
```

Version 1.1 completed the first three L3/L4 dependencies. The remaining v2
precision additions are:

| Dependency or improvement | Status / purpose |
| --- | --- |
| Sentence or evidence table in SQLite | Implemented in v1.1 |
| Sentence-to-mention linkage | Implemented in v1.1 using surface-text matching |
| L4 sentence retrieval function | Implemented in v1.1 using explicit evidence modes |
| Character-offset linkage | v2 improvement for exact mention placement |
| Ingestion provenance metadata | v2 improvement for refresh/citation traceability |

### Improvement 3: Controlled Retrieval Plans

Version 1 performs one retrieval action after an optional refresh. Version 2
may combine multiple approved retrieval steps, for example:

```text
resolve an entity alias
  -> retrieve linked PMIDs
  -> retrieve relevant sentences from those papers
  -> rank and deduplicate evidence
  -> return evidence bundle
```

The controller should record the operations executed so the UI and tests can
explain why particular evidence was returned.

### Improvement 4: Coverage-Aware Refresh Decisions

In v1, an empty database lookup is not enough reason to run PubMed retrieval;
refresh must be explicitly requested.

Version 2 may make a better recommendation by examining metadata such as:

- whether the KB has ever been searched for the requested query
- when that ingestion run occurred
- which task/model/version produced the stored entities
- whether the user allows automatic refresh

This requires adding ingestion-run metadata or provenance tables to the
knowledge base. Without that metadata, L5 cannot reliably tell whether
evidence is missing or simply has not yet been collected.

### Improvement 5: Evidence-Constrained L6 Integration

After sentence-level evidence is available, v2 may hand the evidence bundle
to L6 for summarization through a user-selected provider such as local Ollama
or a BYO API key provider.

The L5/L6 boundary should remain explicit:

```text
L5 returns retrieved evidence and traceable provenance.
L6 summarizes only the evidence supplied by L5.
```

The response should separately expose:

| Output field | Purpose |
| --- | --- |
| `evidence` | Retrieved source-backed records |
| `generation` | Optional natural language summary |
| `citations` | PMIDs and source snippets used by the summary |
| `limitations` | Missing evidence, unresolved entities, or unsupported claims |

### Proposed v2 Files or Extensions

| File or module | Proposed change |
| --- | --- |
| `src/kb/schema.py` | Add sentence/evidence and ingestion provenance tables |
| `src/kb/writer.py` | Persist evidence snippets and run metadata |
| `src/kb/query.py` | Add sentence-level and provenance queries |
| `src/retrieval/sqlite_service.py` | Expose evidence and multi-step retrieval contracts |
| `src/agent/controller.py` | Add validated plans, decision traces, and coverage-aware refresh policy |
| `src/llm/router.py` | Consume evidence bundles for optional constrained summarization |

### Definition of Done for L5 v2

- A user-facing question can be converted into allowlisted retrieval actions.
- Returned evidence includes sentence text and PMID-linked provenance.
- Refresh decisions can be explained using stored ingestion metadata.
- Multi-step retrieval returns a recorded decision trace.
- Optional L6 summaries are separated from source evidence and cite the
  evidence records used.
