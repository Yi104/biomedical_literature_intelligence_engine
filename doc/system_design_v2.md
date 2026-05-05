# Biomedical Literature Intelligence System Design (V2)

## 1. Objective

Build a production-style biomedical literature intelligence system that converts unstructured PubMed abstracts into a structured, queryable evidence knowledge base and supports LLM-assisted querying with strict citation grounding.

Core constraints:

- LLM does not generate new biomedical knowledge
- Every claim must be grounded in PMID-level evidence
- Structured outputs are first-class artifacts
- Components are modular, testable, and reproducible

## 2. Layered Architecture

### L0. Data Layer (PubMed Ingestion)

Responsibilities:

- Query PubMed (gene/disease/filters)
- Fetch PMID metadata + abstracts
- Deduplicate by PMID
- Store ingestion provenance (query, timestamp, source)

Inputs:

- Search query, year range, journal filter

Outputs:

- Raw paper records persisted to KB

### L1. Extraction Layer (BioBERT NER)

Responsibilities:

- Split abstracts into sentences
- Run BioBERT token classification
- Produce mention spans, entity types, and confidence

Inputs:

- Paper abstracts

Outputs:

- Mention-level extraction records linked to sentence and PMID

### L2. Normalization Layer

Responsibilities:

- Canonicalize entity strings (case/symbol normalization)
- Map synonyms to canonical names
- Optional mapping to external IDs (HGNC, MeSH, UMLS)
- Apply confidence thresholds and type validation

Inputs:

- Mention-level entities from NER

Outputs:

- Canonical entities + normalized mention links

### L3. Knowledge Base Layer (SQLite-first)

Responsibilities:

- Persist papers, sentences, entities, mentions, and evidence tuples
- Maintain foreign-key traceability from claim -> sentence -> PMID
- Support deterministic SQL retrieval

Inputs:

- Ingested papers + normalized extraction outputs

Outputs:

- Queryable evidence knowledge base

### L4. Retrieval Layer

Structured retrieval:

- SQL retrieval over evidence tables (`gene_disease_evidence`, `papers`, `entities`)

Optional semantic retrieval:

- Sentence embedding reranking for recall boost

Output:

- Ranked evidence packets with sentence text and PMID citations

### L5. Agent Layer (Tool-Calling Orchestration)

Responsibilities:

- Parse user query intent and slots (`gene`, `disease`, filters)
- Decide whether KB-only retrieval is sufficient
- Trigger PubMed refresh path when evidence coverage is low

Output:

- Evidence bundle for LLM summarization

### L6. LLM Layer (Constrained Summarization)

Responsibilities:

- Summarize only retrieved evidence
- Attach citations to each claim
- Report uncertainty/conflicts explicitly

Constraint:

- No unsupported claims allowed

### L7. Output Layer

Responsibilities:

- Return machine-readable + human-readable outputs
- Include evidence table and citation payload

Formats:

- JSON for APIs
- Markdown/table for UI
- CSV for downstream analytics

## 3. Database Schema

SQLite schema designed for sentence-level provenance.

### `papers`

Purpose: canonical paper metadata and abstract source.

- `pmid TEXT PRIMARY KEY`
- `title TEXT NOT NULL`
- `abstract TEXT`
- `journal TEXT`
- `pub_year INTEGER`
- `doi TEXT`
- `query_source TEXT`
- `ingested_at TEXT` (ISO8601)
- `abstract_hash TEXT`

Recommended indexes:

- `idx_papers_year(pub_year)`
- `idx_papers_journal(journal)`

### `sentences`

Purpose: sentence-level anchoring for evidence.

- `sentence_id INTEGER PRIMARY KEY AUTOINCREMENT`
- `pmid TEXT NOT NULL` (FK -> `papers.pmid`)
- `sent_idx INTEGER NOT NULL`
- `text TEXT NOT NULL`
- `char_start INTEGER`
- `char_end INTEGER`

Recommended indexes:

- `idx_sentences_pmid(pmid)`

### `entities`

Purpose: canonicalized entity registry.

- `entity_id INTEGER PRIMARY KEY AUTOINCREMENT`
- `canonical_name TEXT NOT NULL`
- `entity_type TEXT NOT NULL` (`GENE|DISEASE|CHEMICAL`)
- `external_id TEXT`
- `source_vocab TEXT`
- `created_at TEXT`

Constraint:

- `UNIQUE(canonical_name, entity_type, external_id)`

### `entity_mentions`

Purpose: raw NER mentions with confidence and normalization linkage.

- `mention_id INTEGER PRIMARY KEY AUTOINCREMENT`
- `pmid TEXT NOT NULL` (FK -> `papers.pmid`)
- `sentence_id INTEGER NOT NULL` (FK -> `sentences.sentence_id`)
- `mention_text TEXT NOT NULL`
- `entity_type_pred TEXT NOT NULL`
- `char_start INTEGER`
- `char_end INTEGER`
- `confidence REAL`
- `model_version TEXT`
- `normalized_entity_id INTEGER` (nullable FK -> `entities.entity_id`)

