# Biomedical Literature Intelligence Engine Design (V2)

Last updated on: 2026-06-17 (America/Los_Angeles)

## 1. Objective

Build a production-style biomedical literature intelligence platform with one
primary evidence task and retained supporting task lines:

- Primary Task A: gene/protein-disease citation-grounded evidence with `BioRED`
- Baseline Task B: chemical-disease evidence extraction with `BC5CDR`
- Auxiliary Task C: biomedical entity discovery with `JNLPBA`

The platform converts unstructured PubMed abstracts into structured, queryable evidence and supports LLM-assisted querying with strict citation grounding.

Quick visual map:

- [System Architecture Diagram](system_architecture_diagram.md): current high-level platform map
- [End-to-End Data Flow](end_to_end_data_flow.md): current implemented mapping, ingestion, SQLite, retrieval, and evidence flow
- [Data Flow Architecture](data_flow_architecture.md): current layer-by-layer object flow and contract boundaries
- [Unified Evidence Schema](unified_evidence_schema.md): current reusable evidence-layer contract
- [Sentence-Level Evidence Upgrade](historical/sentence_level_evidence_upgrade.md): historical upgrade record for L3-L5 sentence evidence persistence
- [BioRED Primary Task Transition](historical/biored_primary_task_transition.md): historical rationale for moving the primary task to BioRED
- [Evidence Schema Refactor Plan](evidence_schema_refactor_plan.md): partially historical migration plan; several early integration steps are now implemented

Core constraints:

- LLM does not generate new biomedical knowledge
- Every claim must be grounded in PMID-level evidence
- Structured outputs are first-class artifacts
- Components are modular, testable, and reproducible

Task separation:

- `BioRED` is the primary target dataset for gene/protein-disease relations
- Live BioRED local PubTator ingest + relation persistence + relation retrieval are implemented
- `BC5CDR` labels chemicals and diseases; it remains an implemented evidence baseline, not the primary gene-disease task
- `JNLPBA` remains an implemented broader entity-discovery auxiliary dataset
- The platform shares ingestion, retrieval, KB, and UI layers, but keeps task-specific label spaces and outputs separate

## 1A. Dataset and Resource Roles

The current architecture depends on a clear distinction between:

1. `BioRED` as a high-quality gold benchmark and training/evaluation anchor
2. `PubTator` / `PubTator 3` as a future coverage source for broader runtime use
3. task-specific supporting datasets such as `BC5CDR` and `JNLPBA`

Role split:

- `BioRED`
  - role: gold benchmark, relation-training anchor, error-analysis anchor
  - use: define the primary gene/protein-disease relation task and calibrate
    relation/evidence quality
  - current status: implemented and actively used

- `PubTator` / `PubTator 3`
  - role: coverage source, candidate/reference annotation source, possible
    future silver/weak-supervision source
  - use: expand runtime literature coverage after the BioRED-calibrated
    evidence path is stable
  - current status: not yet integrated as a general runtime ingestion path

- `BC5CDR`
  - role: chemical-disease baseline and workflow support dataset
  - use: retained NER/normalization/retrieval baseline, not the primary
    gene-disease relation benchmark

- `JNLPBA`
  - role: broader entity-discovery auxiliary dataset
  - use: retained for biomedical entity coverage experiments, not the primary
    relation benchmark

Important non-goal:

- The current project is **not** intended to ingest the entire PubTator corpus
  into the local system as a first step.
- The intended long-term direction is query-time literature retrieval plus
  selective use of external coverage annotations.

## 2. Layered Architecture

### L0. Data Layer (PubMed Ingestion)

Responsibilities:

- Query PubMed (gene/disease/filters for the primary BioRED path; chemical/disease for BC5CDR baseline)
- Fetch PMID metadata + abstracts
- Deduplicate by PMID
- Store ingestion provenance (query, timestamp, source)

Inputs:

- Search query, year range, journal filter

Outputs:

- Raw paper records persisted to KB

Current boundary:

- New PubMed abstracts can already enter the system through the ingestion path.
- What is still incomplete is the primary-task extraction path for turning new
  abstracts into BioRED-style relation evidence at runtime.

### L1. Extraction Layer (Entity and Relation Extraction)

Responsibilities:

