# Training scaffold for BioBERT NER
import json, os
import numpy as np
from dataclasses import dataclass
from transformers import (AutoTokenizer, AutoModelForSequenceClassification, AutoModelForTokenClassification, Trainer, TrainingArguments, DataCollatorForTokenClassification)
from seqeval.metrics import precision_score, recall_score, f1_score, classification_report
from src.data import load_ner_dataset, tokenize_and_align_labels
from src.utils import set_seed

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
    eval_strategy: str
    eval_steps: int
    save_strategy: str
    save_steps: int
    seed: int

def compute_metrics(p, label_list):
    preds, labels = p
    preds = np.argmax(-1)
    true_preds = [
        [label_list[p] for (p, l) in zip(pred, lab) if l != -100]
        for pred, lab in zip(preds, labels)
    ]
    true_labels = [
        [label_list[l] for (p, l) in zip(pred, lab) if l != -100]
        for pred, lab in zip(preds, labels)
    ]
    p = precision_score(true_labels, true_preds)
    r = recall_score(true_labels, true_preds)
    f1 = f1_score(true_labels, true_preds)
    return {"precision": p, "recall": r, "f1": f1}

def main(config_path: str = "configs/base.json"):
    cfg = Config(**json.load(open(config_path)))
    set_seed(cfg.seed)

    ds, text_col, label_col, label_list = load_ner_dataset(cfg.dataset)
    tokenizer = AutoTokenizer.from_pretrained(cfg.model_name)
    tokenized = tokenize_and_align_labels(ds, tokenizer, text_col, label_col, cfg.max_length)

    model = AutoModelForTokenClassification.from_pretrained(cfg.model_name, num_labels=len(label_list))

    args = TrainingArguments(
        output_dir="outputs/checkpoints",
        learning_rate=cfg.learning_rate,
        weight_decay=cfg.weight_decay,
        num_train_epochs=cfg.num_train_epochs,
        per_device_train_batch_size=cfg.per_device_train_batch_size,
        per_device_eval_batch_size=cfg.per_device_eval_batch_size,
        warmup_ratio=cfg.warmup_ratio,
        evaluation_strategy=cfg.eval_strategy,
        save_strategy=cfg.save_strategy,
        eval_steps=cfg.eval_steps,
        save_steps=cfg.save_steps,
        logging_steps=cfg.logging_steps,
        load_best_model_at_end=True,
        metric_for_best_model="f1"
    )

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

    trainer.train()
    metrics = trainer.evaluate(tokenized["test"])  # final metrics

    os.makedirs("outputs/reports", exist_ok=True)
    with open("outputs/reports/test_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

if __name__ == "__main__":
    print('Train BioBERT on biomedical NER here.')
