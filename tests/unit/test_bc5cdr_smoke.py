from src.extraction.bc5cdr_pipeline import run_bc5cdr_pipeline


def test_bc5cdr_smoke_mode_is_deterministic():
    papers_df, entities_df = run_bc5cdr_pipeline(
        query="cisplatin kidney diseases",
        smoke=True,
    )

    assert len(papers_df) == 1
    assert len(entities_df) == 2
    assert papers_df.iloc[0]["pmid"] == "SMOKE001"
    assert set(entities_df["entity_type"].tolist()) == {"Chemical", "Disease"}
    assert set(entities_df["normalized_id"].tolist()) == {"CHEBI:27899", "MESH:D007674"}
