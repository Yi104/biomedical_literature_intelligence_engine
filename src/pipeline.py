from __future__ import annotations

from collections import Counter
from typing import Dict, List, Tuple

import pandas as pd

from src.infer import ner
from src.pubmed import fetch_pubmed_details, search_pubmed


def run_search_ner_pipeline(
    query: str,
    model_path: str = "outputs/best_model",
    retmax: int = 20,
    max_length: int = 256,
    year_from: int | None = None,
    year_to: int | None = None,
    journal: str | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    pmids = search_pubmed(
        query=query,
        retmax=retmax,
        year_from=year_from,
        year_to=year_to,
        journal=journal,
    )
    records = fetch_pubmed_details(pmids)

    rows: List[Dict] = []
    entity_rows: List[Dict] = []
    for rec in records:
        if not rec.abstract:
            continue

        tokens = rec.abstract.split()
        pred = ner(model_path=model_path, text_tokens=tokens, max_length=max_length)
        entities = pred["entities"]

        type_counts = Counter(ent["type"] for ent in entities)
        rows.append(
            {
                "pmid": rec.pmid,
                "title": rec.title,
                "year": rec.year,
                "journal": rec.journal,
                "abstract": rec.abstract,
                "entity_count": len(entities),
                "entity_types": ", ".join(
                    f"{k}:{v}" for k, v in sorted(type_counts.items(), key=lambda x: x[0])
                ),
            }
        )

        for ent in entities:
            entity_rows.append(
                {
                    "pmid": rec.pmid,
                    "entity_type": ent["type"],
                    "entity_text": ent["text"],
                    "token_start": ent["start"],
                    "token_end": ent["end"],
                }
            )

    papers_df = pd.DataFrame(rows)
    entities_df = pd.DataFrame(entity_rows)
    return papers_df, entities_df
