from __future__ import annotations

from src.output.l7_answer import build_l7_answer


def test_build_l7_answer_with_relation_evidence():
    agent_result = {
        "status": "evidence_found",
        "task": "biored",
    }
    l6_result = {
        "provider": "none",
        "summary": "",
        "bundle": {
            "records": [
                {
                    "evidence_type": "relation",
                    "pmid": "10788334",
                    "relation_type": "Association",
                    "entity1_text": "BRCA1",
                    "entity2_text": "breast cancer",
                }
            ],
            "pmids": ["10788334"],
        },
    }
    out = build_l7_answer(
        question="Q",
        agent_result=agent_result,
        l6_result=l6_result,
    )
    assert out["answer"] == "evidence bundle returned"
    assert out["claims"][0]["text"] == "BRCA1 -[Association]-> breast cancer"
    assert out["citations"] == ["10788334"]


def test_build_l7_answer_without_evidence():
    out = build_l7_answer(
        question="Q",
        agent_result={"status": "insufficient_evidence", "task": "biored"},
        l6_result={"provider": "none", "summary": "", "bundle": {"records": [], "pmids": []}},
    )
    assert out["answer"] == "insufficient evidence"
    assert out["claims"] == []
    assert out["citations"] == []


def test_build_l7_answer_refresh_failed():
    out = build_l7_answer(
        question="Q",
        agent_result={
            "status": "refresh_failed",
            "task": "biored",
            "message": "pipeline failed",
        },
        l6_result={
            "provider": "none",
            "summary": "",
            "bundle": {
                "records": [],
                "pmids": [],
                "status": "refresh_failed",
            },
        },
    )
    assert out["status"] == "refresh_failed"
    assert out["answer"] == "insufficient evidence"
    assert out["claims"] == []
    assert out["citations"] == []
    assert "claim-level citation validation is pending" in out["limitations"][0]
