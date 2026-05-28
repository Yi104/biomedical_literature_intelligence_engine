from __future__ import annotations

from src.extraction.biored_relation_data import build_biored_relation_samples


def test_build_biored_relation_samples_ratio_and_labels(tmp_path):
    path = tmp_path / "toy.PubTator"
    path.write_text(
        "\n".join(
            [
                "1001|t|Title",
                "1001|a|BRCA1 is linked to breast cancer and ovarian cancer.",
                "1001\t0\t5\tBRCA1\tGeneOrGeneProduct\t672",
                "1001\t20\t33\tbreast cancer\tDiseaseOrPhenotypicFeature\tD001943",
                "1001\t38\t52\tovarian cancer\tDiseaseOrPhenotypicFeature\tD010051",
                "1001\tAssociation\t672\tD001943\tNovel",
                "",
            ]
        ),
        encoding="utf-8",
    )

    df = build_biored_relation_samples(
        pubtator_path=str(path),
        split="train",
        pair_mode="gene_disease",
        negative_ratio=1,
        seed=7,
    )
    assert not df.empty
    assert set(df["split"]) == {"train"}
    pos = df[df["label"] != "No_Relation"]
    neg = df[df["label"] == "No_Relation"]
    assert len(pos) == 1
    assert len(neg) == 1
    assert set(pos["label"]) == {"Association"}


def test_build_biored_relation_samples_ratio_two(tmp_path):
    path = tmp_path / "toy2.PubTator"
    path.write_text(
        "\n".join(
            [
                "1002|t|Title",
                "1002|a|BRCA1 and TP53 are linked to breast cancer and ovarian cancer.",
                "1002\t0\t5\tBRCA1\tGeneOrGeneProduct\t672",
                "1002\t10\t14\tTP53\tGeneOrGeneProduct\t7157",
                "1002\t30\t43\tbreast cancer\tDiseaseOrPhenotypicFeature\tD001943",
                "1002\t48\t62\tovarian cancer\tDiseaseOrPhenotypicFeature\tD010051",
                "1002\tAssociation\t672\tD001943\tNovel",
                "",
            ]
        ),
        encoding="utf-8",
    )

    df = build_biored_relation_samples(
        pubtator_path=str(path),
        split="train",
        pair_mode="gene_disease",
        negative_ratio=2,
        seed=11,
    )
    pos = df[df["label"] != "No_Relation"]
    neg = df[df["label"] == "No_Relation"]
    assert len(pos) == 1
    # With available candidates, ratio cap should keep up to 2 negatives.
    assert len(neg) <= 2
