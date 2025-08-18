# Inference scaffold
from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch

LABELS = None  # load from dataset

@torch.inference_mode()
def ner(model_path: str, text_tokens: list[str], max_length: int = 256):
    tok = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForTokenClassification.from_pretrained(model_path)
    batch = tok([text_tokens], is_split_into_words=True, truncation=True, max_length=max_length, return_tensors="pt")
    logits = model(**batch).logits.argmax(-1)[0]
    word_ids = batch.word_ids(0)
    out = []
    prev = None
    for j, w_id in enumerate(word_ids):
        if w_id is None: continue
        token = tok.convert_ids_to_tokens([batch.input_ids[0, j]])[0]
        if token.startswith("##"): continue
        out.append((text_tokens[w_id], int(logits[j].item())))
        prev = w_id
    return out
if __name__ == "__main__":
    print('Run inference on PubMed abstracts.')
