from __future__ import annotations

import logging
from typing import Tuple

import pandas as pd

from src.extraction.biored_loader import load_biored_pubtator_as_dataframes
from src.extraction.biored_relation_infer import predict_biored_relations
from src.normalization.rule_based import normalize_entities_df

logger = logging.getLogger(__name__)

# Primary target task: BioRED supports gene/protein and disease entities plus
# document-level disease-gene relations. Live mode reads local BioRED PubTator
# annotations; smoke mode establishes the same three-table contract.


def run_biored_pipeline(
    query: str,
    smoke: bool = False,
    data_path: str | None = None,
    max_docs: int | None = None,
    retmax: int | None = None,
    max_length: int = 256,
    relation_mode: str = "gold",
    relation_model_path: str | None = None,
    confidence_threshold: float = 0.5,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Return BioRED-shaped papers, entities, and relations.

    BioRED differs from the current BC5CDR/JNLPBA wrappers because a primary
    gene-disease evidence task must carry relation rows, not only NER mentions.
    """
    if max_docs is None:
        max_docs = retmax
    logger.info(
        "BioRED pipeline start: smoke=%s relation_mode=%s data_path=%s max_docs=%s",
        smoke,
        relation_mode,
        data_path,
        max_docs,
    )
    if not smoke:
        if not data_path:
            raise FileNotFoundError(
                "BioRED live mode requires --data_path to a local PubTator file "
                "(for example Train.PubTator or Dev.PubTator)."
            )
        papers_df, entities_df, relations_df = load_biored_pubtator_as_dataframes(
            pubtator_path=data_path,
            max_docs=max_docs,
        )
        logger.info(
            "BioRED pipeline loaded PubTator tables: papers=%d entities=%d relations=%d",
            len(papers_df),
            len(entities_df),
            len(relations_df),
        )
        if relation_mode == "gold":
            logger.info("BioRED pipeline returning gold relations")
            return papers_df, entities_df, relations_df
        if relation_mode == "model":
            predicted_relations_df = predict_biored_relations(
                papers_df=papers_df,
                entities_df=entities_df,
                model_path=relation_model_path,
                max_length=max_length,
                confidence_threshold=confidence_threshold,
            )
            logger.info(
                "BioRED pipeline returning model relations: predicted_relations=%d",
                len(predicted_relations_df),
            )
            return (
                papers_df,
                entities_df,
                predicted_relations_df,
            )
        raise ValueError("relation_mode must be one of: gold, model")

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
                "confidence": 1.0,
            }
        ]
    )
    logger.info(
        "BioRED pipeline returning smoke fixture: papers=%d entities=%d relations=%d",
        len(papers_df),
        len(entities_df),
        len(relations_df),
    )
    return papers_df, entities_df, relations_df
