from __future__ import annotations

import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")
_PUNCT_TRIM_RE = re.compile(r"^[\s\.,;:!?\"'()\[\]{}]+|[\s\.,;:!?\"'()\[\]{}]+$")


def normalize_nfc(text: str) -> str:
    """Normalize Unicode to NFC and collapse redundant whitespace."""
    if not text:
        return ""
    nfc = unicodedata.normalize("NFC", text)
    return _WHITESPACE_RE.sub(" ", nfc).strip()


def strip_vietnamese_accents(text: str) -> str:
    """Remove Vietnamese diacritics while mapping đ/Đ -> d/D."""
    if not text:
        return ""
    replaced = text.replace("đ", "d").replace("Đ", "D")
    nfd = unicodedata.normalize("NFD", replaced)
    stripped = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFC", stripped)


def build_search_text(text: str) -> str:
    """
    Build dual-form search text (NFC lowercase + accent-folded lowercase)
    for PostgreSQL simple FTS and pg_trgm indexes.
    """
    normalized = normalize_nfc(text).lower()
    folded = strip_vietnamese_accents(normalized).lower()
    if folded == normalized:
        return normalized
    return f"{normalized}\n{folded}"


def normalize_query(text: str) -> str:
    """Canonicalize user queries for cache lookup and lexical matching."""
    cleaned = normalize_nfc(text).lower()
    return _PUNCT_TRIM_RE.sub("", cleaned)


def estimate_tokens(text: str) -> int:
    """Approximate token count for Vietnamese/English prose (~1.45 tokens/word)."""
    words = text.split()
    if not words:
        return 0
    return max(1, int(round(len(words) * 1.45)))
