from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, fields
from typing import Dict, List

import numpy as np
from datasets import Dataset
from sklearn.metrics import classification_report, confusion_matrix, f1_score, precision_score, recall_score
import torch
import torch.nn as nn
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

from src.extraction.biored_relation_data import build_biored_relation_samples
from src.extraction.train_utils import set_seed


@dataclass
class RelationConfig:
    model_name: str
    train_pubtator_path: str
    dev_pubtator_path: str
    test_pubtator_path: str | None = None
    pair_mode: str = "gene_disease"
    negative_ratio: int = 1
    max_length: int = 256
    learning_rate: float = 3e-5
    weight_decay: float = 0.01
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 8
    per_device_eval_batch_size: int = 16
    warmup_ratio: float = 0.1
    logging_steps: int = 50
    eval_strategy: str = "epoch"
    save_strategy: str = "epoch"
    seed: int = 42
    max_docs_train: int | None = None
    max_docs_dev: int | None = None
    max_docs_test: int | None = None
    checkpoints_dir: str = "outputs/checkpoints/biored_relations"
    best_model_dir: str = "outputs/best_model_biored_relations"
    report_path: str = "outputs/reports/biored_relations/test_metrics.json"
    class_weight_mode: str = "none"  # none | balanced


def _load_config(config_path: str) -> RelationConfig:
    with open(config_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    allowed = {f.name for f in fields(RelationConfig)}
    filtered = {k: v for k, v in raw.items() if k in allowed}
    return RelationConfig(**filtered)


def _build_split_df(cfg: RelationConfig, split: str):
    if split == "train":
        return build_biored_relation_samples(
            pubtator_path=cfg.train_pubtator_path,
            split="train",
            pair_mode=cfg.pair_mode,
            negative_ratio=cfg.negative_ratio,
            max_docs=cfg.max_docs_train,
            seed=cfg.seed,
        )
    if split == "validation":
        return build_biored_relation_samples(
            pubtator_path=cfg.dev_pubtator_path,
            split="validation",
            pair_mode=cfg.pair_mode,
            # Keep eval split sampling stable so metrics remain comparable
            # across training runs with different train negative ratios.
            negative_ratio=1,
            max_docs=cfg.max_docs_dev,
            seed=cfg.seed + 1,
        )
    if not cfg.test_pubtator_path:
        return None
    return build_biored_relation_samples(
        pubtator_path=cfg.test_pubtator_path,
        split="test",
        pair_mode=cfg.pair_mode,
        # Keep eval split sampling stable for consistent test metrics.
        negative_ratio=1,
        max_docs=cfg.max_docs_test,
        seed=cfg.seed + 2,
    )


def _to_hf_dataset(df, label2id: Dict[str, int], tokenizer, max_length: int) -> Dataset:
    rows = []
    for _, row in df.iterrows():
        rows.append(
            {
                "text": str(row["sentence"]),
                "text_pair": f"{row['head_text']} [SEP] {row['tail_text']}",
                "labels": label2id[str(row["label"])],
            }
        )
    ds = Dataset.from_list(rows)

    def _tok(batch):
        return tokenizer(
            batch["text"],
            batch["text_pair"],
            truncation=True,
            max_length=max_length,
        )

    return ds.map(_tok, batched=True)


def _compute_metrics(eval_pred):
    preds, labels = eval_pred
    yhat = np.argmax(preds, axis=1)
    return {
        "precision_macro": precision_score(labels, yhat, average="macro", zero_division=0),
        "recall_macro": recall_score(labels, yhat, average="macro", zero_division=0),
        "f1_macro": f1_score(labels, yhat, average="macro", zero_division=0),
        "f1_micro": f1_score(labels, yhat, average="micro", zero_division=0),
    }


def _compute_balanced_class_weights(train_df: pd.DataFrame, label2id: Dict[str, int]) -> torch.Tensor:
    counts = train_df["label"].value_counts().to_dict()
    total = float(len(train_df))
    n_classes = float(len(label2id))
    weights = []
    for label, idx in sorted(label2id.items(), key=lambda x: x[1]):
        c = float(counts.get(label, 1.0))
        # sklearn-style balanced weighting
        w = total / (n_classes * c)
        weights.append(w)
    return torch.tensor(weights, dtype=torch.float)


class WeightedTrainer(Trainer):
    def __init__(self, *args, class_weights: torch.Tensor | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._class_weights = class_weights

    def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
        labels = inputs.get("labels")
        outputs = model(**inputs)
        logits = outputs.get("logits")
        if self._class_weights is None:
            loss_fct = nn.CrossEntropyLoss()
        else:
            loss_fct = nn.CrossEntropyLoss(weight=self._class_weights.to(logits.device))
        loss = loss_fct(logits.view(-1, model.config.num_labels), labels.view(-1))
        return (loss, outputs) if return_outputs else loss


def dry_run(config_path: str = "configs/biored_relations.json") -> None:
    cfg = _load_config(config_path)
    train_df = _build_split_df(cfg, "train")
    dev_df = _build_split_df(cfg, "validation")
    print(f"OK: relation dry_run config={config_path}")
    print(f"train_samples={len(train_df)} dev_samples={len(dev_df)} pair_mode={cfg.pair_mode} neg_ratio={cfg.negative_ratio}")
    print(f"train_labels={sorted(set(train_df['label']))[:10]}")


def main(config_path: str = "configs/biored_relations.json", eval_only: bool = False) -> None:
    cfg = _load_config(config_path)
    set_seed(cfg.seed)

    train_df = _build_split_df(cfg, "train")
    dev_df = _build_split_df(cfg, "validation")
    test_df = _build_split_df(cfg, "test")

    label_list: List[str] = sorted(set(train_df["label"]) | set(dev_df["label"]))
    if test_df is not None:
        label_list = sorted(set(label_list) | set(test_df["label"]))
    label2id = {x: i for i, x in enumerate(label_list)}
    id2label = {i: x for x, i in label2id.items()}

    tokenizer = AutoTokenizer.from_pretrained(cfg.model_name)
    train_ds = _to_hf_dataset(train_df, label2id, tokenizer, cfg.max_length)
    dev_ds = _to_hf_dataset(dev_df, label2id, tokenizer, cfg.max_length)
    test_ds = _to_hf_dataset(test_df, label2id, tokenizer, cfg.max_length) if test_df is not None else dev_ds

    if eval_only:
        model = AutoModelForSequenceClassification.from_pretrained(cfg.best_model_dir)
    else:
        model = AutoModelForSequenceClassification.from_pretrained(
            cfg.model_name,
            num_labels=len(label_list),
            id2label=id2label,
            label2id=label2id,
        )

    args = TrainingArguments(
        output_dir=cfg.checkpoints_dir,
        learning_rate=cfg.learning_rate,
        weight_decay=cfg.weight_decay,
        num_train_epochs=cfg.num_train_epochs,
        per_device_train_batch_size=cfg.per_device_train_batch_size,
        per_device_eval_batch_size=cfg.per_device_eval_batch_size,
        warmup_ratio=cfg.warmup_ratio,
        logging_steps=cfg.logging_steps,
        eval_strategy=cfg.eval_strategy,
        save_strategy=cfg.save_strategy,
        load_best_model_at_end=True,
        metric_for_best_model="f1_macro",
        greater_is_better=True,
    )

    class_weights = None
    if cfg.class_weight_mode == "balanced":
        class_weights = _compute_balanced_class_weights(train_df, label2id)
    elif cfg.class_weight_mode != "none":
        raise ValueError("class_weight_mode must be one of: none, balanced")

    trainer = WeightedTrainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=dev_ds,
        tokenizer=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer),
        compute_metrics=_compute_metrics,
        class_weights=class_weights,
    )

    if not eval_only:
        trainer.train()
        trainer.save_model(cfg.best_model_dir)
        tokenizer.save_pretrained(cfg.best_model_dir)

    metrics = trainer.evaluate(test_ds)
    os.makedirs(os.path.dirname(cfg.report_path), exist_ok=True)
    with open(cfg.report_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    # Detailed diagnostics for class imbalance and confusion analysis.
    pred_output = trainer.predict(test_ds)
    y_true = pred_output.label_ids
    y_pred = np.argmax(pred_output.predictions, axis=1)
    labels_sorted = [label for label, _ in sorted(label2id.items(), key=lambda x: x[1])]
    report = classification_report(
        y_true,
        y_pred,
        labels=list(range(len(labels_sorted))),
        target_names=labels_sorted,
        output_dict=True,
        zero_division=0,
    )
    cm = confusion_matrix(
        y_true,
        y_pred,
        labels=list(range(len(labels_sorted))),
    )
    details_path = os.path.join(
        os.path.dirname(cfg.report_path),
        "test_metrics_detailed.json",
    )
    with open(details_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "labels": labels_sorted,
                "classification_report": report,
                "confusion_matrix": cm.tolist(),
                "class_weight_mode": cfg.class_weight_mode,
            },
            f,
            indent=2,
        )
    print(f"OK: relation train/eval done report={cfg.report_path} details={details_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train BioRED relation model.")
    parser.add_argument("--config_path", type=str, default="configs/biored_relations.json")
    parser.add_argument("--dry_run", action="store_true")
    parser.add_argument("--eval_only", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        dry_run(args.config_path)
    else:
        main(args.config_path, eval_only=args.eval_only)
