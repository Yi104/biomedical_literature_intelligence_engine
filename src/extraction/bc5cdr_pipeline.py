from __future__ import annotations

import argparse
from typing import Tuple

import pandas as pd

from src.normalization.rule_based import normalize_entities_df
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
    smoke: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    BC5CDR task wrapper for the current query -> PubMed -> NER -> tables flow.
    """
    if smoke:
        # Deterministic local smoke path that does not depend on network or model files.
        papers_df = pd.DataFrame(
            [
                {
                    "pmid": "SMOKE001",
                    "title": "Smoke test paper",
                    "year": "2024",
                    "journal": "Smoke Journal",
                    "abstract": "BRCA1 is associated with breast cancer.",
                    "entity_count": 2,
                    "entity_types": "Gene:1, Disease:1",
                }
            ]
        )
        entities_df = pd.DataFrame(
            [
                {
                    "pmid": "SMOKE001",
                    "entity_type": "Gene",
                    "entity_text": "BRCA1",
                    "token_start": 0,
                    "token_end": 0,
                },
                {
                    "pmid": "SMOKE001",
                    "entity_type": "Disease",
                    "entity_text": "breast cancer",
                    "token_start": 5,
                    "token_end": 6,
                },
            ]
        )
        return papers_df, normalize_entities_df(entities_df)

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
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run a local deterministic smoke test without network/model dependencies.",
    )
    args = parser.parse_args()

    papers_df, entities_df = run_bc5cdr_pipeline(
        query=args.query,
        model_path=args.model_path,
        retmax=args.retmax,
        max_length=args.max_length,
        smoke=args.smoke,
    )
    mode = "smoke" if args.smoke else "live"
    print(f"OK: bc5cdr mode={mode} papers={len(papers_df)} entities={len(entities_df)}")
