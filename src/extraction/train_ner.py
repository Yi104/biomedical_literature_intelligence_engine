"""
Fine-tune BioBERT for Named Entity Recognition (NER).
"""

import json
import os
import numpy as np
import argparse
from dataclasses import dataclass

# Huggingface
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    Trainer,
    TrainingArguments,
    DataCollatorForTokenClassification,
)

# seqeval https://github.com/chakki-works/seqeval，
# sequence labeling evaluation.
# entity-level. for BIO/BILOU (exact span match and entity type match)
from seqeval.metrics import precision_score, recall_score, f1_score

# helpers
from src.extraction.data import load_ner_dataset, tokenize_and_align_labels
from src.extraction.train_utils import set_seed

# Layer: extraction
# Role: train and evaluate the NER model, then export artifacts for inference.

@dataclass
class Config:
    model_name : str
    dataset: str
    max_length: int
    learning_rate: float
    weight_decay: float
    num_train_epochs: int
    per_device_train_batch_size: int
    per_device_eval_batch_size: int
    warmup_ratio: float
    logging_steps: int
    eval_strategy: str  # epochs
    eval_steps: int
    save_strategy: str # epochs
    save_steps: int
    seed: int


def compute_metrics(eval_pred, label_list):
    """
    Compute evaluation metrics for NER (entity-level).
    convert predictions & labels back to strings, then compute seqeval metrics (entity-level).
    :param eval_pred: Tuple[np.ndarray, np.ndarray]
                     - predictions: model outputs (logits), shape (batch_size, seq_len, num_labels)
                        - labels: true labels, shape (batch_size, seq_len)
    :param label_list: List[str], list of label strings, e.g ["O", "B-Chemical", "I-Chemical", "B-Disease" ...]
    :return: metrics  dict {precision, recall, f1_score}
    """
    predictions, labels = eval_pred

    # Greedy token prediction from logits.
    preds = np.argmax(predictions, axis=2)

    # Convert IDs back to label strings, ignore special tokens (-100)
    true_preds = [
        [label_list[p] for (p, l) in zip(pred, lab) if l != -100]
        for pred, lab in zip(preds, labels)
    ]
    true_labels = [
        [label_list[l] for (p, l) in zip(pred, lab) if l != -100]
        for pred, lab in zip(preds, labels)
    ]

    # Compute entity-level metrics
    p = precision_score(true_labels, true_preds)
    r = recall_score(true_labels, true_preds)
    f1 = f1_score(true_labels, true_preds)

    return {"precision": p, "recall": r, "f1": f1}

# ======================= Main Training Pipeline =====================

def main(config_path: str = "configs/base.json"):
    """
    Main training pipeline for BioBERT NER.

    Parameters
    ----------
    config_path : str, optional
        Path to JSON configuration file (default "configs/base.json").

    Workflow
    --------
    1. Load config and set random seed.
    2. Load dataset and label space.
    3. Tokenize input text and align labels to subwords.
    4. Initialize BioBERT model for token classification.
    5. Define training arguments and Trainer.
    6. Train and evaluate model.
    7. Save best checkpoint and final test metrics.
    """

    # 1) Config and reproducibility
    with open(config_path, "r") as f:
        cfg = Config(**json.load(f))
    set_seed(cfg.seed)

    # 2) Dataset loading
    ds, text_col, label_col, label_list = load_ner_dataset(cfg.dataset)

    # 3) Feature construction
    tokenizer = AutoTokenizer.from_pretrained(cfg.model_name)
    tokenized = tokenize_and_align_labels(
        ds, tokenizer, text_col, label_col, cfg.max_length
    )


    # 4) Model init + label mapping persistence
    model = AutoModelForTokenClassification.from_pretrained(
        cfg.model_name,
        num_labels=len(label_list)
    )
    model.config.label2id = {label: idx for idx, label in enumerate(label_list)}
    model.config.id2label = {idx: label for idx, label in enumerate(label_list)}


    # 5) Trainer configuration
    args = TrainingArguments(
        output_dir="outputs/checkpoints",
        learning_rate=cfg.learning_rate,
        weight_decay=cfg.weight_decay,
        num_train_epochs=cfg.num_train_epochs,
        per_device_train_batch_size=cfg.per_device_train_batch_size,
        per_device_eval_batch_size=cfg.per_device_eval_batch_size,
        warmup_ratio=cfg.warmup_ratio,
        eval_strategy=cfg.eval_strategy,
        save_strategy=cfg.save_strategy,
        eval_steps=cfg.eval_steps,
        save_steps=cfg.save_steps,
        logging_steps=cfg.logging_steps,
        save_total_limit=2,            # keep last 2 checkpoints
        load_best_model_at_end=True,
        metric_for_best_model="f1",    # choose F1 for best model
        greater_is_better=True,
    )


    # 6) Trainer assembly
    data_collator = DataCollatorForTokenClassification(tokenizer)

    def _compute(eval_pred):
        return compute_metrics(eval_pred, label_list)

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["validation"],
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=_compute,
    )

    # 7) Fit
    trainer.train()

    # Persist model/tokenizer for app usage.
    trainer.save_model("outputs/best_model")
    tokenizer.save_pretrained("outputs/best_model")


    # 8) Final evaluation report
    metrics = trainer.evaluate(tokenized["test"])
    os.makedirs("outputs/reports", exist_ok=True)
    with open("outputs/reports/test_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)



def dry_run(config_path: str = "configs/base.json"):
    # Fast check for config wiring without launching training.
    with open(config_path, "r") as f:
        cfg = Config(**json.load(f))
    print(f"OK: train_ner dry_run config={config_path}")
    print(f"model_name={cfg.model_name} dataset={cfg.dataset} max_length={cfg.max_length}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train BioBERT NER.")
    parser.add_argument("--config_path", type=str, default="configs/base.json")
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Only validate config wiring, do not train.",
    )
    args = parser.parse_args()

    if args.dry_run:
        dry_run(args.config_path)
    else:
        print("Training BioBERT on biomedical NER...")
        main(args.config_path)
