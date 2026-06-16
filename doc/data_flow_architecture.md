# Data Flow Architecture

This document explains the platform as a data flow system rather than only a
set of modules. Its main purpose is to answer four questions clearly:

1. what data object exists at each stage
2. where each contract lives
3. where one contract ends and another begins
4. where the unified evidence schema should be implemented

This is the reference to use when deciding where new code belongs.

## 1. Why This Document Exists

The repository already has:

- [System Architecture Diagram](system_architecture_diagram.md)
- [End-to-End Data Flow](end_to_end_data_flow.md)
- [Unified Evidence Schema](unified_evidence_schema.md)
- [Evidence Schema Refactor Plan](evidence_schema_refactor_plan.md)

Those documents are useful, but they answer different questions:

- system architecture: what components exist
- end-to-end flow: what the current implementation already does
- unified schema: what the target reusable evidence objects look like
- refactor plan: how to migrate code

What was still missing is one document that shows:

- the full data path
- the object transformations
- the contract boundaries between layers

That is the purpose of this file.

## 2. The Main Data Flow

At the highest level, the platform should be read as:

```text
source literature
  -> extraction outputs
  -> normalized records
  -> persisted KB rows
  -> retrieved evidence objects
  -> downstream evidence bundle
  -> answer / KB integration / agent use
```

The important point is that these are not all the same kind of data.

The other important point is portability: the unified evidence contract should
remain generic across biomedical relation domains. The platform may start with
gene-disease, but the target object model should also support drug-disease,
drug-target, variant-disease, biomarker-outcome, and related tasks without
changing the top-level bundle shape.

## 3. Flow by Layer

### L0. Source and Ingestion

Inputs:

- PubMed abstracts
- local BioRED PubTator files
- normalization vocabularies such as HGNC, MeSH, ChEBI

Outputs:

- source paper records
- local normalization mapping files

Main files:

- `src/ingestion/pubmed_client.py`
- `pipelines/build_normalization_mappings.py`

Primary runtime objects:

- raw paper metadata
- raw abstract text
- raw vocabulary files

Contract at this stage:

- no platform-level evidence contract yet
- this is source-data format, not repository-defined evidence format

### L1. Extraction

Inputs:

- paper abstracts or local BioRED document/entity inputs

Outputs:

- task-specific extracted mentions
- optional task-specific relation rows

Main files:

- `src/extraction/ner_infer.py`
- `src/extraction/bc5cdr_pipeline.py`
- `src/extraction/jnlpba_pipeline.py`
- `src/extraction/biored_pipeline.py`
- `src/extraction/biored_loader.py`
- `src/extraction/biored_relation_infer.py`

Primary runtime objects:

- `papers_df`
- `entities_df`
- `relations_df`

Contract at this stage:

- `extraction-layer contract`

Current contract definition:

- [src/contracts/task_output_schemas.py](/Users/yijin/Document/OMSCS_YJ_study/biobert_biomarker_ner/src/contracts/task_output_schemas.py)

Meaning:

- this contract tells extraction code what columns to output
- this contract is optimized for model pipelines and persistence
- this contract is not yet the final reusable evidence schema

### L2. Normalization

Inputs:

- extracted entity mentions
- local alias mappings

Outputs:

- enriched mention records with normalized IDs, labels, and scores

Main files:

- `src/normalization/rule_based.py`

Primary runtime objects:

- `entities_df` with:
  - `normalized_text`
  - `normalized_id`
  - `normalized_source`
  - `normalized_score`

Contract at this stage:

- still inside the `extraction-layer contract`

Meaning:

- normalization extends extraction outputs
- it still does not yet define reusable `Entity / Relation / Evidence / Provenance`
  objects

### L3. Persistence

Inputs:

- `papers_df`
- `entities_df`
- optional `relations_df`

Outputs:

- SQLite rows

Main files:

- `src/kb/schema.py`
- `src/kb/writer.py`

Primary persisted objects:

- `papers`
- `entity_mentions`
- `normalized_entities`
- `evidence_sentences`
- `evidence_sentence_mentions`
- `entity_relations`
- `relation_provenance`

Contract at this stage:

- `storage contract`

Meaning:

- this contract defines how data is stored and linked in SQLite
- it is shaped by database concerns: keys, uniqueness, indexes, joins
- it is not the same as the final downstream evidence object model

### L4. Retrieval

Inputs:

- SQLite rows

Outputs:

- query result payloads for mention, sentence, or relation evidence

Main files:

- `src/retrieval/sqlite_service.py`
- `src/kb/query.py`

Current retrieval modes:

- `pmid`
- `normalized_id`
- `type_keyword`
- `evidence_pmid`
- `evidence_normalized_id`
- `relation_pmid`
- `relation_entity_pair`

Current runtime objects:

- query result dictionaries
- relation rows with provenance lists
- sentence evidence rows with linked entities

Contract at this stage:

- `retrieval contract`

Meaning:

- retrieval contract defines what query functions return
- it is the transition point between storage-oriented rows and
  downstream-oriented evidence objects

This is the most important boundary in the current repo.

### L5. Agent / Orchestration

Inputs:

- user task
- retrieval mode
- filters
- optional refresh request

Outputs:

- structured agent result with evidence payload

Main files:

- `src/agent/controller.py`

Current runtime objects:

- L5 agent result
- `status`
- `filters`
- `count`
- `evidence`
- optional `refresh`

Contract at this stage:

- `agent response contract`

Meaning:

