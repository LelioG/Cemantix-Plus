from __future__ import annotations

import re
import unicodedata

from unidecode import unidecode


WORD_PATTERN = re.compile(r"^[a-zà-öø-ÿœæ]+(?:['-][a-zà-öø-ÿœæ]+)*$")


def normalize_word(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "").strip().lower()
    text = text.replace("’", "'").replace("`", "'").replace("´", "'")
    text = re.sub(r"\s+", "", text)
    return text


def ascii_key(value: str) -> str:
    return normalize_word(unidecode(value))


def is_valid_word_shape(value: str) -> bool:
    return bool(WORD_PATTERN.fullmatch(normalize_word(value)))


def letter_count(value: str) -> int:
    cleaned = normalize_word(value).replace("'", "").replace("-", "")
    return len(cleaned)


def mask_word(value: str) -> str:
    normalized = normalize_word(value)
    if len(normalized) <= 2:
        return normalized[0] + "•" * max(0, len(normalized) - 1)
    return normalized[0] + "•" * (len(normalized) - 2) + normalized[-1]


def reveal_pattern(value: str) -> str:
    normalized = normalize_word(value)
    if len(normalized) <= 2:
        return normalized
    middle = "".join("•" if char.isalpha() else char for char in normalized[1:-1])
    return f"{normalized[0]}{middle}{normalized[-1]}"
