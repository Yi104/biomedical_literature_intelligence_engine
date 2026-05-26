from __future__ import annotations

import pytest

from src.contracts.registry import get_schema
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


def test_biored_live_path_is_not_claimed_as_implemented():
    with pytest.raises(FileNotFoundError, match="requires --data_path"):
        run_biored_pipeline(query="BRCA1 breast cancer", smoke=False)
