from __future__ import annotations

import argparse
from typing import Tuple

import pandas as pd

# Task B: broader biomedical entity discovery.
# This file defines the public interface now, while the JNLPBA-specific model path can be filled in later.


def run_jnlpba_pipeline(
    query: str,
    model_path: str = "outputs/best_model_jnlpba",
    retmax: int = 20,
    max_length: int = 256,
    year_from: int | None = None,
    year_to: int | None = None,
    journal: str | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Placeholder interface for the JNLPBA discovery workflow.

    The eventual implementation should mirror the BC5CDR path but use a task-specific
    JNLPBA-trained model and output schema for broader entity discovery.
    """
    raise NotImplementedError(
        "JNLPBA pipeline is scaffolded but not yet wired to a task-specific model."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JNLPBA task smoke check.")
    parser.add_argument("--query", type=str, default="IL-2 gene expression")
    parser.add_argument("--model_path", type=str, default="outputs/best_model_jnlpba")
    parser.add_argument("--retmax", type=int, default=3)
    parser.add_argument("--max_length", type=int, default=256)
    args = parser.parse_args()

    print("JNLPBA pipeline scaffold loaded.")
    print(f"query={args.query} model_path={args.model_path} retmax={args.retmax} max_length={args.max_length}")
