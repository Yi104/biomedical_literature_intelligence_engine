import pandas as pd

from src.extraction import bc5cdr_pipeline as bp


def test_run_bc5cdr_pipeline_forwards_arguments(monkeypatch):
    sentinel_papers = pd.DataFrame([{"pmid": "1"}])
    sentinel_entities = pd.DataFrame([{"pmid": "1", "entity_type": "Disease"}])

    def fake_run_search_ner_pipeline(**kwargs):
        assert kwargs["query"] == "cisplatin kidney diseases"
        assert kwargs["model_path"] == "outputs/best_model"
        assert kwargs["retmax"] == 5
        assert kwargs["max_length"] == 128
        assert kwargs["year_from"] == 2010
        assert kwargs["year_to"] == 2020
        assert kwargs["journal"] == "Nature"
        assert kwargs["expected_entity_types"] == {"Chemical", "Disease"}
        return sentinel_papers, sentinel_entities

    monkeypatch.setattr(bp, "run_search_ner_pipeline", fake_run_search_ner_pipeline)
    papers_df, entities_df = bp.run_bc5cdr_pipeline(
        query="cisplatin kidney diseases",
        model_path="outputs/best_model",
        retmax=5,
        max_length=128,
        year_from=2010,
        year_to=2020,
        journal="Nature",
    )

    assert papers_df.equals(sentinel_papers)
    assert entities_df.equals(sentinel_entities)
