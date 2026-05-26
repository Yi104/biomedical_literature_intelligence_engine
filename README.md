# PubMed Biomedical Evidence Extraction

## What This App Is For

The project target is gene-disease evidence extraction with `BioRED`.
The currently runnable backend baselines are retained while the BioRED
relation path is implemented:

| Dataset | Role | Status |
| --- | --- | --- |
| `BioRED` | Primary gene/protein-disease relation evidence | Smoke contract added; live pipeline pending |
| `BC5CDR` | Chemical-disease evidence baseline | Runnable through sentence-evidence retrieval |
| `JNLPBA` | Broader entity-discovery auxiliary path | Retained |

Shared backend flow:

```text
PubMed -> extraction -> normalization -> SQLite -> sentence evidence -> L5 controller
```

## What You Input

- A primary-task query (BioRED smoke example: `BRCA1 breast cancer`)
- A runnable baseline query (BC5CDR example: `cisplatin kidney diseases`)
- Number of papers to retrieve
- Year range (`Year from`, `Year to`)
- Journal filter (optional, exact journal name)
- Model path for currently trained task artifacts

## What You Get

The current runnable BC5CDR/JNLPBA UI paths return two tables:

1. **Papers table**
   - `pmid`, `title`, `journal`, `year`, `abstract`
   - `entity_count` (how many entities detected)
   - `entity_types` (type summary, e.g. `Disease:3, Chemical:1`)

2. **Entities table**
   - `pmid`
   - `entity_type`
   - `entity_text`
   - `token_start`, `token_end`

Both tables can be downloaded as CSV.

The BioRED primary-task contract adds a third `relations` table for
gene/protein-disease evidence. That table is available in the smoke contract
now and will reach the UI after relation persistence and retrieval are added.

## How to Interpret Labels (`entity_type` vs `label_id`)

- `entity_type`: readable category for analysis (use this in downstream work)
- `label_id`: internal numeric class index from model output

`label_id` does not carry biological meaning by itself.  
It must be interpreted through model mapping (`id2label`).

BIO convention:
- `B-XXX`: beginning of entity
- `I-XXX`: continuation of entity
- `O`: non-entity token

For detailed explanation, see [LABEL_GUIDE.md](LABEL_GUIDE.md).

## Scope and Limits

- This app does **retrieval + NER extraction**, not ranking biomarkers by biological validity.
- It uses abstract text only (not full-text articles).
- BioRED live relation extraction is not implemented yet.
- BC5CDR entity quality depends on a valid Chemical/Disease model artifact.

## Quick Start

From repo root:

```bash
cd /path/to/biobert_biomarker_ner
```

Create a clean environment (recommended):

```bash
conda create -n biomarker310 python=3.10 -y
conda activate biomarker310
pip install -r requirements.txt
```

Run app:

```bash
python -m streamlit run demo/app.py --server.port 8502
```

Open:

`http://localhost:8502`

## How To Use the App (Step-by-Step)

1. In **Model checkpoint path**, keep `outputs/best_model` (or set your own model folder).  
2. In **Search keyword**, enter a chemical/disease query for the BC5CDR model.
3. Set **Number of papers**.  
4. Click **Search and Extract**.  
5. (Optional) Apply entity filters:
   - choose entity types
   - set minimum entities per paper  
6. Review the two tables and download CSV for analysis.

## Recommended BC5CDR Query Patterns

- `CHEMICAL disease` (e.g., `cisplatin kidney diseases`)
- `drug adverse event`
- Add context words: `toxicity`, `induced`, `treatment`

## Files and Roles

- `demo/app.py`: Streamlit user interface
- `src/ingestion/pubmed_client.py`: PubMed search + fetch
- `src/extraction/biored_pipeline.py`: primary gene-disease task contract scaffold
- `src/extraction/bc5cdr_pipeline.py`: retained chemical-disease evidence baseline
- `src/extraction/jnlpba_pipeline.py`: retained biomedical entity discovery path
- `src/retrieval/structured_query.py`: shared query-time pipeline (`query -> papers -> ner -> tables`)
- `src/extraction/ner_infer.py`: model inference and entity aggregation
- `src/extraction/train_ner.py`: NER training pipeline
- `pipelines/run_train.py`, `pipelines/run_eval.py`: runnable training/evaluation entrypoints
- `pipelines/run_extract_bc5cdr.py`, `pipelines/run_extract_jnlpba.py`: task-specific entrypoints
- `doc/system_architecture_diagram.md`: quick architecture diagram
- `doc/end_to_end_data_flow.md`: Mermaid diagrams and tables tracing data from mappings through the L5 evidence bundle
- `doc/sentence_level_evidence_upgrade.md`: L3-L5 v1.1 upgrade record for citation-ready source sentences
- `doc/biored_primary_task_transition.md`: primary task migration and BioRED relation contract

