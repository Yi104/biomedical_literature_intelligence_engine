from __future__ import annotations

import pandas as pd

from src.agent.controller import run_agent_controller
from src.kb.writer import (
    write_pipeline_outputs_to_sqlite,
    write_pipeline_outputs_with_relations_to_sqlite,
)


def _one_paper_and_entity(pmid: str = "P100"):
    papers_df = pd.DataFrame(
        [
            {
                "pmid": pmid,
                "title": "Evidence paper",
                "year": "2024",
                "journal": "Journal",
                "abstract": "Cisplatin is associated with kidney diseases.",
            }
        ]
    )
    entities_df = pd.DataFrame(
        [
            {
                "pmid": pmid,
                "entity_type": "Chemical",
                "entity_text": "Cisplatin",
                "token_start": 0,
                "token_end": 0,
                "normalized_id": "CHEBI:27899",
                "normalized_text": "cisplatin",
                "normalized_source": "rule_alias_v1",
                "normalized_score": 1.0,
            }
        ]
    )
    return papers_df, entities_df


def test_read_only_request_returns_existing_evidence_without_refresh(tmp_path):
    db_path = str(tmp_path / "agent_read_only.db")
    papers_df, entities_df = _one_paper_and_entity()
    write_pipeline_outputs_to_sqlite(papers_df, entities_df, db_path=db_path)

    def should_not_refresh(*args, **kwargs):
        raise AssertionError("read-only request must not run refresh")

    result = run_agent_controller(
        task="bc5cdr",
        retrieval_mode="normalized_id",
        normalized_id="CHEBI:27899",
        allow_refresh=False,
        db_path=db_path,
        refresh_runner=should_not_refresh,
    )

    assert result["status"] == "evidence_found"
    assert result["refreshed"] is False
    assert result["count"] == 1
    assert result["evidence"] == [{"pmid": "P100"}]
    assert result["refresh"] is None


def test_read_only_request_reports_insufficient_evidence(tmp_path):
    result = run_agent_controller(
        task="bc5cdr",
        retrieval_mode="normalized_id",
        normalized_id="CHEBI:missing",
        allow_refresh=False,
        db_path=str(tmp_path / "agent_empty.db"),
    )

    assert result["status"] == "insufficient_evidence"
    assert result["count"] == 0
    assert result["evidence"] == []


def test_explicit_refresh_writes_outputs_and_returns_follow_up_evidence(tmp_path):
    db_path = str(tmp_path / "agent_refresh.db")

    def fake_refresh(task, **kwargs):
        assert task == "bc5cdr"
        assert kwargs["search_query"] == "cisplatin kidney diseases"
        assert kwargs["smoke"] is False
        return _one_paper_and_entity(pmid="P200")

    result = run_agent_controller(
        task="bc5cdr",
        retrieval_mode="pmid",
        pmid="P200",
        search_query="cisplatin kidney diseases",
        allow_refresh=True,
        db_path=db_path,
        refresh_runner=fake_refresh,
    )

    assert result["status"] == "refreshed_and_found"
    assert result["refreshed"] is True
    assert result["count"] == 1
    assert result["evidence"][0]["normalized_id"] == "CHEBI:27899"
    assert result["refresh"] == {
        "search_query": "cisplatin kidney diseases",
        "papers_added": 1,
        "mentions_added": 1,
        "normalized_entities_added": 1,
        "evidence_sentences_added": 1,
    }


def test_refresh_failure_returns_no_fabricated_evidence(tmp_path):
    def failing_refresh(*args, **kwargs):
        raise RuntimeError("pipeline failed")

    result = run_agent_controller(
        task="bc5cdr",
        retrieval_mode="pmid",
        pmid="P300",
        search_query="new query",
        allow_refresh=True,
        db_path=str(tmp_path / "agent_failed.db"),
        refresh_runner=failing_refresh,
    )

    assert result["status"] == "refresh_failed"
    assert result["refreshed"] is False
    assert result["count"] == 0
    assert result["evidence"] == []
    assert result["message"] == "pipeline failed"


def test_bc5cdr_smoke_refresh_runs_through_l5_controller(tmp_path):
    result = run_agent_controller(
        task="bc5cdr",
        retrieval_mode="evidence_pmid",
        pmid="SMOKE001",
        search_query="cisplatin kidney diseases",
        allow_refresh=True,
        smoke=True,
        db_path=str(tmp_path / "agent_smoke.db"),
    )

    assert result["status"] == "refreshed_and_found"
    assert result["count"] == 1
    assert result["evidence"][0]["sentence_text"] == (
        "Cisplatin is associated with kidney diseases."
    )
    assert {item["entity_type"] for item in result["evidence"][0]["entities"]} == {
        "Chemical",
        "Disease",
    }
    assert result["refresh"]["evidence_sentences_added"] == 1


