from __future__ import annotations

import argparse
import json

from src.agent.controller import run_agent_controller
from src.kb.schema import DEFAULT_DB_PATH
from src.llm.router import LLMOptions, summarize_agent_result_with_provider


def main() -> None:
    parser = argparse.ArgumentParser(description="Run L5 retrieval and build L6 evidence bundle summary.")
    parser.add_argument("--task", choices=["bc5cdr", "jnlpba", "biored"], required=True)
    parser.add_argument(
        "--mode",
        dest="retrieval_mode",
        choices=[
            "pmid",
            "normalized_id",
            "type_keyword",
            "evidence_pmid",
            "evidence_normalized_id",
            "relation_pmid",
            "relation_entity_pair",
        ],
        required=True,
    )
    parser.add_argument("--question", type=str, required=True)
    parser.add_argument("--pmid", type=str, default=None)
    parser.add_argument("--normalized_id", type=str, default=None)
    parser.add_argument("--entity_type", type=str, default=None)
    parser.add_argument("--keyword", type=str, default=None)
    parser.add_argument("--entity1_normalized_id", type=str, default=None)
    parser.add_argument("--entity2_normalized_id", type=str, default=None)
    parser.add_argument("--query", dest="search_query", type=str, default=None)
    parser.add_argument("--allow_refresh", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--retmax", type=int, default=5)
    parser.add_argument("--max_length", type=int, default=256)
    parser.add_argument("--model_path", type=str, default=None)
    parser.add_argument("--data_path", type=str, default=None)
    parser.add_argument("--db_path", type=str, default=DEFAULT_DB_PATH)
    parser.add_argument("--provider", choices=["none", "ollama", "openai", "anthropic", "gemini"], default="none")
    parser.add_argument("--llm_model", type=str, default="")
    parser.add_argument("--base_url", type=str, default=None)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max_tokens", type=int, default=512)
    args = parser.parse_args()

    agent_result = run_agent_controller(
        task=args.task,
        retrieval_mode=args.retrieval_mode,
        pmid=args.pmid,
        normalized_id=args.normalized_id,
        entity_type=args.entity_type,
        keyword=args.keyword,
        entity1_normalized_id=args.entity1_normalized_id,
        entity2_normalized_id=args.entity2_normalized_id,
        search_query=args.search_query,
        retmax=args.retmax,
        max_length=args.max_length,
        model_path=args.model_path,
        allow_refresh=args.allow_refresh,
        smoke=args.smoke,
        data_path=args.data_path,
        db_path=args.db_path,
    )

    options = LLMOptions(
        provider=args.provider,
        model=args.llm_model,
        base_url=args.base_url,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )
    result = summarize_agent_result_with_provider(
        question=args.question,
        agent_result=agent_result,
        options=options,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
