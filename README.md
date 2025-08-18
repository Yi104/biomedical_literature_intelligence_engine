# BioBERT Biomarker NER

Fine-tune BioBERT for biomedical NER (JNLPBA/BC5CDR) to extract biomarker-relevant entities.

## Quickstart
```bash
conda create -n biomarker-env python=3.10 -y
conda activate biomarker-env
pip install -r requirements.txt
pip install --upgrade pip

# python src/train.py
```

### Environment Setup

This project provides both Conda (`env.yaml`) and pip (`requirements.txt`) options.

### Option A: Conda (recommended)
```bash
conda env create -f env.yaml
conda activate biomarker-env
```
### Option B: pip/venv
```bash
python -m venv .venv
source .venv/bin/activate   # Mac/Linux
# .venv\Scripts\activate    # Windows
pip install -r requirements.txt
```



See `notebooks/` for exploration and error analysis.