- Parse task-specific source annotations or run extraction models
- Produce entity mentions, normalized-ready entity records, and when
  applicable relation candidates or relation rows
- Support both entity-centric baseline paths and relation-centric primary-task
  paths

Inputs:

- Paper abstracts or task-specific annotated sources such as local BioRED
  PubTator files

Outputs:

- Entity-level extraction records linked to PMID
- Relation-level records for relation-aware task paths such as BioRED

Task-specific models:

- `BioRED` target: gene/protein, disease, and relation-aware evidence extraction
- `BC5CDR` model: chemical/disease entity extraction baseline
- `JNLPBA` model: broader biomedical entity discovery

Current boundary:

- For `BioRED`, the implemented live path is still centered on local BioRED
  PubTator files.
- A true "new abstract -> BioRED-style entity extraction -> relation inference"
  path is not yet fully implemented.

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

Task-specific normalization:

- For `BioRED`, normalize gene/protein and disease entities for relation evidence
- For `BC5CDR`, normalize chemical and disease mentions for evidence tuples
- For `JNLPBA`, normalize broader bio-entity mentions for KB expansion

Normalization mapping files (local contracts):

- `data/processed/normalization/gene_aliases.csv`
- `data/processed/normalization/disease_aliases.csv`
- `data/processed/normalization/chemical_aliases.csv`

CSV schema (all three files):

- `entity_type, alias, normalized_id, preferred_label`
- `entity_type`: expected values such as `gene`, `disease`, `chemical`
- `alias`: raw/synonym mention form used for lookup
- `normalized_id`: stable external ID (for example `HGNC:1100`, `MESH:D001943`)
- `preferred_label`: canonical display label used in normalized output

Authoritative upstream sources:

Gene mappings (HGNC complete set):

| column | example_value |
|---|---|
| `entity_type` | `gene` |
| `alias` | `(p)rr` |
| `normalized_id` | `HGNC:18305` |
| `preferred_label` | `ATP6AP2` |

Disease mappings (MeSH descriptors/entry terms):

| column | example_value |
|---|---|
| `entity_type` | `disease` |
| `alias` | `(ppnet) peripheral primitive neuroectodermal tumors` |
| `normalized_id` | `MESH:D018241` |
| `preferred_label` | `Neuroectodermal Tumors, Primitive, Peripheral` |

Chemical mappings (ChEBI names/synonyms):

| column | example_value |
|---|---|
| `entity_type` | `chemical` |
| `alias` | `#as(o)` |
| `normalized_id` | `CHEBI:30276` |
| `preferred_label` | `arsorylidyne group` |


Maintenance policy:

- Keep repository CSV files as curated snapshots derived from upstream releases.
- Record upstream release date/version in commit message when refreshing mappings.

### L3. Knowledge Base Layer (SQLite-first)

Responsibilities:

- Persist papers, sentences, entities, mentions, and evidence tuples
- Maintain foreign-key traceability from claim -> sentence -> PMID
- Support deterministic SQL retrieval

Inputs:

- Ingested papers + normalized extraction outputs

Outputs:

- Queryable evidence knowledge base

Shared KB principle:

- Keep one KB backend
- Store task-specific entity mentions and evidence in separate tables or views
- Reuse paper/sentence provenance across both tasks

### L4. Retrieval Layer

Structured retrieval:

- SQL retrieval over evidence tables (`evidence_sentences`, `papers`, `entity_mentions`)

Optional semantic retrieval:

- Sentence embedding reranking for recall boost

Output:

- Ranked evidence packets with sentence text and PMID citations

Task outputs:

- Primary evidence mode: structured gene/protein-disease relation evidence packets from BioRED
- Baseline evidence mode: structured chemical-disease evidence packets from BC5CDR
- Discovery mode: broader entity mention summaries and export tables

Current integration status:

- L4 now exposes unified evidence-layer payload sections in addition to legacy
  mode-specific row outputs.
- The unified payload currently includes:
  - `schema_version`
  - `documents`
  - `entities`
  - `relations`
  - `evidence`
  - `provenance`

### L5. Agent Layer (Tool-Calling Orchestration)

Responsibilities:

- Parse user query intent and slots (`chemical`, `disease`, filters) for the current evidence path
- Decide whether KB-only retrieval is sufficient
- Trigger PubMed refresh path when evidence coverage is low

