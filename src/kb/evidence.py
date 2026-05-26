from __future__ import annotations

import re
from typing import List


def split_abstract_into_sentences(abstract: str) -> List[str]:
    """
    Split an abstract into deterministic sentence-level evidence text.

    This intentionally uses a small rule-based splitter instead of adding an
    NLP dependency. It is suitable for the first evidence-storage pass and
    can later be replaced by a biomedical sentence segmenter if needed.
    """
    cleaned = re.sub(r"\s+", " ", (abstract or "").strip())
    if not cleaned:
        return []
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", cleaned)
        if sentence.strip()
    ]


def mention_appears_in_sentence(entity_text: str, sentence_text: str) -> bool:
    """
    Decide whether a mention belongs to a stored sentence.

    Current task outputs preserve token offsets but not reliable character
    offsets. Linking by surface occurrence avoids deriving inaccurate
    sentence links from token positions; char-offset linkage is a later
    precision upgrade.
    """
    mention = re.sub(r"\s+", " ", (entity_text or "").strip()).casefold()
    sentence = re.sub(r"\s+", " ", (sentence_text or "").strip()).casefold()
    return bool(mention) and mention in sentence
