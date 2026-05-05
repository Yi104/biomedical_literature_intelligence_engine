from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch

# Layer: extraction
# Role: run BioBERT NER inference and convert token labels into entity spans.


def get_label_mapping(model_path: str):
    # Exposes model id->label for UI/debugging and reproducibility checks.
    model = AutoModelForTokenClassification.from_pretrained(model_path)
    id2label = model.config.id2label or {}
    id2label = {int(k): v for k, v in id2label.items()} if id2label else {}
    return dict(sorted(id2label.items(), key=lambda x: x[0]))


def _collect_entities(words_with_labels):
    # Merge BIO token predictions into contiguous entity spans.
    entities = []
    current = None

    for item in words_with_labels:
        label = item["label"]
        token = item["token"]
        index = item["word_index"]

        if label == "O":
            if current is not None:
                entities.append(current)
                current = None
            continue

        if "-" not in label:
            if current is not None:
                entities.append(current)
            current = {"type": label, "tokens": [token], "start": index, "end": index}
            continue

        prefix, ent_type = label.split("-", 1)
        if prefix == "B" or current is None or current["type"] != ent_type:
            if current is not None:
                entities.append(current)
            current = {"type": ent_type, "tokens": [token], "start": index, "end": index}
        else:
            current["tokens"].append(token)
            current["end"] = index

    if current is not None:
        entities.append(current)

    for ent in entities:
        ent["text"] = " ".join(ent["tokens"])
    return entities


@torch.inference_mode()
def ner(model_path: str, text_tokens: list[str], max_length: int = 256):
    """
    Run token-level NER and return both token predictions and merged entities.
    """
    tok = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForTokenClassification.from_pretrained(model_path)
    id2label = model.config.id2label or {}
    id2label = {int(k): v for k, v in id2label.items()} if id2label else {}

    batch = tok(
        [text_tokens],
        is_split_into_words=True,
        truncation=True,
        max_length=max_length,
        return_tensors="pt",
    )
    pred_ids = model(**batch).logits.argmax(-1)[0]
    word_ids = batch.word_ids(0)

    token_predictions = []
    seen_word_ids = set()
    for j, word_id in enumerate(word_ids):
        # Keep only the first subword piece for each input token.
        if word_id is None or word_id in seen_word_ids:
            continue
        seen_word_ids.add(word_id)
        pred_id = int(pred_ids[j].item())
        label = id2label.get(pred_id, str(pred_id))
        token_predictions.append(
            {
                "token": text_tokens[word_id],
                "label": label,
                "label_id": pred_id,
                "word_index": word_id,
            }
        )

    entities = _collect_entities(token_predictions)
    return {"tokens": token_predictions, "entities": entities}


if __name__ == "__main__":
    print("Run inference on PubMed abstracts.")
