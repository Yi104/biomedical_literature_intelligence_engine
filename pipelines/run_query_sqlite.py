from __future__ import annotations

import argparse
import json

from src.kb.schema import DEFAULT_DB_PATH
from src.retrieval.sqlite_service import query_kb


def main():
    parser = argparse.ArgumentParser(description="Query SQLite KB.")
    parser.add_argument("--db_path", type=str, default=DEFAULT_DB_PATH)
    parser.add_argument(
        "--mode",
        choices=["pmid", "normalized_id", "type_keyword"],
        required=True,
    )
    parser.add_argument("--pmid", type=str, default=None)
    parser.add_argument("--normalized_id", type=str, default=None)
    parser.add_argument("--entity_type", type=str, default=None)
    parser.add_argument("--keyword", type=str, default=None)
    args = parser.parse_args()

    result = query_kb(
        mode=args.mode,
        pmid=args.pmid,
        normalized_id=args.normalized_id,
        entity_type=args.entity_type,
        keyword=args.keyword,
        db_path=args.db_path,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
