from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from rag.ingestion.cleaner import clean_markdown_body

FOLDER_CATEGORY_MAP: dict[str, str] = {
    "menu": "MENU",
    "coffee_guide": "COFFEE_GUIDE",
    "faq": "FAQ",
    "policies": "POLICY",
    "brand": "BRAND",
    "store": "STORE",
}

_FRONTMATTER_EXTRACT_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


@dataclass(slots=True)
class LoadedDocument:
    source_key: str
    doc_key: str
    title: str
    category: str
    language: str
    raw_content: str
    clean_body: str
    content_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)
    is_faq: bool = False


def _infer_category(rel_path: Path, frontmatter: dict[str, Any]) -> str:
    explicit = str(frontmatter.get("category", "")).strip().upper()
    if explicit:
        return explicit
    for part in rel_path.parts:
        mapped = FOLDER_CATEGORY_MAP.get(part.lower())
        if mapped:
            return mapped
    return "BRAND"


def _extract_frontmatter(raw_text: str) -> dict[str, Any]:
    match = _FRONTMATTER_EXTRACT_RE.match(raw_text.replace("\r\n", "\n"))
    if not match:
        return {}
    parsed = yaml.safe_load(match.group(1))
    return parsed if isinstance(parsed, dict) else {}


def _extract_title(frontmatter: dict[str, Any], clean_body: str, path: Path) -> str:
    if frontmatter.get("title"):
        return str(frontmatter["title"]).strip()
    h1 = _H1_RE.search(clean_body)
    if h1:
        return h1.group(1).strip()
    return path.stem.replace("_", " ").replace("-", " ").title()


def load_markdown_file(file_path: Path, root_dir: Path) -> LoadedDocument:
    raw_bytes = file_path.read_bytes()
    content_hash = hashlib.sha256(raw_bytes).hexdigest()
    raw_text = raw_bytes.decode("utf-8")

    rel_path = file_path.resolve().relative_to(root_dir.resolve())
    source_key = rel_path.as_posix()

    frontmatter = _extract_frontmatter(raw_text)
    clean_body = clean_markdown_body(raw_text)
    category = _infer_category(rel_path, frontmatter)
    title = _extract_title(frontmatter, clean_body, file_path)
    language = str(frontmatter.get("language", "vi")).strip().lower() or "vi"

    metadata: dict[str, Any] = {
        "source_key": source_key,
        "category": category,
        "language": language,
        "title": title,
    }
    if frontmatter.get("tags"):
        metadata["tags"] = list(frontmatter["tags"])
    if frontmatter.get("product_slugs"):
        metadata["product_slugs"] = list(frontmatter["product_slugs"])

    is_faq = category == "FAQ" or "### Q:" in clean_body
    return LoadedDocument(
        source_key=source_key,
        doc_key=source_key,
        title=title,
        category=category,
        language=language,
        raw_content=raw_text,
        clean_body=clean_body,
        content_hash=content_hash,
        metadata=metadata,
        is_faq=is_faq,
    )


def load_knowledge_directory(path: Path) -> list[LoadedDocument]:
    if not path.exists():
        raise FileNotFoundError(f"Knowledge base path does not exist: {path}")

    if path.is_file():
        return [load_markdown_file(path, path.parent)]

    files = sorted(p for p in path.rglob("*.md") if p.is_file() and not p.name.startswith("."))
    return [load_markdown_file(file_path, path) for file_path in files]
