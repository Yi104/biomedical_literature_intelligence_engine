from __future__ import annotations

import pandas as pd

from src.kb.query import (
    find_mentions_by_type_and_keyword,
    get_evidence_sentences_by_normalized_id,
    get_evidence_sentences_by_pmid,
    get_mentions_by_pmid,
    get_pmids_by_normalized_id,
)
from src.kb.schema import init_sqlite_schema
from src.kb.writer import write_pipeline_outputs_to_sqlite


def test_kb_writer_and_query_roundtrip(tmp_path):
    db_path = str(tmp_path / "biomed_kb_test.db")
    init_sqlite_schema(db_path)

    papers_df = pd.DataFrame(
        [
            {
                "pmid": "P1",
                "title": "Paper 1",
                "year": "2024",
                "journal": "J1",
                "abstract": "BRCA1 and breast cancer",
            }
        ]
    )
    entities_df = pd.DataFrame(
        [
            {
                "pmid": "P1",
                "entity_type": "Gene",
                "entity_text": "BRCA1",
                "token_start": 0,
                "token_end": 0,
                "normalized_id": "HGNC:1100",
                "normalized_text": "BRCA1",
                "normalized_source": "rule_alias_v1",
                "normalized_score": 1.0,
            }
        ]
    )

    added = write_pipeline_outputs_to_sqlite(
        papers_df, entities_df, db_path=db_path, task="bc5cdr"
    )
    assert added == (1, 1, 1, 1)

    # Idempotency: second write should not duplicate rows.
    added_again = write_pipeline_outputs_to_sqlite(
        papers_df, entities_df, db_path=db_path, task="bc5cdr"
    )
    assert added_again == (0, 0, 0, 0)

    mentions = get_mentions_by_pmid("P1", db_path=db_path)
    assert len(mentions) == 1
    assert mentions[0]["normalized_id"] == "HGNC:1100"

    pmids = get_pmids_by_normalized_id("HGNC:1100", db_path=db_path)
    assert pmids == ["P1"]

    matches = find_mentions_by_type_and_keyword("Gene", "brca", db_path=db_path)
    assert len(matches) == 1
    assert matches[0]["pmid"] == "P1"

    sentences = get_evidence_sentences_by_pmid("P1", task="bc5cdr", db_path=db_path)
    assert len(sentences) == 1
    assert sentences[0]["sentence_text"] == "BRCA1 and breast cancer"
    assert sentences[0]["entities"][0]["normalized_id"] == "HGNC:1100"

    by_norm_sentences = get_evidence_sentences_by_normalized_id(
        "HGNC:1100", task="bc5cdr", db_path=db_path
    )
    assert [row["sentence_text"] for row in by_norm_sentences] == [
        "BRCA1 and breast cancer"
    ]


def test_sentence_evidence_links_mentions_only_to_containing_sentences(tmp_path):
    db_path = str(tmp_path / "sentence_link_test.db")
    papers_df = pd.DataFrame(
        [
            {
                "pmid": "P2",
                "title": "Two-sentence paper",
                "year": "2025",
                "journal": "J2",
                "abstract": (
                    "BRCA1 was detected in the cohort. "
                    "Breast cancer outcomes were reviewed."
                ),
            }
        ]
    )
    entities_df = pd.DataFrame(
        [
            {
                "pmid": "P2",
                "entity_type": "Gene",
                "entity_text": "BRCA1",
                "token_start": 0,
                "token_end": 0,
                "normalized_id": "HGNC:1100",
                "normalized_text": "BRCA1",
                "normalized_source": "rule_alias_v1",
                "normalized_score": 1.0,
            },
            {
                "pmid": "P2",
                "entity_type": "Disease",
                "entity_text": "Breast cancer",
                "token_start": 6,
                "token_end": 7,
                "normalized_id": "MESH:D001943",
                "normalized_text": "Breast Neoplasms",
                "normalized_source": "rule_alias_v1",
                "normalized_score": 1.0,
            },
        ]
    )

    added = write_pipeline_outputs_to_sqlite(
        papers_df, entities_df, db_path=db_path, task="bc5cdr"
    )
    assert added == (1, 2, 2, 2)

    sentences = get_evidence_sentences_by_pmid("P2", task="bc5cdr", db_path=db_path)
    assert [row["sentence_text"] for row in sentences] == [
        "BRCA1 was detected in the cohort.",
        "Breast cancer outcomes were reviewed.",
    ]
    assert [row["entities"][0]["normalized_id"] for row in sentences] == [
        "HGNC:1100",
        "MESH:D001943",
    ]
