# System Architecture Diagram

This diagram is the quick orientation map for the platform.

## 1. Platform Overview

```mermaid
flowchart TB
    U[User Query<br/>gene / disease / keyword] --> A[Agent Router]
    A -->|evidence mode| B[BC5CDR Workflow]
    A -->|discovery mode| C[JNLPBA Workflow]

    subgraph Shared Platform
        D[PubMed Ingestion<br/>src/ingestion/pubmed_client.py]
        E[BioBERT NER<br/>src/extraction/ner_infer.py]
        F[Normalization Layer<br/>planned]
        G[SQLite Knowledge Base<br/>planned]
        H[Structured Retrieval<br/>src/retrieval/structured_query.py<br/>future SQL retrieval]
        I[LLM Summarizer<br/>planned]
        J[Output Layer<br/>UI / CSV / JSON]
    end

    B --> D --> E --> F --> G --> H --> I --> J
    C --> D --> E --> F --> G --> H --> I --> J
```

## 2. Task Split

```mermaid
flowchart LR
    P[Shared Platform] --> A1[Task A: BC5CDR]
    P --> B1[Task B: JNLPBA]

    A1 --> A2[Gene-Disease<br/>Evidence]
    A1 --> A3[PMID +<br/>Evidence Sentence]
    A1 --> A4[Evidence Type]

    B1 --> B2[Broader Entity<br/>Discovery]
    B1 --> B3[Gene / Protein / DNA / RNA<br/>/ Cell Line]
    B1 --> B4[Mention Table<br/>/ KB Expansion]
```

## 3. How To Read It

- `BC5CDR` is the evidence task used for association analysis.
- `JNLPBA` is the discovery task used for broader biomedical entity extraction.
- Both tasks share ingestion, retrieval, and storage infrastructure.
- The difference is mainly the model, label space, and output schema.

## 4. Current Status

- `PubMed ingestion`: implemented
- `BioBERT NER`: implemented
- `BC5CDR workflow`: implemented
- `JNLPBA workflow`: scaffold only
- `Normalization / KB / Agent / LLM layers`: planned
