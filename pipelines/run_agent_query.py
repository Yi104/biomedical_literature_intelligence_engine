from __future__ import annotations

import argparse
import json

from src.agent.controller import run_agent_controller
from src.kb.schema import DEFAULT_DB_PATH


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deterministic L5 agent controller.")
    parser.add_argument("--task", choices=["bc5cdr", "jnlpba"], default="bc5cdr")
    parser.add_argument(
        "--mode",
        dest="retrieval_mode",
        choices=[
            "pmid",
            "normalized_id",
            "type_keyword",
            "evidence_pmid",
            "evidence_normalized_id",
        ],
        required=True,
    )
    parser.add_argument("--pmid", type=str, default=None)
    parser.add_argument("--normalized_id", type=str, default=None)
    parser.add_argument("--entity_type", type=str, default=None)
    parser.add_argument("--keyword", type=str, default=None)
    parser.add_argument("--query", dest="search_query", type=str, default=None)
    parser.add_argument("--retmax", type=int, default=5)
    parser.add_argument("--max_length", type=int, default=256)
    parser.add_argument("--model_path", type=str, default=None)
    parser.add_argument("--db_path", type=str, default=DEFAULT_DB_PATH)
    parser.add_argument(
        "--allow_refresh",
        action="store_true",
        help="Run the task pipeline and write new results before querying the KB.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Use deterministic local task output when a refresh is run.",
    )
    args = parser.parse_args()

    result = run_agent_controller(
        task=args.task,
        retrieval_mode=args.retrieval_mode,
        pmid=args.pmid,
        normalized_id=args.normalized_id,
        entity_type=args.entity_type,
        keyword=args.keyword,
        search_query=args.search_query,
        retmax=args.retmax,
        max_length=args.max_length,
        model_path=args.model_path,
        allow_refresh=args.allow_refresh,
        smoke=args.smoke,
        db_path=args.db_path,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
