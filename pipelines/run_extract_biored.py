from __future__ import annotations

import argparse

from src.extraction.biored_pipeline import run_biored_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the BioRED primary gene-disease task contract check."
    )
    parser.add_argument("--query", type=str, default="BRCA1 breast cancer")
    parser.add_argument(
        "--data_path",
        type=str,
        default=None,
        help="Path to local BioRED PubTator file for live mode.",
    )
    parser.add_argument(
        "--max_docs",
        type=int,
        default=None,
        help="Optional cap for number of parsed PubTator documents.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run the deterministic BioRED contract check without a live model.",
    )
    args = parser.parse_args()

    papers_df, entities_df, relations_df = run_biored_pipeline(
        query=args.query,
        smoke=args.smoke,
        data_path=args.data_path,
        max_docs=args.max_docs,
    )
    print(
        "OK: biored "
        f"mode={'smoke' if args.smoke else 'live'} "
        f"papers={len(papers_df)} entities={len(entities_df)} relations={len(relations_df)}"
    )
    if args.smoke:
        print(relations_df.to_string(index=False))


if __name__ == "__main__":
    main()
