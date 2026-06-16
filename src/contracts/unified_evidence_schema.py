from __future__ import annotations

from typing import Any, NotRequired, TypedDict

SCHEMA_VERSION = "evidence-v1"


class DocumentRecord(TypedDict):
    document_id: str
    pmid: str
    source: str
    title: NotRequired[str]
    year: NotRequired[str]
    journal: NotRequired[str]
    abstract: NotRequired[str]


class MentionSpanRecord(TypedDict):
    token_start: int | None
    token_end: int | None
    char_start: int | None
    char_end: int | None


class NormalizedEntityRecord(TypedDict):
    id: str
    label: str
    source_vocab: str
    method: str
    score: float


class EntityRecord(TypedDict):
    entity_id: str
    pmid: str
    document_id: str
    text: str
    type: str
    mention_span: MentionSpanRecord
    normalized: NotRequired[NormalizedEntityRecord]


class RelationEndpointRecord(TypedDict):
    entity_id: str
    text: str
    type: str
    normalized_id: str


class RelationExtractionRecord(TypedDict):
    source: str
    confidence: float
    novelty: str


class RelationRecord(TypedDict):
    relation_id: str
    pmid: str
    document_id: str
    type: str
    subject: RelationEndpointRecord
    object: RelationEndpointRecord
    extraction: RelationExtractionRecord


class EvidenceSupportRecord(TypedDict):
    relation_id: str


class EvidenceScoreRecord(TypedDict):
    relation_confidence: NotRequired[float]
    evidence_rank_score: NotRequired[float]
    normalization_support_score: NotRequired[float]


class EvidenceRecord(TypedDict):
    evidence_id: str
    pmid: str
    document_id: str
    text: str
    source: str
    sentence_index: NotRequired[int | None]
    supports: NotRequired[EvidenceSupportRecord]
    score: NotRequired[EvidenceScoreRecord]


class SentenceSpanRecord(TypedDict):
    char_start: int | None
    char_end: int | None


class ProvenanceRecord(TypedDict):
    provenance_id: str
    pmid: str
    source_document: str
    source_pmid: str
    method: str
    source_system: str
    relation_id: NotRequired[str]
    evidence_id: NotRequired[str]
    sentence_index: NotRequired[int | None]
    sentence_span: NotRequired[SentenceSpanRecord]
    linked_entities: NotRequired[list[str]]
    evidence_sentence: NotRequired[str]
    confidence: NotRequired[float]
    novelty: NotRequired[str]


class EvidenceBundleV1(TypedDict):
    schema_version: str
    question: str
    task: str
    retrieval_mode: str
    status: str
    insufficient_evidence: bool
    count: int
    pmids: list[str]
    filters: dict[str, Any]
    documents: list[DocumentRecord]
    entities: list[EntityRecord]
    relations: list[RelationRecord]
    evidence: list[EvidenceRecord]
    provenance: list[ProvenanceRecord]
    records: list[dict[str, Any]]