Output:

- Evidence bundle for LLM summarization

Current integration status:

- L5 now returns both:
  - existing task/mode-specific response fields
  - unified evidence-layer payload sections and `bundle`
- This is sufficient for downstream systems such as `bioAI-target` to consume
  evidence objects without requiring L6 summarization.

### L6. LLM Layer (Constrained Summarization)

Responsibilities:

- Summarize only retrieved evidence
- Attach citations to each claim
- Report uncertainty/conflicts explicitly

Constraint:

- No unsupported claims allowed

Provider strategy (cost-aware and user-flexible):

- `none` (default): no model call, return structured evidence bundle only
- `ollama`: local model via `http://localhost:11434` if user has Ollama
- `openai` / `anthropic` / `gemini`: BYO-key mode (user-provided API key; no platform-hosted model requirement)

Integration contract:

- Input: `question` + evidence bundle from L4/L5
- Output: `{provider, model(optional), summary, citations/evidence}`
- Fallback: if provider unavailable, return evidence-only mode

Current status note:

- L6 bundle construction already flows through the unified adapter path.
- The remaining cleanup item is to keep L6/L7 purely consumer-oriented over the
  unified bundle and avoid future dependence on ad hoc retrieval row shapes.

## 2B. Runtime Inference Semantics

This section clarifies how new-abstract inference should be interpreted.

### Current intended runtime logic

For a new user question:

```text
question
  -> PubMed retrieval
  -> abstract ingestion
  -> entity extraction / normalization
  -> candidate generation
  -> relation inference
  -> evidence objects
  -> target assessment / downstream answer
```

### Current role of the BioRED-trained model

- The BioRED-trained relation model is the current baseline model for the
  primary gene/protein-disease relation task.
- Its role is to provide a first runtime inference path after candidate pairs
  are generated.
- It is calibrated against BioRED gold data, not against PubTator as a gold
  reference.

### Current role of PubTator in runtime inference

- PubTator is **not** currently the main runtime judge for new abstract
  inference.
- PubTator is better understood as a future coverage/reference source that may
  later help with:
  - entity coverage
  - relation candidate support
  - non-gold evidence/reference comparison

### Important comparison rule

- New abstract inference should not be defined as "run the model and always
  compare against PubTator."
- Instead:
  - `BioRED` calibrates model quality
  - runtime inference produces evidence objects
  - `PubTator` may later be added as a separate non-gold coverage layer

Implemented L6 bundle contract (v1):

```json
{
  "question": "What is the evidence for BRCA1 and breast cancer?",
  "task": "biored",
  "retrieval_mode": "relation_entity_pair",
  "status": "evidence_found",
  "insufficient_evidence": false,
  "count": 1,
  "pmids": ["10788334"],
  "records": [
    {
      "evidence_type": "relation",
      "pmid": "10788334",
      "relation_type": "Association",
      "entity1_text": "BRCA1",
      "entity1_type": "GeneOrGeneProduct",
      "entity1_normalized_id": "672",
      "entity2_text": "breast or ovarian cancer",
      "entity2_type": "DiseaseOrPhenotypicFeature",
      "entity2_normalized_id": "D001943",
      "evidence_sentence": "...",
      "novelty": "No",
      "provenance_source": "biored_relation_v1",
      "confidence": 1.0
    }
  ],
  "filters": {
    "entity1_normalized_id": "672",
    "entity2_normalized_id": "D001943",
    "task": "biored"
  }
}
```

Reference implementation:

- `src/llm/evidence_bundle.py`
- `src/llm/router.py::summarize_agent_result_with_provider`
- `pipelines/run_l6_summary.py`
- `src/llm/L6_SUMMARIZATION_LOGIC.md`

### L7. Output Layer

Responsibilities:

- Return machine-readable + human-readable outputs
- Include evidence table and citation payload

Formats:

- JSON for APIs
- Markdown/table for UI
- CSV for downstream analytics

Implemented L7 v1 contract:

- `question`
- `status`
- `task`
- `answer`
- `claims[]`
- `citations[]`
- `evidence_bundle`
- `limitations[]`

Reference implementation:

- `src/output/l7_answer.py`
- `pipelines/run_l7_answer.py`
- `src/output/L7_OUTPUT_CONTRACT.md`

