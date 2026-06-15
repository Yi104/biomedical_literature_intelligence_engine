from __future__ import annotations

import logging
from typing import Callable, Iterable

import pandas as pd
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.extraction.biored_loader import _select_evidence_sentence
from src.extraction.model_registry import resolve_model_for_eval

logger = logging.getLogger(__name__)

GENE_TYPES = {"GeneOrGeneProduct", "Gene"}
DISEASE_TYPES = {"DiseaseOrPhenotypicFeature", "Disease"}
DEFAULT_RELATION_MODEL_ROOT = "outputs/best_model_biored_relations"
RELATION_COLUMNS = [
    "pmid",
    "relation_type",
    "entity1_text",
    "entity1_type",
    "entity1_normalized_id",
    "entity2_text",
    "entity2_type",
    "entity2_normalized_id",
    "evidence_sentence",
    "relation_source",
    "novelty",
    "confidence",
]

PredictionFn = Callable[[pd.DataFrame], Iterable[tuple[str, float]]]


def _empty_relations_df() -> pd.DataFrame:
    return pd.DataFrame(columns=RELATION_COLUMNS)


def _unique_entities(group: pd.DataFrame, allowed_types: set[str]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    entities: list[dict] = []
    for _, row in group.iterrows():
        entity_type = str(row.get("entity_type", ""))
        normalized_id = str(row.get("normalized_id", ""))
        if entity_type not in allowed_types:
            continue
        if not normalized_id or normalized_id == "UNRESOLVED":
            continue
        key = (entity_type, normalized_id)
        if key in seen:
            continue
        seen.add(key)
        entities.append(
            {
                "entity_type": entity_type,
                "entity_text": str(row.get("entity_text", "")),
                "normalized_id": normalized_id,
            }
        )
    return entities


def build_biored_relation_candidates(
    papers_df: pd.DataFrame,
    entities_df: pd.DataFrame,
) -> pd.DataFrame:
    abstract_by_pmid = {
        str(row.get("pmid", "")): str(row.get("abstract", ""))
        for _, row in papers_df.iterrows()
    }
    rows: list[dict] = []

    for pmid, group in entities_df.groupby("pmid", sort=False):
        pmid = str(pmid)
        abstract = abstract_by_pmid.get(pmid, "")
        genes = _unique_entities(group, GENE_TYPES)
        diseases = _unique_entities(group, DISEASE_TYPES)
        for gene in genes:
            for disease in diseases:
                rows.append(
                    {
                        "pmid": pmid,
                        "sentence": _select_evidence_sentence(
                            abstract,
                            gene["entity_text"],
                            disease["entity_text"],
                        ),
                        "head_text": gene["entity_text"],
                        "head_type": gene["entity_type"],
                        "head_id": gene["normalized_id"],
                        "tail_text": disease["entity_text"],
                        "tail_type": disease["entity_type"],
                        "tail_id": disease["normalized_id"],
                    }
                )
    candidates_df = pd.DataFrame(rows)
    logger.info(
        "BioRED 4A built relation candidates: papers=%d entities=%d candidates=%d",
        len(papers_df),
        len(entities_df),
        len(candidates_df),
    )
    return candidates_df


def relation_predictions_to_dataframe(
    candidates_df: pd.DataFrame,
    predictions: Iterable[tuple[str, float]],
    *,
    confidence_threshold: float = 0.5,
) -> pd.DataFrame:
    rows: list[dict] = []
    skipped_no_relation = 0
    skipped_low_confidence = 0
    for (_, candidate), (label, confidence) in zip(candidates_df.iterrows(), predictions):
        label = str(label)
        confidence = float(confidence)
        if label == "No_Relation":
            skipped_no_relation += 1
            continue
        if confidence < confidence_threshold:
            skipped_low_confidence += 1
            continue
        rows.append(
            {
                "pmid": str(candidate["pmid"]),
                "relation_type": label,
                "entity1_text": str(candidate["head_text"]),
                "entity1_type": str(candidate["head_type"]),
                "entity1_normalized_id": str(candidate["head_id"]),
                "entity2_text": str(candidate["tail_text"]),
                "entity2_type": str(candidate["tail_type"]),
                "entity2_normalized_id": str(candidate["tail_id"]),
                "evidence_sentence": str(candidate["sentence"]),
                "relation_source": "biored_model_v1",
                "novelty": "",
                "confidence": confidence,
            }
        )
    logger.info(
        "BioRED 4A filtered relation predictions: candidates=%d kept=%d no_relation=%d low_confidence=%d threshold=%.3f",
        len(candidates_df),
        len(rows),
        skipped_no_relation,
        skipped_low_confidence,
        confidence_threshold,
    )
    if not rows:
        return _empty_relations_df()
    return pd.DataFrame(rows, columns=RELATION_COLUMNS)


def predict_biored_relations(
    *,
    papers_df: pd.DataFrame,
    entities_df: pd.DataFrame,
    model_path: str | None = None,
    max_length: int = 256,
    batch_size: int = 16,
    confidence_threshold: float = 0.5,
    prediction_fn: PredictionFn | None = None,
) -> pd.DataFrame:
    candidates_df = build_biored_relation_candidates(papers_df, entities_df)
    if candidates_df.empty:
        logger.info("BioRED 4A found no gene-disease candidates to score")
        return _empty_relations_df()

    if prediction_fn is None:
        resolved_model_path = model_path or resolve_model_for_eval(
            DEFAULT_RELATION_MODEL_ROOT
        )
        logger.info(
            "BioRED 4A scoring candidates with model=%s batch_size=%d max_length=%d",
            resolved_model_path,
            batch_size,
            max_length,
        )
        predictions = _predict_with_transformer(
            candidates_df,
            model_path=resolved_model_path,
            max_length=max_length,
            batch_size=batch_size,
        )
    else:
        logger.info("BioRED 4A using injected prediction function for %d candidates", len(candidates_df))
        predictions = list(prediction_fn(candidates_df))

    return relation_predictions_to_dataframe(
        candidates_df,
        predictions,
        confidence_threshold=confidence_threshold,
    )


@torch.inference_mode()
def _predict_with_transformer(
    candidates_df: pd.DataFrame,
    *,
    model_path: str,
    max_length: int,
    batch_size: int,
) -> list[tuple[str, float]]:
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSequenceClassification.from_pretrained(model_path)
    model.eval()
    id2label = {int(k): v for k, v in dict(model.config.id2label).items()}
    logger.info(
        "BioRED 4A loaded relation model labels: model=%s labels=%s",
        model_path,
        sorted(id2label.values()),
    )

    predictions: list[tuple[str, float]] = []
    for start in range(0, len(candidates_df), batch_size):
        batch_df = candidates_df.iloc[start : start + batch_size]
        texts = [str(x) for x in batch_df["sentence"].tolist()]
        text_pairs = [
            f"{row['head_text']} [SEP] {row['tail_text']}"
            for _, row in batch_df.iterrows()
        ]
        batch = tokenizer(
            texts,
            text_pairs,
            truncation=True,
            max_length=max_length,
            padding=True,
            return_tensors="pt",
        )
        outputs = model(**batch)
        probs = torch.softmax(outputs.logits, dim=-1)
        confidences, pred_ids = torch.max(probs, dim=-1)
        for pred_id, confidence in zip(pred_ids.tolist(), confidences.tolist()):
            predictions.append((str(id2label[int(pred_id)]), float(confidence)))
    return predictions
