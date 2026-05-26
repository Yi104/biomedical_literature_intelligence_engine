from __future__ import annotations

import pandas as pd

from src.kb.schema import init_sqlite_schema
from src.kb.writer import (
    write_pipeline_outputs_to_sqlite,
    write_pipeline_outputs_with_relations_to_sqlite,
)
from src.retrieval.sqlite_service import query_kb


def test_query_kb_contract_for_three_modes(tmp_path):
    db_path = str(tmp_path / "biomed_kb_service_test.db")
    init_sqlite_schema(db_path)

    papers_df = pd.DataFrame(
        [
            {
                "pmid": "P100",
                "title": "Paper",
                "year": "2024",
                "journal": "J1",
                "abstract": "Cisplatin in kidney diseases",
            }
        ]
    )
    entities_df = pd.DataFrame(
        [
            {
                "pmid": "P100",
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
    write_pipeline_outputs_to_sqlite(
        papers_df, entities_df, db_path=db_path, task="bc5cdr"
    )

    by_pmid = query_kb(mode="pmid", pmid="P100", db_path=db_path)
    assert by_pmid["mode"] == "pmid"
    assert by_pmid["filters"] == {"pmid": "P100"}
    assert by_pmid["count"] == 1
    assert by_pmid["results"][0]["normalized_id"] == "CHEBI:27899"

    by_norm = query_kb(mode="normalized_id", normalized_id="CHEBI:27899", db_path=db_path)
    assert by_norm["mode"] == "normalized_id"
    assert by_norm["filters"] == {"normalized_id": "CHEBI:27899"}
    assert by_norm["count"] == 1
    assert by_norm["results"] == [{"pmid": "P100"}]

    by_type_kw = query_kb(
        mode="type_keyword",
        entity_type="Chemical",
        keyword="cisplatin",
        db_path=db_path,
    )
    assert by_type_kw["mode"] == "type_keyword"
    assert by_type_kw["filters"] == {"entity_type": "Chemical", "keyword": "cisplatin"}
    assert by_type_kw["count"] == 1
    assert by_type_kw["results"][0]["pmid"] == "P100"

    by_evidence_pmid = query_kb(
        mode="evidence_pmid", pmid="P100", task="bc5cdr", db_path=db_path
    )
    assert by_evidence_pmid["filters"] == {"pmid": "P100", "task": "bc5cdr"}
    assert by_evidence_pmid["count"] == 1
    assert by_evidence_pmid["results"][0]["sentence_text"] == "Cisplatin in kidney diseases"

    by_evidence_norm = query_kb(
        mode="evidence_normalized_id",
        normalized_id="CHEBI:27899",
        task="bc5cdr",
        db_path=db_path,
    )
    assert by_evidence_norm["count"] == 1
    assert by_evidence_norm["results"][0]["entities"][0]["normalized_id"] == "CHEBI:27899"


def test_query_kb_relation_modes(tmp_path):
    db_path = str(tmp_path / "biomed_kb_relation_service_test.db")
    init_sqlite_schema(db_path)

    papers_df = pd.DataFrame(
        [
            {
                "pmid": "P300",
                "title": "Relation Paper",
                "year": "2025",
                "journal": "JR",
                "abstract": "BRCA1 is associated with breast cancer.",
            }
        ]
    )
    entities_df = pd.DataFrame(
        [
            {
                "pmid": "P300",
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
                "pmid": "P300",
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
                "pmid": "P300",
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
        papers_df,
        entities_df,
        relations_df,
        db_path=db_path,
        task="biored",
    )

    by_pmid = query_kb(mode="relation_pmid", pmid="P300", task="biored", db_path=db_path)
    assert by_pmid["count"] == 1
    assert by_pmid["results"][0]["relation_type"] == "Association"

    by_pair = query_kb(
        mode="relation_entity_pair",
        entity1_normalized_id="672",
        entity2_normalized_id="D001943",
        task="biored",
        db_path=db_path,
    )
    assert by_pair["count"] == 1
    assert by_pair["results"][0]["provenance"][0]["novelty"] == "Novel"
