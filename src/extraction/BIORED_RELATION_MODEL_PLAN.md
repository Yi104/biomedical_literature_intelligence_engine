# BioRED Relation Model Plan (v1)

This file is the implementation plan for training a BioRED relation prediction model
that can generalize to new PubMed text (not only loader-based gold annotations).

## 1. Target Task

Primary target:

- Relation classification for entity pairs in biomedical text.
- First milestone can be:
  - `gene/protein <-> disease` only, or
  - full BioRED relation label set.

Recommended first milestone:

- Start with `gene/protein <-> disease` subset.
- Keep other entity types for later expansion.

## 2. Training Unit

Use pair-classification examples.

One training sample = `(context, head_entity, tail_entity, label)`.

Recommended context unit:

- sentence-level candidate pairs first (faster and cleaner baseline),
- then extend to document-level modeling if needed.

## 3. Positive/Negative Sample Construction

## 3.1 Positive Samples

From BioRED annotations:

- For each labeled relation row:
  - take its `(pmid, concept_1, concept_2, relation_type)`.
  - map concepts back to entity mentions.
  - pick an evidence sentence (same approach used in current pipeline).

Output label:

- `label = relation_type` (multi-class), or
- `label = 1` for binary relation-vs-no-relation baseline.

## 3.2 Negative Samples (Where to Get Them)

Use **in-dataset unlabeled candidate pairs** from BioRED itself.

For each document (or sentence):

1. Enumerate candidate entity pairs from allowed type combinations.
2. Remove all pairs that appear in gold relation annotations.
3. Remaining pairs are negative candidates (`No_Relation`).

This is the standard source of negatives for supervised relation extraction.
You do not need an external negative dataset.

## 3.3 Negative Sampling Ratio

Both are fine:

- `1:1`: simple and stable baseline.
- `1:2`: often improves robustness without exploding imbalance.

Recommended start:

- train with `1:1`,
- compare with `1:2`,
- keep whichever improves dev F1 (especially for minority classes).

## 3.4 Hard Negative Option (Later)

After first baseline:

- prioritize negatives with high lexical overlap or same entity types as positives,
- this improves boundary cases and reduces false positives.

## 4. Input Encoding

Use BioBERT encoder with entity-aware text formatting.

Two practical formats:

1. Marker-in-context (recommended):
   - Insert markers around head/tail mentions in sentence.
   - Example:
     - `[E1] BRCA1 [/E1] ... [E2] breast cancer [/E2]`

2. Triple-segment format:
   - `[CLS] sentence [SEP] head_mention [SEP] tail_mention [SEP]`

Classifier head:

- linear classification layer on `[CLS]` embedding.

## 5. Data Split and Leakage Control

- Keep BioRED official split boundaries (`Train` / `Dev` / `Test`).
- Do not mix PMIDs across splits.
- Build negatives within each split separately.

## 6. Evaluation

Minimum metrics:

- micro F1
- macro F1
- per-class F1

Also track:

- confusion matrix
- precision/recall for key relation classes

## 7. Integration with Current Pipeline

Map prediction output to existing relation contract:

- `pmid`
- `relation_type`
- `entity1_text`, `entity1_type`, `entity1_normalized_id`
- `entity2_text`, `entity2_type`, `entity2_normalized_id`
- `evidence_sentence`
- `relation_source = biored_model_v1`
- optional confidence score

Then reuse existing L3/L4/L5/L6/L7 path already implemented.

## 8. Execution Plan (Concrete)

1. Build dataset constructor:
   - `src/extraction/biored_relation_data.py`
   - output train/dev/test pair examples with selectable negative ratio.

2. Build trainer:
   - `src/extraction/train_relations.py`
   - BioBERT + classifier head.

3. Add pipeline entry:
   - `pipelines/run_train_relations.py`

4. Add quick smoke test:
   - very small sample subset to validate data and forward pass.

## 9. First Experiments to Run

1. Binary baseline (`relation` vs `no_relation`), ratio `1:1`.
2. Binary baseline, ratio `1:2`.
3. Multi-class relation baseline, ratio `1:1`.

Pick the best dev setup, then scale training.
