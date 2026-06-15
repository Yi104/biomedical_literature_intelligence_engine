from __future__ import annotations

import pytest
import pandas as pd

from src.contracts.registry import get_schema
from src.extraction import biored_pipeline
from src.extraction.biored_pipeline import run_biored_pipeline


def test_biored_smoke_contract_includes_gene_disease_relation():
    papers_df, entities_df, relations_df = run_biored_pipeline(
        query="BRCA1 breast cancer",
        smoke=True,
    )
    schema = get_schema("biored:v1")

    assert list(papers_df.columns) == schema["papers_columns"]
    assert list(entities_df.columns) == schema["entities_columns"]
    assert list(relations_df.columns) == schema["relations_columns"]
    assert relations_df.iloc[0]["relation_type"] == "Disease-Gene"
    assert relations_df.iloc[0]["entity1_normalized_id"] == "HGNC:1100"
    assert relations_df.iloc[0]["entity2_normalized_id"] == "MESH:D001943"
    assert relations_df.iloc[0]["confidence"] == 1.0


def test_biored_live_path_is_not_claimed_as_implemented():
    with pytest.raises(FileNotFoundError, match="requires --data_path"):
        run_biored_pipeline(query="BRCA1 breast cancer", smoke=False)


def test_biored_model_relation_mode_uses_classifier_output(tmp_path, monkeypatch):
    pubtator_path = tmp_path / "sample.PubTator"
    pubtator_path.write_text(
        "\n".join(
            [
                "12345|t|BRCA1 and breast cancer",
                "12345|a|BRCA1 is associated with breast cancer.",
                "12345\t0\t5\tBRCA1\tGeneOrGeneProduct\t672",
                "12345\t30\t43\tbreast cancer\tDiseaseOrPhenotypicFeature\tD001943",
                "12345\tAssociation\t672\tD001943\tNovel",
                "",
            ]
        ),
        encoding="utf-8",
    )

    def fake_predict(**kwargs):
        assert kwargs["model_path"] == "model-dir"
        assert kwargs["confidence_threshold"] == 0.75
        return pd.DataFrame(
            [
                {
                    "pmid": "12345",
                    "relation_type": "Association",
                    "entity1_text": "BRCA1",
                    "entity1_type": "GeneOrGeneProduct",
                    "entity1_normalized_id": "672",
                    "entity2_text": "breast cancer",
                    "entity2_type": "DiseaseOrPhenotypicFeature",
                    "entity2_normalized_id": "D001943",
                    "evidence_sentence": "BRCA1 is associated with breast cancer.",
                    "relation_source": "biored_model_v1",
                    "novelty": "",
                    "confidence": 0.88,
                }
            ]
        )

    monkeypatch.setattr(biored_pipeline, "predict_biored_relations", fake_predict)

    _, _, relations_df = run_biored_pipeline(
        query="BRCA1 breast cancer",
        data_path=str(pubtator_path),
        relation_mode="model",
        relation_model_path="model-dir",
        confidence_threshold=0.75,
    )

    assert relations_df.iloc[0]["relation_source"] == "biored_model_v1"
    assert relations_df.iloc[0]["confidence"] == 0.88
