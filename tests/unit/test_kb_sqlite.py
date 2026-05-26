from __future__ import annotations

import pandas as pd

from src.kb.query import (
    find_mentions_by_type_and_keyword,
    get_evidence_sentences_by_normalized_id,
    get_evidence_sentences_by_pmid,
    get_mentions_by_pmid,
    get_pmids_by_normalized_id,
    get_relations_by_entity_pair,
    get_relations_by_pmid,
)
from src.kb.schema import init_sqlite_schema
from src.kb.writer import (
    write_pipeline_outputs_to_sqlite,
    write_pipeline_outputs_with_relations_to_sqlite,
)


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
                "abstract": "Cisplatin and kidney diseases",
            }
        ]
    )
    entities_df = pd.DataFrame(
        [
            {
                "pmid": "P1",
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
    assert mentions[0]["normalized_id"] == "CHEBI:27899"

    pmids = get_pmids_by_normalized_id("CHEBI:27899", db_path=db_path)
    assert pmids == ["P1"]

    matches = find_mentions_by_type_and_keyword("Chemical", "cisplatin", db_path=db_path)
    assert len(matches) == 1
    assert matches[0]["pmid"] == "P1"

    sentences = get_evidence_sentences_by_pmid("P1", task="bc5cdr", db_path=db_path)
    assert len(sentences) == 1
    assert sentences[0]["sentence_text"] == "Cisplatin and kidney diseases"
    assert sentences[0]["entities"][0]["normalized_id"] == "CHEBI:27899"

    by_norm_sentences = get_evidence_sentences_by_normalized_id(
        "CHEBI:27899", task="bc5cdr", db_path=db_path
    )
    assert [row["sentence_text"] for row in by_norm_sentences] == [
        "Cisplatin and kidney diseases"
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
                    "Cisplatin was given in the cohort. "
                    "Kidney diseases were reviewed."
                ),
            }
        ]
    )
    entities_df = pd.DataFrame(
        [
            {
                "pmid": "P2",
                "entity_type": "Chemical",
                "entity_text": "Cisplatin",
                "token_start": 0,
                "token_end": 0,
                "normalized_id": "CHEBI:27899",
                "normalized_text": "cisplatin",
                "normalized_source": "rule_alias_v1",
                "normalized_score": 1.0,
            },
            {
                "pmid": "P2",
                "entity_type": "Disease",
                "entity_text": "Kidney diseases",
                "token_start": 6,
                "token_end": 7,
                "normalized_id": "MESH:D007674",
                "normalized_text": "Kidney Diseases",
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
        "Cisplatin was given in the cohort.",
        "Kidney diseases were reviewed.",
    ]
    assert [row["entities"][0]["normalized_id"] for row in sentences] == [
        "CHEBI:27899",
        "MESH:D007674",
    ]


def test_relation_writer_and_queries_roundtrip(tmp_path):
    db_path = str(tmp_path / "relation_roundtrip.db")
    papers_df = pd.DataFrame(
        [
            {
                "pmid": "P3",
                "title": "Relation paper",
                "year": "2025",
                "journal": "J3",
                "abstract": "BRCA1 is associated with breast cancer.",
            }
        ]
    )
    entities_df = pd.DataFrame(
        [
            {
                "pmid": "P3",
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
                "pmid": "P3",
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
                "pmid": "P3",
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

    summary = write_pipeline_outputs_with_relations_to_sqlite(
        papers_df,
        entities_df,
        relations_df,
        db_path=db_path,
        task="biored",
    )
    assert summary["papers_added"] == 1
    assert summary["relations_added"] == 1
    assert summary["relation_provenance_added"] == 1

    rows_by_pmid = get_relations_by_pmid("P3", task="biored", db_path=db_path)
    assert len(rows_by_pmid) == 1
    assert rows_by_pmid[0]["entity1_normalized_id"] == "672"
    assert rows_by_pmid[0]["provenance"][0]["novelty"] == "Novel"

    rows_by_pair = get_relations_by_entity_pair(
        "672", "D001943", task="biored", db_path=db_path
    )
    assert len(rows_by_pair) == 1
    assert rows_by_pair[0]["relation_type"] == "Association"
