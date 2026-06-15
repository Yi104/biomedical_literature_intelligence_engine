from __future__ import annotations

from src.extraction.biored_loader import load_biored_pubtator_as_dataframes


def test_biored_pubtator_loader_builds_three_tables(tmp_path):
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

    papers_df, entities_df, relations_df = load_biored_pubtator_as_dataframes(
        pubtator_path=str(pubtator_path)
    )

    assert len(papers_df) == 1
    assert papers_df.iloc[0]["pmid"] == "12345"
    assert len(entities_df) == 2
    assert set(entities_df["normalized_id"]) == {"672", "D001943"}
    assert len(relations_df) == 1
    assert relations_df.iloc[0]["relation_type"] == "Association"
    assert relations_df.iloc[0]["entity1_normalized_id"] == "672"
    assert relations_df.iloc[0]["entity2_normalized_id"] == "D001943"
    assert relations_df.iloc[0]["novelty"] == "Novel"
    assert relations_df.iloc[0]["confidence"] == 1.0
