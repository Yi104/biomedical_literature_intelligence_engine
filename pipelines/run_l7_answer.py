from __future__ import annotations

import argparse
import json
import logging

from src.agent.controller import run_agent_controller
from src.kb.schema import DEFAULT_DB_PATH
from src.llm.router import LLMOptions, summarize_agent_result_with_provider
from src.logging_utils import finalize_run_manifest, setup_run_logging
from src.output.l7_answer import build_l7_answer


def main() -> None:
    parser = argparse.ArgumentParser(description="Run L5->L6 and emit L7 answer contract.")
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
    parser.add_argument("--relation_mode", choices=["gold", "model"], default="gold")
    parser.add_argument("--confidence_threshold", type=float, default=0.5)
    parser.add_argument("--data_path", type=str, default=None)
    parser.add_argument("--db_path", type=str, default=DEFAULT_DB_PATH)
    parser.add_argument("--provider", choices=["none", "ollama", "openai", "anthropic", "gemini"], default="none")
    parser.add_argument("--llm_model", type=str, default="")
    parser.add_argument("--base_url", type=str, default=None)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max_tokens", type=int, default=512)
    parser.add_argument("--log_level", type=str, default="INFO")
    args = parser.parse_args()
    run_artifacts = setup_run_logging(
        command_name="run_l7_answer",
        log_level=args.log_level,
        args=vars(args),
    )

    try:
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
            relation_mode=args.relation_mode,
            confidence_threshold=args.confidence_threshold,
            db_path=args.db_path,
        )

        options = LLMOptions(
            provider=args.provider,
            model=args.llm_model,
            base_url=args.base_url,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
        l6_result = summarize_agent_result_with_provider(
            question=args.question,
            agent_result=agent_result,
            options=options,
        )

        l7_result = build_l7_answer(
            question=args.question,
            agent_result=agent_result,
            l6_result=l6_result,
        )
        finalize_run_manifest(
            run_artifacts,
            status="completed",
            args=vars(args),
            summary={
                "status": l7_result.get("status"),
                "task": l7_result.get("task"),
                "citation_count": len(l7_result.get("citations", [])),
                "claim_count": len(l7_result.get("claims", [])),
            },
        )
        print(json.dumps(l7_result, ensure_ascii=False, indent=2))
    except Exception as exc:
        logging.getLogger(__name__).exception("run_l7_answer failed")
        finalize_run_manifest(
            run_artifacts,
            status="failed",
            args=vars(args),
            error=exc,
        )
        raise


if __name__ == "__main__":
    main()