Task-specific outputs:

- `BC5CDR`: chemical, disease, PMID, evidence sentence, evidence type
- `JNLPBA`: entity type, mention text, PMID, sentence, optional canonical ID

## 2A. Current Priorities and TODO

Integration baseline status:

- Unified evidence contract documentation: complete
- Unified evidence contract code scaffolding: complete
- L4 retrieval integration: complete for v1
- L5 agent integration: complete for v1
- Provenance v1 field plumbing:
  - `evidence_id`
  - `sentence_index`
  - `link_method`
  - nullable `char_start` / `char_end`
  complete for v1

Remaining integration cleanup:

1. Keep L6/L7 consumer-only over the unified bundle contract.
2. Expand regression coverage once the local `pytest` environment is stable.
3. Add explicit schema migration/version tracking for SQLite changes.

Next priority after integration baseline:

1. Improve normalization quality and ambiguity handling.
2. Improve relation extraction quality beyond the current BioRED baseline.
3. Add evidence ranking/scoring for better downstream retrieval usefulness.
4. Design the future `PubTator` coverage-source integration path explicitly,
   rather than treating it as already present.

## 3. Historical / Archived Design Notes

The sections below are retained as historical design context from an earlier
planning phase. They are **not** the current source of truth for the live
repository structure.

Use these documents instead for the current architecture and contracts:

- [Data Flow Architecture](data_flow_architecture.md)
- [Unified Evidence Schema](unified_evidence_schema.md)
- [End-to-End Data Flow](end_to_end_data_flow.md)
- [Evidence Schema Refactor Plan](evidence_schema_refactor_plan.md)

Current implementation source of truth in code:

- SQLite schema and writer:
  - `src/kb/schema.py`
  - `src/kb/writer.py`
- Retrieval and agent integration:
  - `src/retrieval/sqlite_service.py`
  - `src/agent/controller.py`
- Unified evidence contract:
  - `src/contracts/unified_evidence_schema.py`
  - `src/contracts/evidence_adapters.py`

Historical scope retained below:

- earlier relational schema proposals
- earlier agent/tool abstractions
- earlier API sketches

### Archived Database Schema Proposal

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

### `bio_entity_mentions`  [planned]

Purpose: task B output table for broader entity discovery.

- `mention_id INTEGER PRIMARY KEY AUTOINCREMENT`
- `entity_id INTEGER` (FK -> `entities.entity_id`)
- `pmid TEXT NOT NULL`
- `sentence_id INTEGER NOT NULL`
- `mention_text TEXT NOT NULL`
- `entity_type TEXT NOT NULL`
- `char_start INTEGER`
- `char_end INTEGER`
- `confidence REAL`
- `model_version TEXT`

### Archived Tool Abstraction (Agent-Ready API)

Define small deterministic tools with typed returns.

### `search_pubmed(query, retmax=50, year_from=None, year_to=None, journal=None) -> list[dict]`

Returns paper records:

- `pmid`, `title`, `abstract`, `journal`, `pub_year`, `doi`

### `run_ner(papers, model_version) -> list[dict]`

Returns mention records:

- `pmid`, `sentence_id`, `mention_text`, `entity_type_pred`, `char_start`, `char_end`, `confidence`, `model_version`

Task split:

- `run_ner_bc5cdr(...)` returns chemical/disease evidence mentions
- `run_ner_jnlpba(...)` returns broader bio-entity mentions

### `update_kb(papers, mentions) -> dict`

Upserts papers, sentences, entities, mentions, evidence.

Returns ingestion summary:

- `papers_upserted`, `mentions_upserted`, `evidence_upserted`

### Current baseline: `query_kb(chemical, disease, limit=20, min_score=0.0) -> list[dict]`

Returns grounded evidence packets:

- `pmid`, `title`, `pub_year`, `journal`, `evidence_sentence`, `evidence_type`, `directionality`, `association_score`

For the BioRED primary path, this API must be extended to accept
`gene/protein` + `disease` relation filters after relation persistence exists.

### `get_evidence_sentences(chemical, disease, top_k=10, mode="structured") -> list[dict]`

Returns ranked sentence evidence for summarization and display.

### Archived Agent Design

Lightweight deterministic controller (no RL).

