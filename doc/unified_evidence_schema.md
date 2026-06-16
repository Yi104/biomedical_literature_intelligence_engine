# Unified Evidence Schema (V1 Proposal)

## Purpose

This document defines the target intermediate contract for turning biomedical
literature into reusable evidence objects that can support:

- `bioAI-target`
- local SQLite retrieval
- downstream knowledge base ingestion
- evidence-grounded QA and agent workflows

The goal is not to replace task-specific extraction outputs immediately. The
goal is to introduce a stable evidence-layer contract that sits above raw
`papers_df / entities_df / relations_df` outputs and above task-specific model
details.

## Scope

This schema is designed for the current repository boundary:

- biomedical literature in, primarily PubMed abstracts
- normalized mentions, relations, and evidence out
- provenance retained at PMID and sentence level
- optional scoring retained separately from raw extraction output

Out of scope for this schema:

- final knowledge graph ontology design
- graph reasoning or multi-hop inference
- UI-specific rendering shape
- clinical decision support

## Design Principles

1. Keep evidence objects independent from any one model backend.
2. Separate relation statements from the evidence that supports them.
3. Treat provenance as a first-class object, not an incidental string field.
4. Preserve current repository capabilities while leaving room for stronger
   offsets, ranking, and multi-evidence aggregation.
5. Make the contract portable to other knowledge base systems.

## Core Objects

The minimum portable contract contains four primary object types:

1. `Entity`
2. `Relation`
3. `Evidence`
4. `Provenance`

An optional fifth object, `Document`, is included because the current codebase
already treats papers as first-class records.

## 1. Document

Represents the source literature record.

```json
{
  "document_id": "pmid:10788334",
  "pmid": "10788334",
  "title": "Example title",
  "year": "2000",
  "journal": "Example Journal",
  "abstract": "Abstract text",
  "source": "pubmed"
}
```

Required fields:

- `document_id`
- `pmid`
- `source`

Current repository mapping:

- SQLite table: `papers`

## 2. Entity

Represents a mention plus its normalization payload.

```json
{
  "entity_id": "entity:10788334:Gene:120:125:BRCA1",
  "pmid": "10788334",
  "document_id": "pmid:10788334",
  "text": "BRCA1",
  "type": "GeneOrGeneProduct",
  "mention_span": {
    "token_start": 120,
    "token_end": 125,
    "char_start": null,
    "char_end": null
  },
  "normalized": {
    "id": "672",
    "label": "BRCA1",
    "source_vocab": "HGNC",
    "method": "rule_based_v1",
    "score": 0.98
  }
}
```

Required fields:

- `entity_id`
- `pmid`
- `text`
- `type`

Recommended fields:

- `mention_span.token_start`
- `mention_span.token_end`
- `normalized.id`
- `normalized.label`

Notes:

- `char_start` and `char_end` should be nullable in V1 because the current
  extraction path does not guarantee source-text character offsets.
- `entity_id` can be deterministic and derived from PMID, type, span, and text.

Current repository mapping:

- SQLite table: `entity_mentions`
- lookup table: `normalized_entities`
- current task contracts:
  - `COMMON_ENTITIES_COLUMNS_V2`

## 3. Relation

Represents a structured statement between two normalized entities. It is not
the same thing as evidence.

```json
{
  "relation_id": "rel:10788334:672:D001943:Association",
  "pmid": "10788334",
  "document_id": "pmid:10788334",
  "type": "Association",
  "subject": {
    "entity_id": "entity-subject-id",
    "text": "BRCA1",
    "type": "GeneOrGeneProduct",
    "normalized_id": "672"
  },
  "object": {
    "entity_id": "entity-object-id",
    "text": "breast cancer",
    "type": "DiseaseOrPhenotypicFeature",
    "normalized_id": "D001943"
  },
  "extraction": {
    "source": "biored_model_v1",
    "confidence": 0.91,
    "novelty": "Novel"
  }
}
```

Required fields:

- `relation_id`
- `pmid`
- `type`
- `subject.normalized_id`
- `object.normalized_id`
- `extraction.source`

Recommended fields:

- `extraction.confidence`
- `extraction.novelty`

Notes:

- Future versions may add directionality roles explicitly beyond
  subject/object naming.
- A relation should be queryable independently of which evidence sentence was
  selected first.

Current repository mapping:

- SQLite table: `entity_relations`
- current task contracts:
  - `BIORED_RELATIONS_COLUMNS_V1`

## 4. Evidence

Represents a textual evidence unit that supports a relation or an entity-level
claim. In the current repository this is sentence-oriented.

