
import json
from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch

from src.data import load_ner_dataset

@torch.inference_mode()
def collect_examples(model_path: str, dataset: str = "jnlpba", n: int = 20, max_length: int = 256):
    """
    Collect a few sample predictions for qualitative error analysis.
    Args:
        model_path: directory with trained model checkpoint
        dataset: dataset name ("jnlpba" or "bc5cdr")
        n: number of test examples
        max_length: max sequence length
    Returns:
        A list of dicts with tokens and predicted labels
    """
    # Load dataset and model
    ds, text_col, label_col, label_list = load_ner_dataset(dataset)
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForTokenClassification.from_pretrained(model_path)

    # Select N samples
    samples = ds["test"].select(range(n))
    toks = tokenizer(
        samples[text_col],
        is_split_into_words=True,
        truncation=True,
        padding=True,
        max_length=max_length,
        return_tensors="pt"
    )
    # Predict entity IDs
    out = model(**toks).logits.argmax(-1)

    examples = []
    for i in range(n):
        words = samples[text_col][i]
        word_ids = toks.word_ids(i)
        preds = []
        for j, w_id in enumerate(word_ids):
            if w_id is None:
                continue
            if j >= out.shape[1]:
                break
            pred_id = out[i, j].item()
            token = tokenizer.convert_ids_to_tokens([toks.input_ids[i, j]])[0]
            # Skip subwords like ##ase
            if token.startswith("##"):
                continue
            preds.append((words[w_id], pred_id))
        examples.append({"tokens": words, "preds": preds})
    return examples


if __name__ == "__main__":
    ex = collect_examples("outputs/checkpoints")
    with open("outputs/reports/examples.json", "w") as f:
        json.dump(ex, f, indent=2)