Recommended indexes:

- `idx_mentions_pmid(pmid)`
- `idx_mentions_sentence(sentence_id)`
- `idx_mentions_norm_entity(normalized_entity_id)`

### `gene_disease_evidence`

Purpose: structured evidence tuples used for retrieval and summarization.

- `evidence_id INTEGER PRIMARY KEY AUTOINCREMENT`
- `gene_entity_id INTEGER NOT NULL` (FK -> `entities.entity_id`)
- `disease_entity_id INTEGER NOT NULL` (FK -> `entities.entity_id`)
- `pmid TEXT NOT NULL` (FK -> `papers.pmid`)
- `sentence_id INTEGER NOT NULL` (FK -> `sentences.sentence_id`)
- `evidence_sentence TEXT NOT NULL`
- `evidence_type TEXT` (`GENETIC|EXPRESSION|CLINICAL|UNKNOWN`)
- `directionality TEXT` (`POSITIVE|NEGATIVE|UNCLEAR`)
- `association_score REAL`
- `extraction_method TEXT`
- `created_at TEXT`

Recommended indexes:

- `idx_gde_gene(gene_entity_id)`
- `idx_gde_disease(disease_entity_id)`
- `idx_gde_pmid(pmid)`
- `idx_gde_gene_disease(gene_entity_id, disease_entity_id)`

## 4. Tool Abstraction (Agent-Ready API)

Define small deterministic tools with typed returns.

### `search_pubmed(query, retmax=50, year_from=None, year_to=None, journal=None) -> list[dict]`

Returns paper records:

- `pmid`, `title`, `abstract`, `journal`, `pub_year`, `doi`

### `run_ner(papers, model_version) -> list[dict]`

Returns mention records:

- `pmid`, `sentence_id`, `mention_text`, `entity_type_pred`, `char_start`, `char_end`, `confidence`, `model_version`

### `update_kb(papers, mentions) -> dict`

Upserts papers, sentences, entities, mentions, evidence.

Returns ingestion summary:

- `papers_upserted`, `mentions_upserted`, `evidence_upserted`

### `query_kb(gene, disease, limit=20, min_score=0.0) -> list[dict]`

Returns grounded evidence packets:

- `pmid`, `title`, `pub_year`, `journal`, `evidence_sentence`, `evidence_type`, `directionality`, `association_score`

### `get_evidence_sentences(gene, disease, top_k=10, mode="structured") -> list[dict]`

Returns ranked sentence evidence for summarization and display.

## 5. Agent Design

Lightweight deterministic controller (no RL).

Decision flow:

1. Parse query into slots (`gene`, `disease`, optional filters).
2. Run `query_kb(...)`.
3. If evidence count meets threshold, continue to summarization.
4. If evidence is insufficient:
   - run `search_pubmed(...)`
   - run `run_ner(...)`
   - run `update_kb(...)`
   - rerun `query_kb(...)`
5. If still insufficient, return grounded “no evidence found” response.
6. Call LLM summarizer with evidence packets only.
7. Return structured output + citations.

## 6. Citation Enforcement Strategy

### Prompt Constraints

- Only use provided evidence rows
- Every claim must cite one or more PMIDs from context
- If evidence is weak or conflicting, state uncertainty
- Do not infer unsupported mechanisms

### Output Contract (JSON-first)

```json
{
  "query": {"gene": "TP53", "disease": "breast cancer"},
  "summary": "Grounded summary text...",
  "claims": [
    {"text": "Claim text", "pmids": ["12345678"], "evidence_type": "GENETIC"}
  ],
  "evidence_table": [
    {"pmid": "12345678", "sentence": "Supporting sentence", "score": 0.81}
  ],
  "limitations": ["Scope limited to retrieved abstracts."]
}
```

### No-Evidence Fallback

Return explicit null-evidence response:

- `summary`: no grounded evidence found
- `claims`: empty list
- `evidence_table`: empty list
- `limitations`: explain retrieval scope/date/filters

## 7. Repository Structure

```text
repo/
  src/
    ingestion/
      pubmed_client.py
      ingest_pipeline.py
    extraction/
      ner_infer.py
      sentence_split.py
    normalization/
      entity_normalizer.py
      ontology_mapper.py
    kb/
      schema.sql
      repository.py
      upsert.py
    retrieval/
      structured_query.py
      semantic_index.py
    llm/
      prompts.py
      summarizer.py
    agent/
      tools.py
      planner.py
      controller.py
    api/
      service.py
      dto.py
  pipelines/
    run_ingest.py
    run_extract.py
    run_backfill.py
  db/
    kb.sqlite
    migrations/
  data/
    raw/
    processed/
    snapshots/
  tests/
    unit/
    integration/
    fixtures/
  doc/
    SYSTEM_DESIGN.md
    system_design_v2.md
    research_plan.md
  configs/
    default.yaml
    model.yaml
```