```json
{
  "evidence_id": "ev:10788334:3",
  "pmid": "10788334",
  "document_id": "pmid:10788334",
  "sentence_index": 3,
  "text": "BRCA1 is associated with breast cancer.",
  "supports": {
    "relation_id": "rel:10788334:672:D001943:Association"
  },
  "score": {
    "relation_confidence": 0.91,
    "evidence_rank_score": 0.78,
    "normalization_support_score": 0.95
  },
  "source": "pubmed_abstract"
}
```

Required fields:

- `evidence_id`
- `pmid`
- `text`
- `source`

Recommended fields:

- `sentence_index`
- `supports.relation_id`
- `score`

Notes:

- `Evidence` is where downstream ranking should happen.
- V1 allows only one sentence per evidence object, but the design should not
  rule out paragraph or document-level evidence later.

Current repository mapping:

- SQLite table: `evidence_sentences`
- current L6 bundle relation rows flatten one evidence sentence into each
  relation record

## 5. Provenance

Represents how an evidence object or relation is grounded back to source text
and extraction logic.

```json
{
  "provenance_id": "prov:rel:10788334:672:D001943:Association:ev:10788334:3",
  "pmid": "10788334",
  "relation_id": "rel:10788334:672:D001943:Association",
  "evidence_id": "ev:10788334:3",
  "source_document": "pubmed_abstract",
  "source_pmid": "10788334",
  "sentence_index": 3,
  "sentence_span": {
    "char_start": null,
    "char_end": null
  },
  "linked_entities": [
    "entity-subject-id",
    "entity-object-id"
  ],
  "method": "surface_match_v1",
  "source_system": "biored_model_v1"
}
```

Required fields:

- `provenance_id`
- `pmid`
- `source_document`
- `method`

Recommended fields:

- `relation_id`
- `evidence_id`
- `sentence_index`
- `linked_entities`

Notes:

- The current repository stores provenance only partially. This schema defines
  the stronger target object.
- `method` is important because current linkage is heuristic, not exact.

Current repository mapping:

- SQLite table: `relation_provenance`
- link table: `evidence_sentence_mentions`

## Current Repository Status Against This Schema

| Object | Status | Notes |
| --- | --- | --- |
| `Document` | implemented | `papers` already matches this well |
| `Entity` | implemented v1 | missing reliable char offsets |
| `Relation` | implemented v1 for BioRED | still BioRED-centric |
| `Evidence` | partial | sentences exist, but not yet modeled as a first-class relation support object |
| `Provenance` | weak partial | sentence text and relation confidence exist, but linkage quality is limited |

## V1 Minimal Required Fields for Downstream Integration

For initial integration into `bioAI-target` or another KB system, the minimum
portable payload should contain:

```json
{
  "document": {...},
  "entities": [{...}],
  "relations": [{...}],
  "evidence": [{...}],
  "provenance": [{...}]
}
```

The minimum practical required fields are:

- document: `pmid`, `title`, `abstract`
- entity: `entity_id`, `pmid`, `text`, `type`, `normalized.id`
- relation: `relation_id`, `pmid`, `type`, `subject.normalized_id`, `object.normalized_id`, `extraction.source`
- evidence: `evidence_id`, `pmid`, `text`, `source`
- provenance: `provenance_id`, `pmid`, `method`, and either `relation_id` or `evidence_id`

## Scoring Model Boundary

This schema separates raw extraction confidence from downstream evidence
quality. V1 should keep at least these score slots:

- `normalized.score`
- `relation.extraction.confidence`
- `evidence.score.evidence_rank_score`

Important distinction:

- relation confidence answers "how likely is this label correct?"
- evidence rank score answers "how useful is this evidence for retrieval or QA?"

The current repository has the first two only partially. It does not yet have a
stable evidence ranking score.

## Recommended Serialization Shape

For repository-internal adapters and downstream exports, prefer a top-level
bundle shape like:

```json
{
  "schema_version": "evidence-v1",
  "task": "biored",
  "documents": [],
  "entities": [],
  "relations": [],
  "evidence": [],
  "provenance": []
}
```

This should become the stable interchange format between:

- extraction/persistence
- retrieval
- `bioAI-target`
- future KB export jobs

## Migration Guidance

The repository should not rewrite all tables first. Safer order:

1. keep current SQLite tables
2. add adapter code that emits this schema from current query results
3. upgrade retrieval and L6/L7 code to consume the unified object model
4. improve provenance and scoring fields without breaking the bundle contract

## Non-Goals for V1

Do not block V1 on:

- perfect character offsets
- document-level multi-hop reasoning
- ontology-complete biomarker taxonomy
- graph database migration

The V1 objective is a stable, reusable evidence-layer contract, not a final
biomedical knowledge platform.
