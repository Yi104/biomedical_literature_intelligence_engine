# Research Plan: Structured Biomedical Literature Intelligence with BioBERT-Based Evidence Extraction

## 1. Project Goal

This project aims to develop and evaluate a biomedical literature intelligence system that converts PubMed abstracts into structured, citation-grounded evidence for gene-disease analysis. The central design choice is to move from unstructured text retrieval toward schema-aligned evidence extraction, where each system output is explicitly tied to a PMID and supporting sentence.

The target output is not a free-text summary. Instead, the system produces structured evidence records such as:

- `gene`
- `disease`
- `PMID`
- `evidence sentence`
- `evidence type`

These records can then be aggregated from paper-level evidence to gene-level evidence for downstream biomedical interpretation.

### Current Implementation Alignment Note

The selected primary dataset is now `BioRED`, because it includes
gene/protein, disease, and disease-gene relation annotations. The currently
implemented evidence baseline uses `BC5CDR`. This corpus is
annotated for **chemicals**, **diseases**, and chemical-disease relations; it
does not provide gene entity annotations. Therefore:

- BioRED is the primary path for the research question; the current repo
  implements local PubTator-based relation ingestion and retrieval
- the implemented BC5CDR path validates chemical-disease extraction and
  citation-grounded evidence storage
- trained BioRED relation inference and full evaluation remain implementation work

This distinction prevents chemical-disease baseline results from being
reported as gene-disease extraction performance.

Dataset reference:

- BioRED paper: https://pubmed.ncbi.nlm.nih.gov/35849818/
- BC5CDR corpus paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC4860626/

## 2. Research Questions

### RQ1

Can a BioBERT-based structured evidence extraction pipeline identify gene-disease associations from PubMed abstracts more accurately than a simple co-occurrence baseline and more reliably than a standard RAG pipeline?

### RQ2

Does constraining outputs to structured, citation-grounded evidence reduce hallucination and improve interpretability relative to free-form LLM-based generation?

These questions keep the project focused on performance, grounding, and practical value rather than on overly broad claims about full literature understanding.

## 3. Method Overview

The proposed system follows this pipeline:

1. Submit a gene and/or disease query to PubMed.
2. Retrieve the top `N` relevant abstracts.
3. Run BioBERT-based NER to identify biomedical entities.
4. Post-process extracted entities into structured evidence tuples.
5. Aggregate paper-level evidence into gene-level evidence.

The final system output is a structured evidence table rather than a generated narrative summary.

## 4. Comparison Systems

To demonstrate value rigorously, the project should compare three systems under a shared retrieval setting.

### 4.1 Shared Retrieval Setup

All methods should use:

- the same query set
- the same PubMed retrieval budget
- the same abstract-only corpus
- the same evaluation instances

This ensures that differences in performance come from the evidence extraction method rather than from unequal document access.

### 4.2 Baseline A: Co-occurrence / Keyword Matching

This baseline is designed to represent a simple but common information extraction heuristic.

Procedure:

1. Retrieve the top `N` abstracts for each query.
2. Mark a candidate association when the gene and disease co-occur in the same abstract or sentence.
3. Optionally require one trigger word from a small predefined lexicon such as:
   - `associated`
   - `mutation`
   - `expression`
   - `biomarker`
   - `prognostic`
   - `predictive`
4. Aggregate positive paper-level matches into a gene-level association decision.

Expected behavior:

- high recall
- low precision
- weak evidence specificity

### 4.3 Baseline B: Standard RAG

This baseline represents a typical retrieval-augmented generation setup.

Procedure:

1. Retrieve the same top `N` PubMed abstracts.
2. Build an embedding index over the retrieved abstracts or abstract sentences.
3. Retrieve top `k` passages for a query.
4. Prompt an LLM to answer whether a gene-disease association exists.
5. Require the model to return:
   - association yes/no
   - one supporting sentence
   - one PMID

Expected behavior:

- reasonable association detection
- stronger fluency than rule-based systems
- weaker citation reliability
- possible hallucinated claims or unsupported evidence

### 4.4 Proposed Method: Structured Evidence Extraction + Aggregation

Procedure:

1. Retrieve the same top `N` PubMed abstracts.
2. Run BioBERT NER to identify entities such as genes, diseases, and chemicals.
3. Use sentence-level post-processing to construct structured evidence tuples:
   - `(gene, disease, PMID, evidence sentence, evidence type)`
4. Aggregate paper-level tuples into a gene-level association decision.

The distinguishing feature is that every association is grounded in an explicit sentence and citation.

Expected behavior:

- stronger precision than co-occurrence
- lower hallucination than RAG
- better interpretability than both baselines

## 5. Dataset Construction

The dataset should be intentionally small but carefully curated. A realistic benchmark for a first paper is sufficient if annotation quality is high.

### 5.1 Scope

Recommended benchmark size:

- 30 to 50 genes
- one disease domain or one tightly related disease family

Examples of good starting domains:

- breast cancer
- non-small cell lung cancer
- colorectal cancer
- Alzheimer’s disease

Using one disease domain is preferable for the first paper because it reduces ontology ambiguity and makes annotation more consistent.

### 5.2 Instance Definition

Each evaluation instance is a `(gene, disease)` pair.

For each pair, the system will search PubMed and return structured evidence from retrieved abstracts.

### 5.3 Label Schema

Each `(gene, disease)` pair should be annotated with:

- `association`: `yes` or `no`
- `evidence_type`: `genetic`, `expression`, `clinical`, or `unknown`
- `supporting PMID`
- `supporting sentence`

Optional field:

- `directionality`: `positive`, `negative`, or `unclear`

Directionality is useful, but it should be treated as an optional extension rather than a core requirement for the initial paper.

