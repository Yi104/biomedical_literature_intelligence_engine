# 4B Tracking

This file tracks the live PubMed evidence-extraction path for the primary
BioRED-style application goal.

Scope of `4B`:

```text
PubMed abstract
  -> entity extraction
  -> normalization
  -> candidate pair generation
  -> evidence sentence selection
  -> relation inference
  -> structured evidence output
```

`L5`, `L6`, and `L7` are not the main accuracy bottleneck for this stage.
They remain downstream packaging and delivery layers. The main focus here is
improving extraction quality before evidence reaches those layers.

## 1. Research Alignment

This document maps directly to `doc/research_plan.md`, especially:

- Method Overview step 3:
  `Run BioBERT-based NER to identify biomedical entities.`
- Method Overview step 4:
  `Post-process extracted entities into structured evidence tuples.`

In application terms, `4B` is the part most responsible for whether the system
actually extracts useful biomedical evidence from new literature.

## 2. Current State

Implemented:

- `4A` local BioRED corpus relation inference using PubTator entities
- BioRED relation classifier baseline
- SQLite relation persistence and retrieval
- `L5` / `L6` / `L7` downstream flow
- console logging and persistent run logs/manifests

Not yet stable enough:

- live PubMed gene/disease entity extraction path
- live normalization quality for gene/disease entities
- candidate pair quality on newly retrieved abstracts
- evidence sentence quality on live text
- end-to-end relation accuracy on live PubMed literature

## 3. Main Accuracy Bottlenecks

### 3.1 Entity Extraction

Question:
- Are the right gene and disease mentions being extracted from live PubMed abstracts?

Typical failure modes:
- missed gene mentions
- missed disease mentions
- wrong entity boundaries
- wrong entity type assignment

Why it matters:
- If entities are wrong, every later step becomes unreliable.

### 3.2 Normalization

Question:
- Are extracted mentions being mapped to the correct canonical IDs?

Typical failure modes:
- unresolved mentions
- alias ambiguity
- wrong canonical mapping

Why it matters:
- Wrong normalization corrupts both candidate pairs and retrieval.

### 3.3 Candidate Pair Generation

Question:
- Are we generating the right gene-disease candidates without exploding noise?

Typical failure modes:
- too many irrelevant pairs
- missing true pairs
- pairing mentions that never belong together semantically

Why it matters:
- The relation classifier quality depends heavily on candidate quality.

### 3.4 Evidence Sentence Selection

Question:
- Is the sentence passed to relation inference actually the best evidence sentence?

Typical failure modes:
- selecting a sentence that contains both entities but not the relation
- selecting a weak context sentence when a stronger one exists
- selecting first-match sentences that are structurally poor inputs

Why it matters:
- Relation classification is only as good as the text span it sees.

### 3.5 Relation Inference on Live Text

Question:
- Does the trained classifier generalize from BioRED annotation style to live PubMed retrieval outputs?

Typical failure modes:
- false positives on co-mentioned but unrelated pairs
- false negatives on indirect or complex phrasing
- overconfidence on noisy candidate pairs

Why it matters:
- This is the last algorithmic step before structured evidence becomes user-visible.

## 4. Tracking Table

| Area | Current status | Main risk | Priority |
| --- | --- | --- | --- |
| Entity extraction | Partial / unstable for live PubMed | recall and type errors | High |
| Normalization | Partial | wrong IDs or unresolved mentions | High |
| Candidate generation | Basic | noisy pair explosion | High |
| Evidence sentence selection | Basic first-match strategy | weak classifier input | High |
| Relation inference | Baseline exists | domain shift on live PubMed | Medium |
| L5/L6/L7 packaging | Implemented | not the main accuracy limiter | Low |

## 5. Recommended Order of Work

### Phase 1: Audit the live entity path

Goal:
- understand what is failing before relation inference

Check:
- gene recall
- disease recall
- normalization hit rate
- unresolved mention rate

Success signal:
- clear failure categories rather than vague "4B accuracy is low"

### Phase 2: Audit tuple construction quality

Goal:
- measure whether structured evidence tuples are being built from the right inputs

Check:
- candidate count per paper
- proportion of candidates reaching relation inference
- evidence sentence quality
- obvious noisy pairs

Success signal:
- candidate and evidence quality become measurable

### Phase 3: Audit relation inference on live PubMed

Goal:
- separate classifier mistakes from upstream extraction mistakes

Check:
- false positive examples
- false negative examples
- confidence distribution
- threshold sensitivity

Success signal:
- know whether the next improvement should target classifier, threshold, or upstream extraction

## 6. Immediate Next Experiments

### Experiment A: Live entity-path error audit

Input:
- 5 to 10 retrieved abstracts from one disease domain

Review:
- extracted genes
- extracted diseases
- normalized IDs

Output:
- a short error table:
  - missed entity
  - wrong type
  - wrong normalization

### Experiment B: Candidate-pair audit

Input:
- same abstracts as Experiment A

Review:
- all generated gene-disease pairs
- whether each pair is plausible

Output:
- counts for:
  - total candidates
  - plausible candidates
  - obvious noise candidates

### Experiment C: Evidence-sentence audit

Input:
- same candidate pairs

Review:
- selected evidence sentence for each candidate
- whether a better sentence exists in the abstract

Output:
- proportion of usable evidence sentences

### Experiment D: Relation-inference audit

Input:
- candidate pairs and selected evidence sentences

Review:
- predicted label
- confidence
- whether prediction matches manual judgment

Output:
- error slices:
  - upstream extraction failure
  - sentence-selection failure
  - classifier failure

## 7. Decision Rule

Before changing the relation classifier again, answer these questions:

1. Are entity extraction and normalization already good enough?
2. Are candidate pairs reasonably clean?
3. Are selected evidence sentences actually informative?

If the answer to any of these is `no`, improve the upstream `4B` path first.
Do not blame the classifier too early.

## 8. Logging and Records

Use the persistent logs and manifests when running `4B` experiments:

```text
outputs/logs/<command_name>/<timestamp>/
```

Use `doc/change_log.md` for major behavioral changes.

Use this file for tracking the audit and improvement roadmap itself.
