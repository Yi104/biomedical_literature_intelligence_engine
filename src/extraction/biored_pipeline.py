from __future__ import annotations

from typing import Tuple

import pandas as pd

from src.extraction.biored_loader import load_biored_pubtator_as_dataframes
from src.normalization.rule_based import normalize_entities_df

# Primary target task: BioRED supports gene/protein and disease entities plus
# document-level disease-gene relations. Live mode reads local BioRED PubTator
# annotations; smoke mode establishes the same three-table contract.


def run_biored_pipeline(
    query: str,
    smoke: bool = False,
    data_path: str | None = None,
    max_docs: int | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Return BioRED-shaped papers, entities, and relations.

    BioRED differs from the current BC5CDR/JNLPBA wrappers because a primary
    gene-disease evidence task must carry relation rows, not only NER mentions.
    """
    if not smoke:
        if not data_path:
            raise FileNotFoundError(
                "BioRED live mode requires --data_path to a local PubTator file "
                "(for example Train.PubTator or Dev.PubTator)."
            )
        return load_biored_pubtator_as_dataframes(
            pubtator_path=data_path,
            max_docs=max_docs,
        )

    papers_df = pd.DataFrame(
        [
            {
                "pmid": "SMOKE-BIORED-001",
                "title": "BioRED gene-disease smoke paper",
                "year": "2024",
                "journal": "Smoke Journal",
                "abstract": "BRCA1 is associated with breast cancer.",
                "entity_count": 2,
                "entity_types": "Gene:1, Disease:1",
            }
        ]
    )
    entities_df = normalize_entities_df(
        pd.DataFrame(
            [
                {
                    "pmid": "SMOKE-BIORED-001",
                    "entity_type": "Gene",
                    "entity_text": "BRCA1",
                    "token_start": 0,
                    "token_end": 0,
                },
                {
                    "pmid": "SMOKE-BIORED-001",
                    "entity_type": "Disease",
                    "entity_text": "breast cancer",
                    "token_start": 4,
                    "token_end": 5,
                },
            ]
        )
    )
    relations_df = pd.DataFrame(
        [
            {
                "pmid": "SMOKE-BIORED-001",
                "relation_type": "Disease-Gene",
                "entity1_text": "BRCA1",
                "entity1_type": "Gene",
                "entity1_normalized_id": entities_df.iloc[0]["normalized_id"],
                "entity2_text": "breast cancer",
                "entity2_type": "Disease",
                "entity2_normalized_id": entities_df.iloc[1]["normalized_id"],
                "evidence_sentence": "BRCA1 is associated with breast cancer.",
                "relation_source": "smoke_contract_only",
                "novelty": "Novel",
            }
        ]
    )
    return papers_df, entities_df, relations_df