### 5.4 Evidence Type Definition

Use a compact schema that is biologically meaningful and feasible to annotate:

- `genetic`: mutation, variant, SNP, amplification, deletion, rearrangement
- `expression`: overexpression, underexpression, elevated level, reduced level
- `clinical`: prognosis, diagnosis, treatment response, survival, risk stratification
- `unknown`: supporting evidence exists but does not clearly fit the above categories

### 5.5 Ground Truth Construction

A feasible manual curation strategy:

1. Select 30 to 50 genes from a disease-relevant source.
2. Include a mixture of:
   - well-established positive genes
   - borderline or weakly supported genes
   - likely negative genes
3. For each gene, retrieve top 20 to 30 PubMed abstracts using a fixed query template.
4. Have two annotators independently review the retrieved abstracts and assign:
   - association yes/no
   - best supporting sentence
   - evidence type
5. Resolve disagreements through adjudication.
6. Report inter-annotator agreement on at least a subset of instances.

This design keeps the dataset small but credible.

## 6. Evaluation Metrics

The evaluation should measure both task performance and trustworthiness.

### 6.1 Association Detection

At the gene-disease level:

- Precision
- Recall
- F1

This is the main performance result.

### 6.2 Paper-Level Evidence Detection

At the `(gene, disease, PMID)` level:

- Precision
- Recall
- F1

This evaluates whether the system retrieves not only the right association but also the right supporting papers.

### 6.3 Evidence Sentence Quality

Measure whether the predicted supporting sentence is genuinely valid evidence.

A sentence is counted as correct if:

- it exists in the cited PMID abstract
- it supports the claimed association according to the human annotation

Recommended metrics:

- sentence-level precision
- top-1 evidence accuracy

### 6.4 Citation Grounding Rate

Define citation grounding rate as:

> the proportion of system outputs whose cited PMID and evidence sentence are actually present in the retrieved corpus

This metric is important because it captures whether a method is grounded in real literature rather than unsupported generation.

### 6.5 Hallucination Rate

Define hallucination rate as:

> the fraction of predicted associations whose cited evidence does not support the claim, is missing from the cited abstract, or is fabricated

An output should be marked hallucinated if:

- the PMID does not contain the claimed support
- the evidence sentence is absent or mismatched
- the claim overstates what is actually supported in the abstract

This is expected to be especially useful for comparing the proposed method against the RAG baseline.

### 6.6 Evidence Type Classification

If evidence type is included, evaluate:

- macro F1 over `genetic`, `expression`, `clinical`, and `unknown`

This can be treated as a secondary analysis if annotation resources are limited.

## 7. Expected Results and Hypotheses

The proposed method is not expected to dominate every metric. The more realistic and credible claim is that it improves evidence quality and grounding.

### Expected outcome for Baseline A

- high recall
- low precision
- poor evidence specificity
- many false positives due to simple mention overlap

### Expected outcome for Baseline B

- moderate to strong association-level performance
- more fluent outputs
- lower citation reliability
- measurable hallucination rate

### Expected outcome for Proposed Method

- stronger precision than co-occurrence
- comparable or slightly lower recall than co-occurrence
- lower hallucination rate than RAG
- stronger citation grounding
- better evidence sentence correctness

The main scientific argument should be:

> structured extraction produces more auditable and trustworthy biomedical evidence than either lexical matching or free-form generation.

## 8. Paper Figures

The paper should include a small number of clear figures.

### Figure 1: System Pipeline

A schematic showing:

- query input
- PubMed retrieval
- BioBERT NER
- structured evidence extraction
- aggregation to gene-level evidence

### Figure 2: Main Results Comparison

A bar chart or grouped bar chart comparing:

- Precision
- Recall
- F1
- citation grounding rate
- hallucination rate

across:

- co-occurrence baseline
- RAG baseline
- proposed structured method

### Figure 3: Case Study

A concrete example showing:

- retrieved abstract snippet
- extracted evidence sentence
- structured tuple output
- a failure mode from one baseline

This figure is often more persuasive than an additional aggregate plot because it shows exactly what the system contributes.

## 9. Contribution Statement

The paper can frame its contributions as follows:

- We present a lightweight biomedical literature intelligence pipeline that converts PubMed abstracts into structured, citation-grounded evidence rather than free-text summaries.
- We propose an interpretable evidence extraction and aggregation framework for gene-disease association analysis using BioBERT-based NER and schema-constrained post-processing.
- We introduce a small manually curated benchmark for evaluating gene-disease association detection with sentence-level supporting evidence and evidence type labels.
- We show that structured evidence extraction improves citation grounding and reduces hallucination relative to standard retrieval-augmented generation.

## 10. Minimal Publishable Experimental Plan

The smallest realistic version of this project that can still support a bioRxiv-level paper is:

1. Choose one disease domain.
2. Curate 40 gene-disease instances.
3. Retrieve top 20 to 30 PubMed abstracts per instance.
4. Compare three methods:
   - co-occurrence
   - RAG
   - structured extraction
5. Report:
   - gene-level Precision, Recall, F1
   - paper-level evidence Precision, Recall, F1
   - evidence sentence accuracy
   - citation grounding rate
   - hallucination rate
6. Include one qualitative case study and a short failure analysis.

This setup is intentionally small enough to complete manually, while still making a clear methodological contribution.

## 11. Recommended Paper Framing

The most defensible framing for the paper is not that the system performs full biomedical reasoning. The more rigorous claim is:

> The system improves the conversion of retrieved biomedical abstracts into structured, interpretable, and citation-grounded evidence for downstream gene-disease analysis.

That framing is realistic, testable, and aligned with the strengths of the method.
