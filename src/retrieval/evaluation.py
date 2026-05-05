import json
import torch

from src.extraction.data import load_ner_dataset
from src.extraction.ner_infer import ner

@torch.inference_mode()
def collect_examples(model_path: str, dataset: str = "bc5cdr", n: int = 20, max_length: int = 256):
    """
    Collect a few sample predictions for qualitative error analysis.
    Args:
        model_path: directory with trained model checkpoint
        dataset: dataset name (currently "bc5cdr")
        n: number of test examples
        max_length: max sequence length
    Returns:
        A list of dicts with tokens and predicted labels
    """
    # Load dataset
    ds, text_col, label_col, label_list = load_ner_dataset(dataset)

    # Select N samples
    total = len(ds["test"])
    n = min(n, total)
    samples = ds["test"].select(range(n))

    examples = []
    for i in range(n):
        words = samples[text_col][i]
        gold_ids = samples[label_col][i]
        gold_labels = [label_list[idx] for idx in gold_ids]
        pred = ner(model_path=model_path, text_tokens=words, max_length=max_length)
        examples.append(
            {
                "tokens": words,
                "gold_labels": gold_labels,
                "predictions": pred["tokens"],
                "entities": pred["entities"],
            }
        )
    return examples


if __name__ == "__main__":
    ex = collect_examples("outputs/best_model")
    with open("outputs/reports/examples.json", "w") as f:
        json.dump(ex, f, indent=2)
