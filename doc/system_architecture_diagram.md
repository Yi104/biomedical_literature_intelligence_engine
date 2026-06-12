# System Architecture Diagram

This diagram is the quick orientation map for the platform.

## 1. Platform Overview

```mermaid
flowchart TB
    U[User Query<br/>gene / disease / keyword] --> A[Agent Router]
    A -->|primary evidence mode| R[BioRED Workflow<br/>implemented local PubTator path]
    A -->|chemical baseline| B[BC5CDR Workflow<br/>implemented]
    A -->|discovery auxiliary| C[JNLPBA Workflow<br/>implemented]

    subgraph Shared Platform
        D[PubMed Ingestion<br/>src/ingestion/pubmed_client.py]
        E[BioBERT NER<br/>src/extraction/ner_infer.py]
        F[Normalization Layer<br/>implemented]
        G[SQLite Knowledge Base<br/>implemented]
        H[Structured Retrieval<br/>sentence evidence implemented]
        I[LLM Summarizer<br/>planned]
        J[Output Layer<br/>UI / CSV / JSON]
    end

    R --> K[BioRED Loader<br/>src/extraction/biored_loader.py]
    K --> F
    K --> G
    K --> H
    B --> D --> E --> F --> G --> H --> I --> J
    C --> D --> E --> F --> G --> H --> I --> J
```

## 2. Task Split

```mermaid
flowchart TD
    P[Shared Platform] --> R1[Primary: BioRED]
    P --> A1[Baseline: BC5CDR]
    P --> B1[Auxiliary: JNLPBA]

    R1 --> R2[Gene-Disease<br/>Relation Evidence]
    R1 --> R3[PMID +<br/>Evidence Sentence]
    A1 --> A2[Chemical-Disease<br/>Evidence]
    A1 --> A3[PMID +<br/>Evidence Sentence]
    A1 --> A4[Evidence Type]

    B1 --> B2[Broader Entity<br/>Discovery]
    B1 --> B3[Gene / Protein / DNA / RNA<br/>/ Cell Line]
    B1 --> B4[Mention Table<br/>/ KB Expansion]
```

## 3. How To Read It

- `BioRED` is the primary target because it contains gene/protein-disease relations.
- `BC5CDR` is a retained chemical-disease evidence baseline. It does not provide gene annotations.
- `JNLPBA` is a retained discovery task used for broader biomedical entity extraction.
- All task paths reuse ingestion, normalization, storage, and retrieval
  infrastructure where their data contracts overlap.
- The difference is mainly the model, label space, and output schema.

## 4. Current Status

- `PubMed ingestion`: implemented
- `BioBERT NER`: implemented
- `BC5CDR workflow`: implemented
- `JNLPBA workflow`: implemented baseline/smoke path
- `BioRED workflow`: local PubTator loader, three-table contract, relation persistence, and relation retrieval implemented
- `Normalization / KB / Agent layers`: implemented through sentence evidence
- `LLM layer`: evidence bundle plus `none` and Ollama path implemented; hosted BYO provider clients and citation post-validation remain planned
