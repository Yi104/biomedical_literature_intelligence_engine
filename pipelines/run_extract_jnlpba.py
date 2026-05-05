import argparse

from src.extraction.jnlpba_pipeline import run_jnlpba_pipeline


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the JNLPBA workflow scaffold.")
    parser.add_argument("--query", type=str, default="IL-2 gene expression")
    parser.add_argument("--model_path", type=str, default="outputs/best_model_jnlpba")
    parser.add_argument("--retmax", type=int, default=20)
    parser.add_argument("--max_length", type=int, default=256)
    args = parser.parse_args()

    try:
        run_jnlpba_pipeline(
            query=args.query,
            model_path=args.model_path,
            retmax=args.retmax,
            max_length=args.max_length,
        )
    except NotImplementedError as e:
        print(f"JNLPBA scaffold: {e}")
