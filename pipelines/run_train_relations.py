from __future__ import annotations

import argparse

from src.extraction.train_relations import dry_run, main


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run BioRED relation training pipeline.")
    parser.add_argument("--config_path", type=str, default="configs/biored_relations.json")
    parser.add_argument("--dry_run", action="store_true")
    parser.add_argument("--eval_only", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        dry_run(args.config_path)
    else:
        main(args.config_path, eval_only=args.eval_only)
