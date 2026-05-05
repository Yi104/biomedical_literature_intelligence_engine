import argparse

from src.extraction.bc5cdr_pipeline import run_bc5cdr_pipeline


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the BC5CDR workflow.")
    parser.add_argument("--query", type=str, default="BRCA1 breast cancer")
    parser.add_argument("--model_path", type=str, default="outputs/best_model")
    parser.add_argument("--retmax", type=int, default=20)
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
    print(f"OK: BC5CDR workflow mode={mode} papers={len(papers_df)} entities={len(entities_df)}")