Decision flow:

1. Parse query into slots (`gene/protein`, `disease`, optional filters for the
   BioRED primary target; `chemical`, `disease` for the current BC5CDR baseline).
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

Mode routing:

- Primary gene-disease `evidence` mode will route to `BioRED` after relation
  persistence and retrieval are implemented.
- Current chemical-disease evidence mode routes to the retained `BC5CDR` workflow.
- Current discovery mode routes to the retained `JNLPBA` workflow.

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
  pipelines/
    run_agent_query.py
    run_eval.py
    run_extract_bc5cdr.py
    run_extract_biored.py
    run_extract_jnlpba.py
    run_ingest_to_sqlite.py
    run_l6_summary.py
    run_l7_answer.py
    run_query_sqlite.py
    run_train.py
    run_train_relations.py
  src/
    agent/
      controller.py
      L5_AGENT_LOGIC.md
    api/
    contracts/
      __init__.py
      evidence_adapters.py
      registry.py
      task_output_schemas.py
      unified_evidence_schema.py
    extraction/
      biored_pipeline.py
      biored_loader.py
      biored_relation_infer.py
      bc5cdr_pipeline.py
      jnlpba_pipeline.py
      model_registry.py
      ner_infer.py
      train_ner.py
      train_relations.py
    ingestion/
      pubmed_client.py
    kb/
      evidence.py
      query.py
      schema.py
      writer.py
    llm/
      evidence_bundle.py
      router.py
      L6_SUMMARIZATION_LOGIC.md
    normalization/
      rule_based.py
    output/
      l7_answer.py
      L7_OUTPUT_CONTRACT.md
    retrieval/
      sqlite_service.py
      structured_query.py
      task_router.py