## 8. How This Differs from Generic RAG

Compared with embedding-only RAG:

- Primary retrieval is relational evidence tuples, not only vector-nearest chunks
- Strong provenance from claim -> sentence -> PMID
- Deterministic, auditable SQL path

Compared with generic LLM chatbots:

- LLM is a constrained summarizer, not a knowledge generator
- Citation grounding is mandatory and machine-checkable
- No evidence means no claim
- Structured outputs are first-class artifacts for analysis pipelines

## 9. Implementation Priorities

### Phase 1 (MVP)

- SQLite schema + ingestion + NER + evidence table
- Deterministic SQL retrieval
- Strict citation-constrained summarization

### Phase 2

- Entity normalization improvements and ontology mapping
- Semantic sentence reranking
- Directionality/evidence-type classifier refinement

### Phase 3

- API hardening, caching, and observability
- Integration with translational research platform workflows

## 10. Progress Tracker (Current Repository Snapshot)

Status legend:

- `DONE`: implemented and runnable in current repo
- `PARTIAL`: implemented in simplified form, not yet production-complete
- `NOT STARTED`: design exists but implementation absent

### 10.1 Layer Status

| Layer | Status | Current Evidence in Repo | Gap to Close |
|---|---|---|---|
| L0 Data (PubMed ingestion) | `PARTIAL` | `src/pubmed.py` supports PubMed search + abstract fetch + year/journal filters | No persistent ingestion log, no dedup/versioning pipeline, no ingestion provenance stored in DB |
| L1 Extraction (BioBERT NER) | `DONE` | `src/infer.py` performs token inference, label mapping, entity span aggregation | No batch inference service interface yet |
| L2 Normalization | `NOT STARTED` | None | Need canonicalization, synonym mapping, optional ontology IDs |
| L3 Knowledge Base (SQLite) | `NOT STARTED` | None (`db/` folder absent) | Need schema + migration + upsert layer |
| L4 Retrieval | `PARTIAL` | `src/pipeline.py` returns DataFrame summaries from runtime pipeline | No SQL structured retrieval, no semantic reranking index |
| L5 Agent | `NOT STARTED` | None | Need planner/controller + tool-calling policy |
| L6 LLM constrained summarization | `NOT STARTED` | None | Need prompt policy + citation-bound output contract |
| L7 Output layer | `PARTIAL` | `demo/app.py` table display + CSV export | No API JSON contract, no claim-level citation object |

### 10.2 Tool API Status

| Tool | Target in Design | Status | Current Equivalent |
|---|---|---|---|
| `search_pubmed(...)` | Required | `DONE` | `src/pubmed.py::search_pubmed`, `fetch_pubmed_details` |
| `run_ner(...)` | Required | `PARTIAL` | `src/infer.py::ner` works for one tokenized text; wrapper for paper batches not implemented |
| `update_kb(...)` | Required | `NOT STARTED` | None |
| `query_kb(...)` | Required | `NOT STARTED` | None (current retrieval is in-memory DataFrame logic) |
| `get_evidence_sentences(...)` | Required | `NOT STARTED` | None |

### 10.3 Repo Structure Status

| Planned Module | Status |
|---|---|
| `src/ingestion/` | `NOT STARTED` |
| `src/extraction/` | `NOT STARTED` |
| `src/normalization/` | `NOT STARTED` |
| `src/kb/` | `NOT STARTED` |
| `src/retrieval/` | `NOT STARTED` |
| `src/agent/` | `NOT STARTED` |
| `src/llm/` | `NOT STARTED` |
| `pipelines/` | `NOT STARTED` |
| `db/` | `NOT STARTED` |
| `tests/` | `NOT STARTED` |

### 10.4 Immediate Next Milestones

1. Create `db/schema.sql` and `src/kb/upsert.py` for `papers`, `sentences`, `entities`, `entity_mentions`, `gene_disease_evidence`.
2. Add `update_kb(...)` and `query_kb(...)` tool implementations.
3. Refactor current `src/pipeline.py` to persist records and retrieve from SQL instead of in-memory only.
4. Add minimal `src/agent/controller.py` with deterministic KB-first -> PubMed-refresh decision flow.
5. Add a constrained summarizer stub (`src/llm/prompts.py`, `src/llm/summarizer.py`) that enforces PMID citations.

## 11. Reproducibility and Operations Notes

- Version all model artifacts (`model_version` in mentions)
- Store ingestion timestamps and query provenance
- Keep idempotent upsert pipelines
- Add regression tests for evidence grounding rules
- Log end-to-end query traces for auditability
