from src.ingestion.pubmed_client import PubMedRecord
from src.retrieval import structured_query as sq


def test_run_search_ner_pipeline_returns_two_tables(monkeypatch):
    monkeypatch.setattr(sq, "search_pubmed", lambda **kwargs: ["123"])
    monkeypatch.setattr(
        sq,
        "fetch_pubmed_details",
        lambda pmids: [
            PubMedRecord(
                pmid="123",
                title="Paper A",
                abstract="Cisplatin exposure in kidney diseases",
                journal="J1",
                year="2021",
            )
        ],
    )
    monkeypatch.setattr(
        sq,
        "ner",
        lambda model_path, text_tokens, max_length: {
            "tokens": [],
            "entities": [{"type": "Disease", "text": "breast cancer", "start": 3, "end": 4}],
        },
    )

    papers_df, entities_df = sq.run_search_ner_pipeline(
        query="cisplatin kidney diseases",
        model_path="outputs/best_model",
        retmax=1,
    )

    assert len(papers_df) == 1
    assert len(entities_df) == 1
    assert papers_df.iloc[0]["pmid"] == "123"
    assert entities_df.iloc[0]["entity_type"] == "Disease"