```

Current reading order:

1. `doc/system_design_v2.md`
2. `doc/data_flow_architecture.md`
3. `doc/unified_evidence_schema.md`
4. `src/contracts/`
5. `src/kb/`
6. `src/retrieval/`
7. `src/agent/`

## 8. Task Definitions

### Primary Task A: Gene-Disease Evidence (BioRED, Implemented v1)

Goal:

- Retrieve gene/protein and disease mentions from PubMed documents
- Persist relation evidence with PMIDs and selected supporting sentences

Primary dataset:

- `BioRED`

Primary outputs:

- `gene/protein`, `disease`, `relation type`, `PMID`, `evidence sentence`, `relation source`

Boundary:

- Three-table flow exists and is runnable: `papers`, `entities`, `relations`.
- Current live path is dataset-loader based (BioRED PubTator annotations), not yet a trained relation inference model.
- Current relation path includes both:
  - loader-based gold relation rows from BioRED PubTator files
  - trained baseline relation inference over BioRED entities

### Baseline Task B: Chemical-Disease Evidence (BC5CDR, Implemented)

Goal:

- Preserve the completed chemical-disease sentence-evidence pipeline as a baseline.

Boundary:

- `BC5CDR` does not train or evaluate gene extraction.

### Auxiliary Task C: Biomedical Entity Discovery (JNLPBA, Retained)

Goal:

- Extract broader biomedical entities from text
- Support later KB expansion and exploratory analysis

Primary dataset:

- `JNLPBA`

Primary outputs:

- `entity type`, `mention text`, `PMID`, `sentence`, `canonical entity ID` if available

## 9. How This Differs from Generic RAG

Compared with embedding-only RAG:

- Primary retrieval is relational evidence tuples, not only vector-nearest chunks
- Strong provenance from claim -> sentence -> PMID
- Deterministic, auditable SQL path

Compared with generic LLM chatbots:

- LLM is a constrained summarizer, not a knowledge generator
- Citation grounding is mandatory and machine-checkable
- No evidence means no claim
- Structured outputs are first-class artifacts for analysis pipelines

## 10. Implementation Priorities

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

## 11. Progress Tracker (Current Repository Snapshot)

Status legend:

- `DONE`: implemented and runnable in current repo
- `PARTIAL`: implemented in simplified form, not yet production-complete
- `NOT STARTED`: design exists but implementation absent

### 11.1 Layer Status

| Layer | Status | Current Evidence in Repo | Gap to Close |
|---|---|---|---|
| L0 Data (PubMed ingestion) | `DONE` | `src/ingestion/pubmed_client.py` supports PubMed search + abstract fetch + year/journal filters and is integrated in runnable task pipelines | Add persistent ingestion log/dedup/versioning if needed |
| L1 Extraction (Entity / Relation Extraction) | `PARTIAL` | `src/extraction/ner_infer.py` runs entity baselines; `src/extraction/biored_loader.py`, `src/extraction/biored_pipeline.py`, and `src/extraction/biored_relation_infer.py` cover the current BioRED relation path | Add a fully general new-abstract primary-task extraction path beyond current BioRED-centered inputs |
| L2 Normalization | `DONE` | `src/normalization/rule_based.py` loads local HGNC/MeSH/ChEBI alias CSVs, maps IDs/labels, and exposes confidence/source fields | Improve ambiguous-alias handling and version mapping snapshots |
| L3 Knowledge Base (SQLite) | `DONE` | `src/kb/schema.py`, `writer.py`, and `query.py` persist mentions/sentences plus BioRED `entity_relations` and `relation_provenance` | Add migration/version tracking and richer provenance metadata |
| L4 Retrieval | `DONE` | `src/retrieval/sqlite_service.py` supports mention, sentence evidence, and relation modes (`relation_pmid`, `relation_entity_pair`) | Add pagination/ranking for larger result sets |
| L5 Agent | `DONE` | `src/agent/controller.py` supports deterministic read/refresh for `bc5cdr`, `jnlpba`, and `biored` relation modes | Add multi-step planning and decision trace export |
| L6 LLM constrained summarization | `PARTIAL` | `src/llm/router.py` provides provider routing (`none/ollama/openai/anthropic/gemini`) with evidence-only fallback | Need full BYO provider clients, citation-level post-validation, and prompt/version governance |
| L7 Output layer | `PARTIAL` | `demo/app.py` table display + CSV export | No API JSON contract, no claim-level citation object |

### 11.2 Tool API Status

| Tool | Target in Design | Status | Current Equivalent |
|---|---|---|---|
| `search_pubmed(...)` | Required | `DONE` | `src/ingestion/pubmed_client.py::search_pubmed`, `fetch_pubmed_details` |
| `run_ner(...)` | Required | `DONE` | `src/extraction/ner_infer.py::ner`; `src/retrieval/structured_query.py` applies it across retrieved paper abstracts |
| `update_kb(...)` | Required | `DONE` | `src/kb/writer.py::write_pipeline_outputs_to_sqlite`; `pipelines/run_ingest_to_sqlite.py` |
| `query_kb(...)` | Required | `DONE` | `src/retrieval/sqlite_service.py::query_kb`; `pipelines/run_query_sqlite.py` |
| `get_evidence_sentences(...)` | Required | `DONE` | `src/kb/query.py::get_evidence_sentences_by_pmid`, `get_evidence_sentences_by_normalized_id`; exposed via L4 evidence modes |
| `get_gene_disease_relations(...)` | Primary BioRED task | `DONE` | `src/kb/query.py::get_relations_by_pmid`, `get_relations_by_entity_pair`; exposed via `src/retrieval/sqlite_service.py` |

### 11.3 Repo Structure Status

| Planned Module | Status |
|---|---|
| `src/ingestion/` | `PARTIAL` |
| `src/extraction/` | `PARTIAL` |
| `src/normalization/` | `DONE` |
| `src/kb/` | `DONE` |
| `src/retrieval/` | `DONE` |
| `src/agent/` | `DONE` |
| `src/llm/` | `PARTIAL` |
| `pipelines/` | `DONE` |
| `db/` | `NOT STARTED` |
| `tests/` | `DONE` |

### 11.4 Immediate Next Milestones

1. Improve relation-level provenance quality (better sentence selection and optional char-offset links).
2. Add explicit API contract for L7 claim-level citation objects.
3. Add provider-specific post-validation and citation checks for L6 summaries.
4. Add scalable query ergonomics (pagination/ranking) for larger BioRED evidence sets.

## 12. Reproducibility and Operations Notes

- Version all model artifacts (`model_version` in mentions)
- Store ingestion timestamps and query provenance
- Keep idempotent upsert pipelines
- Add regression tests for evidence grounding rules
- Log end-to-end query traces for auditability
