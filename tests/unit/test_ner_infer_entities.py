import pytest

from src.extraction import ner_infer as ni
from src.extraction.ner_infer import _collect_entities


def test_collect_entities_merges_bio_spans():
    words_with_labels = [
        {"token": "BRCA1", "label": "B-Gene", "word_index": 0},
        {"token": "mutation", "label": "O", "word_index": 1},
        {"token": "breast", "label": "B-Disease", "word_index": 2},
        {"token": "cancer", "label": "I-Disease", "word_index": 3},
        {"token": "drug", "label": "B-Chemical", "word_index": 4},
    ]
    entities = _collect_entities(words_with_labels)
    assert len(entities) == 3
    assert entities[0]["type"] == "Gene"
    assert entities[1]["text"] == "breast cancer"
    assert entities[2]["type"] == "Chemical"


def test_validate_model_label_mapping_rejects_generic_labels(monkeypatch):
    monkeypatch.setattr(
        ni,
        "get_label_mapping",
        lambda model_path: {0: "LABEL_0", 1: "LABEL_1"},
    )

    with pytest.raises(ValueError, match="does not persist interpretable BIO labels"):
        ni.validate_model_label_mapping(
            "dmis-lab/model-on-hub",
            expected_entity_types={"Chemical", "Disease"},
        )


def test_validate_model_label_mapping_accepts_bc5cdr_bio_labels(monkeypatch):
    monkeypatch.setattr(
        ni,
        "get_label_mapping",
        lambda model_path: {
            0: "O",
            1: "B-Chemical",
            2: "I-Chemical",
            3: "B-Disease",
            4: "I-Disease",
        },
    )

    labels = ni.validate_model_label_mapping(
        "dmis-lab/model-on-hub",
        expected_entity_types={"Chemical", "Disease"},
    )

    assert labels[1] == "B-Chemical"