- L5 decides whether retrieval is enough or refresh is needed
- L5 should not own the final reusable evidence schema
- L5 should pass evidence payloads into the unified layer

### L6/L7 and Downstream Consumers

Inputs:

- evidence payload from L4/L5

Outputs:

- evidence bundle
- optional summary
- answer contract
- future export payload for `bioAI-target` or another KB platform

Main files:

- `src/llm/evidence_bundle.py`
- `src/output/l7_answer.py`

Contract at this stage:

- `evidence-layer contract`

This is where the unified contract belongs.

Meaning:

- this contract should be stable across:
  - local retrieval
  - LLM summarization
  - `bioAI-target`
  - other downstream KB integrations

Current state:

- this contract is only partially present today
- the new target definition is documented in
  [Unified Evidence Schema](unified_evidence_schema.md)

## 4. Contract Map

The easiest way to understand the system is to track where each contract lives.

| Stage | Main object shape | Contract name | Where defined now |
| --- | --- | --- | --- |
| L1-L2 | `papers_df`, `entities_df`, `relations_df` | extraction-layer contract | `src/contracts/task_output_schemas.py` |
| L3 | SQLite tables and joins | storage contract | `src/kb/schema.py` |
| L4 | query result rows and mode-specific payloads | retrieval contract | `src/retrieval/sqlite_service.py`, `src/kb/query.py` |
| L5 | agent result payload | agent response contract | `src/agent/controller.py` |
| L6-L7 and downstream | `Document / Entity / Relation / Evidence / Provenance` | evidence-layer contract | target: `src/contracts/unified_evidence_schema.py` |

## 5. Where the Unified Evidence Contract Belongs

This is the part that tends to cause confusion.

The unified evidence contract does **not** belong:

- inside model training code
- inside raw dataframe column definitions
- inside SQLite schema only

It belongs at the boundary between:

- retrieval/agent outputs
- downstream evidence consumers

In practice:

```text
L4 retrieval rows
  -> adapter layer
  -> unified evidence bundle
  -> L6/L7 / bioAI-target / other KB systems
```

That is why the first implementation targets should be:

- `src/contracts/unified_evidence_schema.py`
- `src/contracts/evidence_adapters.py`

not training code.

## 6. The Adapter Layer

The adapter layer is the missing bridge in the current architecture.

Its job is:

1. read current retrieval output or task output
2. convert it into unified objects
3. hide task-specific shape differences from downstream systems

Target location:

- `src/contracts/evidence_adapters.py`

Target responsibilities:

- row-to-entity conversion
- row-to-relation conversion
- sentence-to-evidence conversion
- provenance conversion
- unified bundle assembly

Without this layer, downstream code keeps depending on ad hoc row shapes.

## 7. End-to-End Object Evolution

The same biomedical fact changes shape multiple times as it moves through the
system.

Example:

### Step A: extraction output

```text
entities_df row:
pmid=10788334
entity_text=BRCA1
entity_type=GeneOrGeneProduct
token_start=120
token_end=125
normalized_id=672
```

### Step B: persistence row

```text
entity_mentions row:
mention_id=42
pmid=10788334
entity_text=BRCA1
normalized_id=672
```

### Step C: retrieval result

```text
relation query row:
pmid=10788334
relation_type=Association
entity1_normalized_id=672
entity2_normalized_id=D001943
provenance=[...]
```

### Step D: unified evidence object

```json
{
  "relation_id": "rel:10788334:672:D001943:Association",
  "pmid": "10788334",
  "type": "Association",
  "subject": {
    "normalized_id": "672"
  },
  "object": {
    "normalized_id": "D001943"
  },
  "extraction": {
    "source": "biored_model_v1",
    "confidence": 0.91
  }
}
```

The key point is:

- extraction output is for models
- persistence output is for storage
- retrieval output is for queries
- unified evidence output is for platform interoperability

In particular, the unified relation object should not hardcode fields such as
`gene_id` or `disease_id`. It should continue to use generic endpoints such as
`subject` and `object`, with type labels carried inside those endpoint objects.

## 8. Current Gaps in the Flow

The repository already has most structural pieces, but these gaps remain:

1. `Relation` exists, but is still too BioRED-specific
2. `Evidence` exists as stored sentences, but not yet as a fully first-class
   evidence object
3. `Provenance` exists, but is too weak:
   - sentence text exists
   - char offsets do not
   - linking method is not explicit
4. evidence scoring is not yet a true platform-level concept
5. unified evidence bundle is not yet the default downstream payload

## 9. Recommended Mental Model

When deciding where new work should go, use this rule:

- if it changes model outputs, it belongs to extraction
- if it changes how rows are stored, it belongs to persistence
- if it changes what SQL/query functions return, it belongs to retrieval
- if it changes what downstream systems consume, it belongs to the evidence layer

Short version:

```text
models produce rows
KB stores rows
retrieval returns rows
adapter builds evidence objects
downstream systems consume evidence objects
```

## 10. Implementation Landing Points

If the goal is to make the data flow architecture real in code, the first files
to implement are:

1. `src/contracts/unified_evidence_schema.py`
2. `src/contracts/evidence_adapters.py`
3. `src/llm/evidence_bundle.py`
4. `src/output/l7_answer.py`

Then move downward into:

5. `src/retrieval/sqlite_service.py`
6. `src/kb/query.py`
7. `src/kb/schema.py`
8. `src/kb/writer.py`

This order follows the actual contract boundary where the architecture is most
useful.
