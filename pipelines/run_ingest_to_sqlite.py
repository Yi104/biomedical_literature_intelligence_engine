from __future__ import annotations

import argparse

from src.extraction.biored_pipeline import run_biored_pipeline
from src.extraction.bc5cdr_pipeline import run_bc5cdr_pipeline
from src.extraction.jnlpba_pipeline import run_jnlpba_pipeline
from src.kb.schema import DEFAULT_DB_PATH, init_sqlite_schema
from src.kb.writer import (
    write_pipeline_outputs_to_sqlite,
    write_pipeline_outputs_with_relations_to_sqlite,
)


def main():
    parser = argparse.ArgumentParser(description="Run task pipeline and ingest results into SQLite.")
    parser.add_argument("--task", choices=["bc5cdr", "jnlpba", "biored"], default="bc5cdr")
    parser.add_argument("--query", type=str, default="cisplatin kidney diseases")
    parser.add_argument("--retmax", type=int, default=5)
    parser.add_argument("--max_length", type=int, default=256)
    parser.add_argument("--model_path", type=str, default=None)
    parser.add_argument("--data_path", type=str, default=None)
    parser.add_argument("--db_path", type=str, default=DEFAULT_DB_PATH)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    init_sqlite_schema(args.db_path)

    if args.task == "bc5cdr":
        model_path = args.model_path or "outputs/best_model"
        papers_df, entities_df = run_bc5cdr_pipeline(
            query=args.query,
            model_path=model_path,
            retmax=args.retmax,
            max_length=args.max_length,
            smoke=args.smoke,
        )
        added_papers, added_mentions, added_normalized, added_sentences = write_pipeline_outputs_to_sqlite(
            papers_df,
            entities_df,
            db_path=args.db_path,
            task=args.task,
        )
        mode = "smoke" if args.smoke else "live"
        print(
            "OK: sqlite ingest "
            f"task={args.task} mode={mode} "
            f"papers_added={added_papers} mentions_added={added_mentions} "
            f"normalized_added={added_normalized} evidence_sentences_added={added_sentences}"
        )
    elif args.task == "jnlpba":
        model_path = args.model_path or "outputs/best_model_jnlpba"
        papers_df, entities_df = run_jnlpba_pipeline(
            query=args.query,
            model_path=model_path,
            retmax=args.retmax,
            max_length=args.max_length,
            smoke=args.smoke,
        )

        added_papers, added_mentions, added_normalized, added_sentences = write_pipeline_outputs_to_sqlite(
            papers_df,
            entities_df,
            db_path=args.db_path,
            task=args.task,
        )
        mode = "smoke" if args.smoke else "live"
        print(
            "OK: sqlite ingest "
            f"task={args.task} mode={mode} "
            f"papers_added={added_papers} mentions_added={added_mentions} "
            f"normalized_added={added_normalized} evidence_sentences_added={added_sentences}"
        )
    else:
        papers_df, entities_df, relations_df = run_biored_pipeline(
            query=args.query,
            smoke=args.smoke,
            data_path=args.data_path,
            max_docs=args.retmax,
        )
        summary = write_pipeline_outputs_with_relations_to_sqlite(
            papers_df,
            entities_df,
            relations_df,
            db_path=args.db_path,
            task="biored",
        )
        mode = "smoke" if args.smoke else "live"
        print(
            "OK: sqlite ingest "
            f"task={args.task} mode={mode} "
            f"papers_added={summary['papers_added']} "
            f"mentions_added={summary['mentions_added']} "
            f"normalized_added={summary['normalized_entities_added']} "
            f"evidence_sentences_added={summary['evidence_sentences_added']} "
            f"relations_added={summary['relations_added']} "
            f"relation_provenance_added={summary['relation_provenance_added']}"
        )


if __name__ == "__main__":
    main()
