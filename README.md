# PubMed Biomarker Search + NER

## What This App Is For

This project helps you do one workflow:

1. Search PubMed with a gene or disease keyword  
2. Retrieve paper metadata + abstract  
3. Run BioBERT NER on each abstract  
4. Get structured outputs for downstream analysis (table + CSV)

This is useful when you want to quickly build a candidate evidence set for biomarker analysis.

## What You Input

- A keyword query (examples: `BRCA1 breast cancer`, `EGFR lung adenocarcinoma`)
- Number of papers to retrieve
- Year range (`Year from`, `Year to`)
- Journal filter (optional, exact journal name)
- Model path (default: `outputs/best_model`)

## What You Get

The app returns two tables:

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
- Entity quality depends on your trained model in `outputs/best_model`.

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
2. In **Search keyword**, enter gene/disease query.  
3. Set **Number of papers**.  
4. Click **Search and Extract**.  
5. (Optional) Apply entity filters:
   - choose entity types
   - set minimum entities per paper  
6. Review the two tables and download CSV for analysis.

## Recommended Query Patterns

- `GENE disease` (e.g., `TP53 ovarian cancer`)
- `disease biomarker`
- Add context words: `prognosis`, `diagnosis`, `therapy response`

## Files and Roles

- `demo/app.py`: Streamlit user interface
- `src/pubmed.py`: PubMed search + fetch
- `src/pipeline.py`: end-to-end pipeline (`query -> papers -> ner -> tables`)
- `src/infer.py`: model inference and entity aggregation
- `src/train.py`: training pipeline for model

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

```bash
python -m src.train
```

Artifacts:
- Best model: `outputs/best_model/`
- Metrics: `outputs/reports/test_metrics.json`
