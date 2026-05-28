from __future__ import annotations

from src.llm.evidence_bundle import build_evidence_bundle_from_agent_result
from src.llm.router import LLMOptions, summarize_agent_result_with_provider


def test_build_evidence_bundle_for_relation_mode():
    agent_result = {
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
    }
    bundle = build_evidence_bundle_from_agent_result(
        "Is BRCA1 associated with breast cancer?",
        agent_result,
    )
    assert bundle["task"] == "biored"
    assert bundle["retrieval_mode"] == "relation_entity_pair"
    assert bundle["count"] == 1
    assert bundle["pmids"] == ["10788334"]
    assert bundle["records"][0]["evidence_type"] == "relation"
    assert bundle["records"][0]["novelty"] == "No"


def test_build_evidence_bundle_for_empty_result():
    bundle = build_evidence_bundle_from_agent_result(
        "question",
        {
            "status": "insufficient_evidence",
            "task": "biored",
            "retrieval_mode": "relation_pmid",
            "filters": {"pmid": "1"},
            "count": 0,
            "evidence": [],
        },
    )
    assert bundle["insufficient_evidence"] is True
    assert bundle["count"] == 0
    assert bundle["records"] == []
    assert bundle["pmids"] == []


def test_summarize_agent_result_attaches_bundle():
    result = summarize_agent_result_with_provider(
        "question",
        {
            "status": "evidence_found",
            "task": "bc5cdr",
            "retrieval_mode": "pmid",
            "filters": {"pmid": "P1"},
            "count": 1,
            "evidence": [
                {
                    "pmid": "P1",
                    "entity_type": "Chemical",
                    "entity_text": "Cisplatin",
                    "normalized_id": "CHEBI:27899",
                    "normalized_text": "cisplatin",
                }
            ],
        },
        LLMOptions(provider="none"),
    )
    assert result["provider"] == "none"
    assert result["mode"] == "evidence_only"
    assert result["bundle"]["count"] == 1
    assert result["bundle"]["records"][0]["evidence_type"] == "mention"
