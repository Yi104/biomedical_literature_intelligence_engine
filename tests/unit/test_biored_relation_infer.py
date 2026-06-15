from __future__ import annotations

import pandas as pd

from src.extraction.biored_relation_infer import (
    build_biored_relation_candidates,
    predict_biored_relations,
    relation_predictions_to_dataframe,
)


def _papers_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "pmid": "P1",
                "title": "BRCA1 and cancer",
                "year": "",
                "journal": "",
                "abstract": (
                    "BRCA1 is associated with breast cancer. "
                    "TP53 was discussed separately."
                ),
                "entity_count": 3,
                "entity_types": "DiseaseOrPhenotypicFeature, GeneOrGeneProduct",
            }
        ]
    )


def _entities_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "pmid": "P1",
                "entity_type": "GeneOrGeneProduct",
                "entity_text": "BRCA1",
                "token_start": 0,
                "token_end": 5,
                "normalized_text": "BRCA1",
                "normalized_id": "672",
                "normalized_source": "biored_annotation_v1",
                "normalized_score": 1.0,
            },
            {
                "pmid": "P1",
                "entity_type": "GeneOrGeneProduct",
                "entity_text": "TP53",
                "token_start": 44,
                "token_end": 48,
                "normalized_text": "TP53",
                "normalized_id": "7157",
                "normalized_source": "biored_annotation_v1",
                "normalized_score": 1.0,
            },
            {
                "pmid": "P1",
                "entity_type": "DiseaseOrPhenotypicFeature",
                "entity_text": "breast cancer",
                "token_start": 25,
                "token_end": 38,
                "normalized_text": "breast cancer",
                "normalized_id": "D001943",
                "normalized_source": "biored_annotation_v1",
                "normalized_score": 1.0,
            },
        ]
    )


def test_build_biored_relation_candidates_for_gene_disease_pairs():
    candidates = build_biored_relation_candidates(_papers_df(), _entities_df())

    assert len(candidates) == 2
    assert set(candidates["head_id"]) == {"672", "7157"}
    assert set(candidates["tail_id"]) == {"D001943"}
    brca1 = candidates[candidates["head_id"] == "672"].iloc[0]
    assert brca1["sentence"] == "BRCA1 is associated with breast cancer."


def test_relation_predictions_to_dataframe_filters_no_relation_and_low_confidence():
    candidates = build_biored_relation_candidates(_papers_df(), _entities_df())

    relations = relation_predictions_to_dataframe(
        candidates,
        [("Association", 0.91), ("No_Relation", 0.99)],
        confidence_threshold=0.5,
    )

    assert list(relations["relation_type"]) == ["Association"]
    assert relations.iloc[0]["relation_source"] == "biored_model_v1"
    assert relations.iloc[0]["confidence"] == 0.91

    filtered = relation_predictions_to_dataframe(
        candidates,
        [("Association", 0.49), ("No_Relation", 0.99)],
        confidence_threshold=0.5,
    )
    assert filtered.empty


def test_predict_biored_relations_accepts_test_prediction_function():
    def fake_predict(candidates: pd.DataFrame):
        assert len(candidates) == 2
        return [("Association", 0.88), ("No_Relation", 0.76)]

    relations = predict_biored_relations(
        papers_df=_papers_df(),
        entities_df=_entities_df(),
        prediction_fn=fake_predict,
    )

    assert len(relations) == 1
    assert relations.iloc[0]["entity1_normalized_id"] == "672"
    assert relations.iloc[0]["entity2_normalized_id"] == "D001943"