def test_biored_relation_read_only_mode(tmp_path):
    db_path = str(tmp_path / "agent_biored_read.db")
    papers_df = pd.DataFrame(
        [
            {
                "pmid": "B100",
                "title": "BioRED paper",
                "year": "2025",
                "journal": "J",
                "abstract": "BRCA1 is associated with breast cancer.",
            }
        ]
    )
    entities_df = pd.DataFrame(
        [
            {
                "pmid": "B100",
                "entity_type": "GeneOrGeneProduct",
                "entity_text": "BRCA1",
                "token_start": 0,
                "token_end": 5,
                "normalized_id": "672",
                "normalized_text": "BRCA1",
                "normalized_source": "biored_annotation_v1",
                "normalized_score": 1.0,
            },
            {
                "pmid": "B100",
                "entity_type": "DiseaseOrPhenotypicFeature",
                "entity_text": "breast cancer",
                "token_start": 23,
                "token_end": 36,
                "normalized_id": "D001943",
                "normalized_text": "breast cancer",
                "normalized_source": "biored_annotation_v1",
                "normalized_score": 1.0,
            },
        ]
    )
    relations_df = pd.DataFrame(
        [
            {
                "pmid": "B100",
                "relation_type": "Association",
                "entity1_text": "BRCA1",
                "entity1_type": "GeneOrGeneProduct",
                "entity1_normalized_id": "672",
                "entity2_text": "breast cancer",
                "entity2_type": "DiseaseOrPhenotypicFeature",
                "entity2_normalized_id": "D001943",
                "evidence_sentence": "BRCA1 is associated with breast cancer.",
                "relation_source": "biored_pubtator",
                "novelty": "Novel",
            }
        ]
    )
    write_pipeline_outputs_with_relations_to_sqlite(
        papers_df, entities_df, relations_df, db_path=db_path, task="biored"
    )

    result = run_agent_controller(
        task="biored",
        retrieval_mode="relation_entity_pair",
        entity1_normalized_id="672",
        entity2_normalized_id="D001943",
        allow_refresh=False,
        db_path=db_path,
    )
    assert result["status"] == "evidence_found"
    assert result["count"] == 1
    assert result["evidence"][0]["relation_type"] == "Association"


def test_biored_refresh_writes_relation_outputs(tmp_path):
    db_path = str(tmp_path / "agent_biored_refresh.db")

    def fake_biored_refresh(task, **kwargs):
        assert task == "biored"
        papers_df = pd.DataFrame(
            [
                {
                    "pmid": "B200",
                    "title": "BioRED refreshed",
                    "year": "2025",
                    "journal": "J",
                    "abstract": "BRCA1 is associated with breast cancer.",
                }
            ]
        )
        entities_df = pd.DataFrame(
            [
                {
                    "pmid": "B200",
                    "entity_type": "GeneOrGeneProduct",
                    "entity_text": "BRCA1",
                    "token_start": 0,
                    "token_end": 5,
                    "normalized_id": "672",
                    "normalized_text": "BRCA1",
                    "normalized_source": "biored_annotation_v1",
                    "normalized_score": 1.0,
                },
                {
                    "pmid": "B200",
                    "entity_type": "DiseaseOrPhenotypicFeature",
                    "entity_text": "breast cancer",
                    "token_start": 23,
                    "token_end": 36,
                    "normalized_id": "D001943",
                    "normalized_text": "breast cancer",
                    "normalized_source": "biored_annotation_v1",
                    "normalized_score": 1.0,
                },
            ]
        )
        relations_df = pd.DataFrame(
            [
                {
                    "pmid": "B200",
                    "relation_type": "Association",
                    "entity1_text": "BRCA1",
                    "entity1_type": "GeneOrGeneProduct",
                    "entity1_normalized_id": "672",
                    "entity2_text": "breast cancer",
                    "entity2_type": "DiseaseOrPhenotypicFeature",
                    "entity2_normalized_id": "D001943",
                    "evidence_sentence": "BRCA1 is associated with breast cancer.",
                    "relation_source": "biored_pubtator",
                    "novelty": "Novel",
                }
            ]
        )
        return papers_df, entities_df, relations_df

    result = run_agent_controller(
        task="biored",
        retrieval_mode="relation_pmid",
        pmid="B200",
        search_query="BRCA1 breast cancer",
        allow_refresh=True,
        db_path=db_path,
        refresh_runner=fake_biored_refresh,
    )
    assert result["status"] == "refreshed_and_found"
    assert result["count"] == 1
    assert result["refresh"]["relations_added"] == 1