## Troubleshooting

### 1) `ModuleNotFoundError: No module named 'src'`
Run from project root with:

```bash
python -m streamlit run demo/app.py
```

### 2) Streamlit page says disconnected / cannot connect
- Ensure the terminal process is still running.
- Restart on a different port:

```bash
python -m streamlit run demo/app.py --server.port 8503
```

### 3) `seqeval` install fails in Python 3.13
Use Python 3.10/3.11 environment as shown above.

### 4) No papers or no entities returned
- Try broader query terms.
- Increase paper count.
- Check that model path points to a valid trained checkpoint.

## Optional: Retrain the NER Model

These commands and artifacts currently cover the retained NER baseline paths.
The live BioRED relation model/data path is not implemented yet.

```bash
python -m pipelines.run_train
```

Artifacts:
- BC5CDR best model: `outputs/best_model/`
- JNLPBA best model: `outputs/best_model_jnlpba/`
- BC5CDR reports: `outputs/reports/bc5cdr/`
- JNLPBA reports: `outputs/reports/jnlpba/`

Config files:
- `configs/bc5cdr.json`
- `configs/jnlpba.json`

## Task Entrypoints

Primary Task A, gene-disease relation evidence (`BioRED`):

```bash
python -m pipelines.run_extract_biored --smoke
```

Current status:
- This command establishes the required `papers + entities + relations` output contract.
- Live BioRED dataset/model ingestion is the next implementation phase.
- BioRED is not yet connected to `run_agent_query`, because the SQLite
  relation table is not implemented yet.

Baseline Task B, chemical-disease evidence (`BC5CDR` labels chemicals and diseases, not genes):

```bash
python -m pipelines.run_extract_bc5cdr --query "cisplatin kidney diseases"
```

Local smoke check for the BC5CDR baseline:

```bash
python -m pipelines.run_extract_bc5cdr --smoke
```

Important BC5CDR boundary:
- The BC5CDR model must expose BIO labels for `Chemical` and `Disease`.
- It cannot be used as a gene-disease NER model.
- A saved model with only generic labels such as `LABEL_0` is rejected during
  live BC5CDR execution because downstream normalization cannot interpret it.

Auxiliary Task C, biomedical entity discovery workflow:

```bash
python -m pipelines.run_extract_jnlpba --query "IL-2 gene expression"
```

Local smoke check for the JNLPBA auxiliary path:

```bash
python -m pipelines.run_extract_jnlpba --smoke
```

## Baseline Export (BC5CDR Chemical-Disease)

Export a fixed BC5CDR baseline snapshot for regression checks:

```bash
python -m pipelines.run_export_bc5cdr_baseline
```

Generated files:
- `outputs/reports/baseline_bc5cdr_papers.csv`
- `outputs/reports/baseline_bc5cdr_entities.csv`

## Baseline Export (JNLPBA Auxiliary)

Export a fixed JNLPBA baseline snapshot for regression checks:

```bash
python -m pipelines.run_export_jnlpba_baseline --smoke
```

Generated files:
- `outputs/reports/baseline_jnlpba_papers.csv`
- `outputs/reports/baseline_jnlpba_entities.csv`

## Normalization Mappings

Build normalization mapping CSVs from downloaded raw sources (`HGNC`, `MeSH`, `ChEBI`):

```bash
python -m pipelines.build_normalization_mappings
```

Default outputs:
- `data/processed/normalization/gene_aliases.csv`
- `data/processed/normalization/disease_aliases.csv`
- `data/processed/normalization/chemical_aliases.csv`

Disease filtering (default is already enabled):
- Keeps only MeSH descriptor tree prefixes `C` and `F03` for disease aliases.

Override disease tree prefixes:

