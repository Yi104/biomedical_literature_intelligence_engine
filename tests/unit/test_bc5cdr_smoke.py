from src.extraction.bc5cdr_pipeline import run_bc5cdr_pipeline


def test_bc5cdr_smoke_mode_is_deterministic():
    papers_df, entities_df = run_bc5cdr_pipeline(
        query="BRCA1 breast cancer",
        smoke=True,
    )

    assert len(papers_df) == 1
    assert len(entities_df) == 2
    assert papers_df.iloc[0]["pmid"] == "SMOKE001"
    assert set(entities_df["entity_type"].tolist()) == {"Gene", "Disease"}
