from __future__ import annotations

import re
import unicodedata

_FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n?", re.DOTALL)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")


def clean_markdown_body(raw_text: str) -> str:
    """Strip YAML frontmatter/HTML comments and normalize NFC & line breaks."""
    text = unicodedata.normalize("NFC", raw_text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _FRONTMATTER_RE.sub("", text, count=1)
    text = _HTML_COMMENT_RE.sub("", text)
    lines = [line.rstrip() for line in text.split("\n")]
    cleaned = "\n".join(lines).strip()
    return _MULTI_NEWLINE_RE.sub("\n\n", cleaned)