```bash
python -m pipelines.build_normalization_mappings --disease_tree_prefixes C
```

Override output directory:

```bash
python -m pipelines.build_normalization_mappings --outdir data/processed/normalization
```

## SQLite KB

Initialize SQLite schema:

```bash
python -m pipelines.run_init_sqlite
```

Ingest Task pipeline outputs into SQLite:

```bash
python -m pipelines.run_ingest_to_sqlite --task bc5cdr --smoke
python -m pipelines.run_ingest_to_sqlite --task jnlpba --smoke
```

Query SQLite KB:

```bash
python -m pipelines.run_query_sqlite --mode pmid --pmid SMOKE001
python -m pipelines.run_query_sqlite --mode normalized_id --normalized_id CHEBI:27899
python -m pipelines.run_query_sqlite --mode type_keyword --entity_type Chemical --keyword cisplatin
python -m pipelines.run_query_sqlite --mode evidence_pmid --pmid SMOKE001 --task bc5cdr
python -m pipelines.run_query_sqlite --mode evidence_normalized_id --normalized_id CHEBI:27899 --task bc5cdr
```

Query output contract:
- JSON payload with `mode`, `filters`, `count`, `results`

Sentence evidence upgrade note:
- Databases created before sentence evidence support must be populated again
  by rerunning the relevant `run_ingest_to_sqlite` command before
  `evidence_pmid` or `evidence_normalized_id` queries return rows.

Live BC5CDR refresh also requires a valid trained model folder. If the model
is outside this repository, pass it explicitly:

```bash
python -m pipelines.run_agent_query --task bc5cdr --mode evidence_normalized_id --normalized_id CHEBI:27899 --query "cisplatin kidney diseases" --allow_refresh --model_path /path/to/valid/bc5cdr_model
```

## L5 Agent Controller

The L5 v1 controller provides a deterministic evidence workflow over the
SQLite KB for the currently persisted BC5CDR/JNLPBA paths. It does not
generate biomedical answers or call an LLM. BioRED will be wired here after
relation storage and retrieval are implemented.

Read existing KB evidence only:

```bash
python -m pipelines.run_agent_query --task bc5cdr --mode normalized_id --normalized_id CHEBI:27899
```

Run a local smoke refresh through the BC5CDR pipeline, write results to
SQLite, then query sentence-level evidence:

```bash
python -m pipelines.run_agent_query --task bc5cdr --mode evidence_pmid --pmid SMOKE001 --query "cisplatin kidney diseases" --allow_refresh --smoke
```

Controller output includes:
- `status`, such as `evidence_found`, `insufficient_evidence`, or `refreshed_and_found`
- `evidence`, containing mention rows or sentence records with linked entities, depending on mode
- `refresh`, containing inserted SQLite row counts, including `evidence_sentences_added`, when a refresh is run

Design notes:
- `src/agent/L5_AGENT_LOGIC.md`
- `doc/end_to_end_data_flow.md`
- `doc/sentence_level_evidence_upgrade.md`
- `doc/biored_primary_task_transition.md`

## Module Smoke Checks (Old-school)

Run each core module directly:

```bash
python -m src.ingestion.pubmed_client --query "cisplatin kidney diseases" --retmax 3
python -m src.extraction.data --dataset bc5cdr --max_length 128
python -m src.extraction.train_ner --dry_run
python -m pipelines.run_extract_biored --smoke
python -m src.retrieval.structured_query --query "cisplatin kidney diseases" --retmax 3
python -m src.extraction.bc5cdr_pipeline --smoke
python -m src.extraction.jnlpba_pipeline --query "IL-2 gene expression"
```

## Unit Tests

Run minimal unit tests:

```bash
python -m pytest -q tests/unit
```

Current unit tests focus on:

- PubMed XML parsing (mocked)
- Retrieval pipeline assembly (mocked)
- BIO span-to-entity merge behavior
- Unified task output schema regression (BioRED + BC5CDR + JNLPBA contract checks)
- L5 controller query/refresh decision flow and local smoke ingestion
- L3-L5 sentence evidence storage, linking, and retrieval contract

Schema contract source:
- `src/contracts/task_output_schemas.py` (shared definitions)
- `src/contracts/registry.py` (versioned registry, e.g. `biored:v1`, `bc5cdr:v1`, `jnlpba:v1`)
