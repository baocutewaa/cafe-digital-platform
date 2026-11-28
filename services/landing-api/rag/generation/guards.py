from __future__ import annotations

import re

_THINK_BLOCK_RE = re.compile(
    r"<(?:think|thought)>.*?</(?:think|thought)>", re.DOTALL | re.IGNORECASE
)
_LEADING_CLOSE_THINK_RE = re.compile(
    r"^.*?</(?:think|thought)>\s*", re.DOTALL | re.IGNORECASE
)
_UNCLOSED_THINK_RE = re.compile(
    r"<(?:think|thought)>.*$", re.DOTALL | re.IGNORECASE
)
_RAW_THINK_TAG_RE = re.compile(r"</?(?:think|thought)>", re.IGNORECASE)

_LEAKED_THOUGHT_VI_PREFIX_RE = re.compile(
    r"^(?:"
    r"okay[,!.\s]|alright[,!.\s]|hmm+[,!.\s]|well,\s+(?:let|the|i|we)\b|"
    r"let's\s+(?:tackle|check|look|analyze|see|break|find|examine|review|go)|"
    r"let\s+me\s+(?:check|think|see|look|analyze|find|verify|go\s+through)|"
    r"wait[,!.\s]|"
    r"(?:the\s+)?user\s+(?:is\s+asking|wants|asks|asked|says|mentioned)|"
    r"first,\s+(?:i\s+need|looking\s+at|let's|let\s+me|we\s+need|we\s+should)|"
    r"i\s+need\s+to\s+(?:check|find|look|answer|verify|make\s+sure)|"
    r"we\s+need\s+to\s+(?:check|find|look|answer)|"
    r"looking\s+at\s+the\s+(?:data|menu|sql|provided|context)|"
    r"to\s+answer\s+this\s+(?:query|question)|"
    r"thinking\s*process\s*:"
    r")",
    re.IGNORECASE,
)

_LEAKED_THOUGHT_ANY_LANG_RE = re.compile(
    r"^(?:"
    r"okay,\s*let's\s+(?:tackle|check|look|analyze|see)|"
    r"let's\s+tackle\s+this\s+query|"
    r"the\s+user\s+(?:is\s+asking|wants\s+me\s+to)|"
    r"first,\s+(?:i\s+need\s+to\s+check|looking\s+at\s+the\s+sql)|"
    r"thinking\s*process\s*:"
    r")",
    re.IGNORECASE,
)

_LEAKED_INTERNAL_MARKER_RE = re.compile(
    r"(?:"
    r"SQL VERIFIED MENU DATA|KNOWLEDGE BASE CONTEXT|"
    r"which translates to\s+[\"']|"
    r"let me (?:look for items priced at|go through each)|"
    r"the user wants me to suggest|"
    r"i need to check the sql data|"
    r"so maybe this is a contender|"
    r"→\s*too\s+cheap"
    r")",
    re.IGNORECASE,
)

_DANGLING_OPEN_PUNCT_RE = re.compile(r"[\(\[\{,:;—–-]\s*$")
_DANGLING_EN_CONNECTOR_RE = re.compile(
    r"\s+\b(?:and|or|the|a|an|to|of|in|for|with|is|are|that|which|because|but|so|has|have)\s*$",
    re.IGNORECASE,
)


def normalize_quotes(text: str) -> str:
    return text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')


def strip_think_tags(text: str) -> str:
    cleaned = _THINK_BLOCK_RE.sub("", text)
    cleaned = _LEADING_CLOSE_THINK_RE.sub("", cleaned)
    cleaned = _UNCLOSED_THINK_RE.sub("", cleaned)
    return cleaned.strip()


def looks_like_leaked_thinking(text: str, language: str = "vi") -> bool:
    stripped = normalize_quotes(text.strip())
    if not stripped:
        return True
    if _LEAKED_INTERNAL_MARKER_RE.search(stripped):
        return True
    if _LEAKED_THOUGHT_ANY_LANG_RE.match(stripped):
        return True
    if language == "vi" and _LEAKED_THOUGHT_VI_PREFIX_RE.match(stripped):
        return True
    return False


def is_corrupted_cached_answer(text: str, language: str = "vi") -> bool:
    """
    Detect poisoned or truncated answers so they are never served from or saved
    into `answer_cache` (e.g. leaked chain-of-thought or mid-sentence cutoffs).
    """
    if not text or not text.strip():
        return True
    if _RAW_THINK_TAG_RE.search(text):
        return True
    stripped = strip_think_tags(text)
    if looks_like_leaked_thinking(stripped, language):
        return True
    if stripped.count("**") % 2 == 1:
        return True
    if _DANGLING_OPEN_PUNCT_RE.search(stripped):
        return True
    if language == "vi" and _DANGLING_EN_CONNECTOR_RE.search(stripped):
        return True
    return False
