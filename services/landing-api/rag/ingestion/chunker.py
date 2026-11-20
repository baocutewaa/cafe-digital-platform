from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from rag.ingestion.loaders import LoadedDocument
from rag.text.normalize import build_search_text, estimate_tokens

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$")
_FAQ_SPLIT_RE = re.compile(r"(?=^###\s+Q:\s*)", re.MULTILINE)


@dataclass(slots=True)
class TextChunk:
    chunk_index: int
    content: str
    search_text: str
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


def _split_paragraphs_with_limit(
    header_prefix: str,
    body_text: str,
    target_tokens: int,
    max_tokens: int,
    overlap_tokens: int,
) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body_text) if p.strip()]
    if not paragraphs:
        return [header_prefix.strip()] if header_prefix.strip() else []

    chunks: list[str] = []
    current_parts: list[str] = []

    def render(parts: list[str]) -> str:
        joined = "\n\n".join(parts)
        return f"{header_prefix}\n\n{joined}".strip() if header_prefix else joined

    for para in paragraphs:
        candidate_parts = [*current_parts, para]
        candidate_text = render(candidate_parts)
        if current_parts and estimate_tokens(candidate_text) > max_tokens:
            chunks.append(render(current_parts))
            # Keep short trailing paragraph overlap when helpful
            if overlap_tokens > 0 and estimate_tokens(current_parts[-1]) <= overlap_tokens:
                current_parts = [current_parts[-1], para]
            else:
                current_parts = [para]
        else:
            current_parts = candidate_parts

        if estimate_tokens(render(current_parts)) >= target_tokens and len(current_parts) > 1:
            chunks.append(render(current_parts))
            current_parts = []

    if current_parts:
        chunks.append(render(current_parts))

    return chunks


def _chunk_faq_document(
    doc: LoadedDocument,
    max_tokens: int,
) -> list[tuple[str, str]]:
    """Keep each FAQ Q-A pair intact inside a single chunk."""
    raw_blocks = [b.strip() for b in _FAQ_SPLIT_RE.split(doc.clean_body) if b.strip()]
    qa_pairs: list[tuple[str, str]] = []
    intro_heading = doc.title

    for block in raw_blocks:
        if not block.startswith("### Q:"):
            # Skip pure document H1/intro header before first question
            continue
        lines = block.splitlines()
        question_line = lines[0].replace("###", "").strip()
        chunk_body = f"[{doc.title}]\n{block}"
        if estimate_tokens(chunk_body) <= max_tokens:
            qa_pairs.append((question_line, chunk_body))
        else:
            # Split long Q-A only at paragraph level while preserving the question prefix
            answer_body = "\n".join(lines[1:]).strip()
            sub_chunks = _split_paragraphs_with_limit(
                f"[{doc.title}]\n{lines[0]}",
                answer_body,
                target_tokens=320,
                max_tokens=max_tokens,
                overlap_tokens=0,
            )
            for part in sub_chunks:
                qa_pairs.append((question_line, part))

    if not qa_pairs and doc.clean_body.strip():
        qa_pairs.append((intro_heading, doc.clean_body.strip()))
    return qa_pairs


def _extract_markdown_sections(doc: LoadedDocument) -> list[tuple[str, str]]:
    h1_title = doc.title
    h2_title = ""
    sections: list[tuple[str, str]] = []
    buffer: list[str] = []

    def current_header() -> str:
        if h2_title and h2_title != h1_title:
            return f"[{h1_title} > {h2_title}]"
        return f"[{h1_title}]"

    for line in doc.clean_body.splitlines():
        match = _HEADING_RE.match(line.strip())
        if match:
            hashes, title_text = match.group(1), match.group(2).strip()
            if len(hashes) == 1:
                h1_title = title_text
                continue
            if len(hashes) == 2:
                if buffer:
                    sections.append((current_header(), "\n".join(buffer).strip()))
                    buffer = []
                h2_title = title_text
                continue
        buffer.append(line)

    if buffer:
        sections.append((current_header(), "\n".join(buffer).strip()))

    return [(hdr, body) for hdr, body in sections if body]


def chunk_document(
    doc: LoadedDocument,
    target_tokens: int = 320,
    max_tokens: int = 400,
    overlap_tokens: int = 45,
) -> list[TextChunk]:
    """
    Split a Markdown/FAQ document into semantic chunks (~250-400 tokens),
    preserving Q-A pairs for FAQs and merging undersized sections cleanly.
    """
    raw_chunks: list[tuple[str, str]] = []

    if doc.is_faq:
        raw_chunks = _chunk_faq_document(doc, max_tokens=max_tokens)
    else:
        sections = _extract_markdown_sections(doc)
        if not sections:
            raw_chunks = [(doc.title, doc.clean_body.strip())]
        else:
            # Group smaller adjacent sections when combined tokens <= target_tokens
            pending_texts: list[str] = []
            pending_section = doc.title

            for header, body in sections:
                sec_text = f"{header}\n{body}".strip()
                sec_tokens = estimate_tokens(sec_text)
                if sec_tokens > max_tokens:
                    if pending_texts:
                        raw_chunks.append((pending_section, "\n\n".join(pending_texts)))
                        pending_texts = []
                    for part in _split_paragraphs_with_limit(
                        header, body, target_tokens, max_tokens, overlap_tokens
                    ):
                        raw_chunks.append((header.strip("[]"), part))
                    continue

                combined = "\n\n".join([*pending_texts, sec_text])
                if pending_texts and estimate_tokens(combined) > max_tokens:
                    raw_chunks.append((pending_section, "\n\n".join(pending_texts)))
                    pending_texts = [sec_text]
                    pending_section = header.strip("[]")
                else:
                    if not pending_texts:
                        pending_section = header.strip("[]")
                    pending_texts.append(sec_text)
                    if estimate_tokens("\n\n".join(pending_texts)) >= 250:
                        raw_chunks.append((pending_section, "\n\n".join(pending_texts)))
                        pending_texts = []

            if pending_texts:
                raw_chunks.append((pending_section, "\n\n".join(pending_texts)))

    chunks: list[TextChunk] = []
    for idx, (section_label, text) in enumerate(raw_chunks):
        chunk_meta = {
            **doc.metadata,
            "section": section_label,
            "chunk_index": idx,
        }
        chunks.append(
            TextChunk(
                chunk_index=idx,
                content=text,
                search_text=build_search_text(text),
                token_count=estimate_tokens(text),
                metadata=chunk_meta,
            )
        )
    return chunks
