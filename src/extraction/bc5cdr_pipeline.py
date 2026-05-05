from __future__ import annotations

import argparse
from typing import Tuple

import pandas as pd

from src.retrieval.structured_query import run_search_ner_pipeline

# Task A: gene-disease evidence extraction.
# This module keeps the BC5CDR-specific workflow separate from the broader entity-discovery path.


def run_bc5cdr_pipeline(
    query: str,
    model_path: str = "outputs/best_model",
    retmax: int = 20,
    max_length: int = 256,
    year_from: int | None = None,
    year_to: int | None = None,
    journal: str | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    BC5CDR task wrapper for the current query -> PubMed -> NER -> tables flow.
    """
    return run_search_ner_pipeline(
        query=query,
        model_path=model_path,
        retmax=retmax,
        max_length=max_length,
        year_from=year_from,
        year_to=year_to,
        journal=journal,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BC5CDR task smoke check.")
    parser.add_argument("--query", type=str, default="BRCA1 breast cancer")
    parser.add_argument("--model_path", type=str, default="outputs/best_model")
    parser.add_argument("--retmax", type=int, default=3)
    parser.add_argument("--max_length", type=int, default=256)
    args = parser.parse_args()

    papers_df, entities_df = run_bc5cdr_pipeline(
        query=args.query,
        model_path=args.model_path,
        retmax=args.retmax,
        max_length=args.max_length,
    )
    print(f"OK: bc5cdr papers={len(papers_df)} entities={len(entities_df)}")
