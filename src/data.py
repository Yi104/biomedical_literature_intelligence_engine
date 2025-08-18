"""
Dataset loading and token alignment for biomarker NER
This module does:
1. loading biomedical NER datasets (BC5CDR, JNLPBA) from huggingface BigBio
2. Converting their KB schema into flat token-level BIO labels
3. Tokenizing + aligning tokens with labels for modl training.

from huggingface bigbio/bc5cdr:
bc5cdr.py: https://huggingface.co/datasets/bigbio/bc5cdr/blob/main/bc5cdr.py
BUILDER_CONFIGS = [
        BigBioConfig(
            name="bc5cdr_source",
            version=SOURCE_VERSION,
            description="BC5CDR source schema",
            schema="source",
            subset_id="bc5cdr",
        ),
        BigBioConfig(
            name="bc5cdr_bigbio_kb",
            version=BIGBIO_VERSION,
            description="BC5CDR simplified BigBio schema",
            schema="bigbio_kb",
            subset_id="bc5cdr",
        ),


kb_schema: see bigbiohub.py kb_features  https://huggingface.co/datasets/bigbio/bc5cdr/blob/main/bigbiohub.py
each has:
{
passages: the text of abstract or document
entitles: id,text, type, offsets
events:
coreferences
relations
}
"""

from datasets import load_dataset, DatasetDict
from transformers import AutoTokenizer

LABEL_ALL_TOKENS = True

# Available datasets
NER_DATASETS = {
    # "jnlpba": {
    #     "path": "bigbio/jnlpba",
    #     "name": "jnlpba_bigbio_kb",   # BigBio schema?? need to test separately.
    #     "text_column": "tokens",      #
    #     "label_column": "ner_tags",   #
    # },
    "bc5cdr": {
        "path": "bigbio/bc5cdr",
        "name": "bc5cdr_bigbio_kb",   # BigBio schema
        "text_column": "tokens",      #
        "label_column": "ner_tags",   #
    },
}


def load_ner_dataset(name: str, tokenizer_name: str = None, cache_dir: str = None):
    """
    Load a biomedical dataset in BigBio KB schema and convert entities into BIO labels.

    Args:
        name (str): dataset key ("jnlpba" or "bc5cdr")
        tokenizer_name (str): HuggingFace tokenizer (needed to split text into tokens)
        cache_dir (str, optional): local cache directory

    Returns:
        ds (DatasetDict): HuggingFace DatasetDict with train/valid/test splits.
            Each example has:
                - "tokens": list[str], tokenized words
                - "ner_tags": list[int], label IDs for each token (BIO format)
        text_column (str): name of the text column ("tokens")
        label_column (str): name of the label column ("ner_tags")
        labels (list[str]): list of label names (e.g., ["O", "B-Chemical", "I-Chemical", "B-Disease", ...])
    """
    spec = NER_DATASETS[name]

    # Load raw BigBio KB schema dataset
    ds = load_dataset(spec["path"], name=spec["name"], cache_dir=cache_dir)

    # Initialize tokenizer
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_name or "dmis-lab/biobert-base-cased-v1.1")

    # Step 1: Convert KB schema (entities with offsets) into token-level BIO tags
    def kb_to_bio(example):
        text = " ".join(p for passage in example["passages"] for p in passage["text"])
        entities = example["entities"]

        # Tokenize by whitespace (before aligning to HF tokenizer)
        tokens = text.split()
        tags = ["O"] * len(tokens)

        for ent in entities:
            ent_text = " ".join(ent["text"])
            ent_type = ent["type"]

            # find entity in token list
            for i, tok in enumerate(tokens):
                if tok == ent["text"][0]:
                    tags[i] = f"B-{ent_type}"
                    for j in range(1, len(ent["text"])):
                        if i + j < len(tokens):
                            tags[i + j] = f"I-{ent_type}"

        return {"tokens": tokens, "ner_tags_str": tags}

    ds = ds.map(kb_to_bio)

    # Step 2: Build label vocabulary
    unique_tags = set(tag for ex in ds["train"]["ner_tags_str"] for tag in ex)
    labels = sorted(unique_tags)
    label2id = {l: i for i, l in enumerate(labels)}
    id2label = {i: l for l, i in label2id.items()}

    # Step 3: Convert string tags → numeric IDs
    def encode_tags(example):
        return {"ner_tags": [label2id[tag] for tag in example["ner_tags_str"]]}

    ds = ds.map(encode_tags)

    return ds, spec["text_column"], spec["label_column"], labels


def tokenize_and_align_labels(ds, tokenizer: AutoTokenizer, text_col: str, label_col: str,
                              max_length: int, label_all_tokens: bool = LABEL_ALL_TOKENS):
    """
    Tokenize dataset and align BIO labels with subword tokens.

    Args:
        ds (DatasetDict): dataset with "tokens" and "ner_tags"
        tokenizer (AutoTokenizer): HuggingFace tokenizer
        text_col (str): text column ("tokens")
        label_col (str): label column ("ner_tags")
        max_length (int): max sequence length
        label_all_tokens (bool): whether to copy label to all subword pieces or not

    Returns:
        tokenized_ds (DatasetDict): dataset with:
            - input_ids
            - attention_mask
            - labels
    """
    def _align(batch):
        tokenized = tokenizer(batch[text_col], is_split_into_words=True,
                              truncation=True, padding=False, max_length=max_length)
        new_labels = []
        for i, labels in enumerate(batch[label_col]):
            word_ids = tokenized.word_ids(i)
            prev_word_id = None
            label_ids = []
            for word_id in word_ids:
                if word_id is None:
                    label_ids.append(-100)
                elif word_id != prev_word_id:
                    label_ids.append(labels[word_id])
                else:
                    label_ids.append(labels[word_id] if label_all_tokens else -100)
                prev_word_id = word_id
            new_labels.append(label_ids)
        tokenized["labels"] = new_labels
        return tokenized

    return ds.map(_align, batched=True)

