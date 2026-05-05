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
