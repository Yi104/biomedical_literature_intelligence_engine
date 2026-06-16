from __future__ import annotations

from src.contracts.evidence_adapters import (
    build_unified_evidence_bundle_from_agent_result,
    mention_row_to_entity_record,
    relation_row_to_relation_record,
)


def test_mention_row_to_entity_record_builds_normalized_payload():
    row = {
        "pmid": "P1",
        "entity_type": "Gene",
        "entity_text": "BRCA1",
        "token_start": 1,
        "token_end": 2,
        "normalized_id": "HGNC:1100",
        "normalized_text": "BRCA1",
        "normalized_source": "rule_based_v1",
        "normalized_score": 0.95,
    }
    record = mention_row_to_entity_record(row)
    assert record["entity_id"] == "entity:P1:Gene:1:2:BRCA1"
    assert record["normalized"]["id"] == "HGNC:1100"
    assert record["normalized"]["score"] == 0.95


def test_relation_row_to_relation_record_uses_first_provenance_confidence():
    row = {
        "pmid": "P2",
        "relation_type": "Association",
        "entity1_text": "BRCA1",
        "entity1_type": "GeneOrGeneProduct",
        "entity1_normalized_id": "672",
        "entity2_text": "breast cancer",
        "entity2_type": "DiseaseOrPhenotypicFeature",
        "entity2_normalized_id": "D001943",
        "relation_source": "biored_model_v1",
        "provenance": [
            {
                "evidence_sentence": "BRCA1 is associated with breast cancer.",
                "novelty": "Novel",
                "provenance_source": "biored_model_v1",
                "confidence": 0.91,
            }
        ],
    }
    record = relation_row_to_relation_record(row)
    assert record["relation_id"] == "rel:P2:672:D001943:Association"
    assert record["subject"]["normalized_id"] == "672"
    assert record["extraction"]["confidence"] == 0.91
    assert record["extraction"]["novelty"] == "Novel"


def test_build_unified_evidence_bundle_for_relation_mode_keeps_legacy_records():
    bundle = build_unified_evidence_bundle_from_agent_result(
        "Q",
        {
            "status": "evidence_found",
            "task": "biored",
            "retrieval_mode": "relation_entity_pair",
            "filters": {"entity1_normalized_id": "672", "entity2_normalized_id": "D001943"},
            "count": 1,
            "evidence": [
                {
                    "pmid": "10788334",
                    "relation_type": "Association",
                    "entity1_text": "BRCA1",
                    "entity1_type": "GeneOrGeneProduct",
                    "entity1_normalized_id": "672",
                    "entity2_text": "breast cancer",
                    "entity2_type": "DiseaseOrPhenotypicFeature",
                    "entity2_normalized_id": "D001943",
                    "relation_source": "biored_relation_v1",
                    "provenance": [
                        {
                            "evidence_sentence": "BRCA1 is associated with breast cancer.",
                            "novelty": "No",
                            "provenance_source": "biored_relation_v1",
                            "confidence": 1.0,
                        }
                    ],
                }
            ],
        },
    )
    assert bundle["schema_version"] == "evidence-v1"
    assert bundle["relations"][0]["type"] == "Association"
    assert bundle["evidence"][0]["supports"]["relation_id"] == bundle["relations"][0]["relation_id"]
    assert bundle["provenance"][0]["relation_id"] == bundle["relations"][0]["relation_id"]
    assert bundle["records"][0]["evidence_type"] == "relation"
