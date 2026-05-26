from __future__ import annotations

COMMON_PAPERS_COLUMNS_V1: list[str] = [
    "pmid",
    "title",
    "year",
    "journal",
    "abstract",
    "entity_count",
    "entity_types",
]

COMMON_ENTITIES_COLUMNS_V1: list[str] = [
    "pmid",
    "entity_type",
    "entity_text",
    "token_start",
    "token_end",
]

# v2 extends v1 with normalization-layer outputs.
COMMON_ENTITIES_COLUMNS_V2: list[str] = [
    *COMMON_ENTITIES_COLUMNS_V1,
    "normalized_text",
    "normalized_id",
    "normalized_source",
    "normalized_score",
]

# BioRED is the primary planned evidence task because it represents both
# entities and document-level biomedical relations, including gene-disease.
BIORED_RELATIONS_COLUMNS_V1: list[str] = [
    "pmid",
    "relation_type",
    "entity1_text",
    "entity1_type",
    "entity1_normalized_id",
    "entity2_text",
    "entity2_type",
    "entity2_normalized_id",
    "evidence_sentence",
    "relation_source",
]
