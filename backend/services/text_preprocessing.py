import re
from collections import Counter

import spacy


try:
    NLP = spacy.blank("en")
except Exception:
    NLP = None


def normalize_text(text: str) -> str:
    text = text.replace("\u2019", "'").replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"[ \t]+", " ", text).strip()


def words(text: str) -> list[str]:
    if NLP:
        return [token.text.lower() for token in NLP.make_doc(text) if not token.is_space and not token.is_punct]
    return re.findall(r"[a-zA-Z0-9+#.]+", text.lower())


def word_count(text: str) -> int:
    return len(words(text))


def token_retention_percent(original: str, optimized: str) -> float:
    original_tokens = Counter(re.findall(r"[a-zA-Z0-9+#.]+", original.lower()))
    optimized_tokens = Counter(re.findall(r"[a-zA-Z0-9+#.]+", optimized.lower()))
    original_count = sum(original_tokens.values())
    if not original_count:
        return 100.0
    retained_count = sum(min(count, optimized_tokens[token]) for token, count in original_tokens.items())
    return round(100 * retained_count / original_count, 1)