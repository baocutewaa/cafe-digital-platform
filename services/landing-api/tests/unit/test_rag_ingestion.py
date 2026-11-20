from __future__ import annotations

from pathlib import Path

from rag.ingestion.chunker import chunk_document
from rag.ingestion.loaders import load_knowledge_directory
from rag.text.normalize import (
    build_search_text,
    normalize_nfc,
    normalize_query,
    strip_vietnamese_accents,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
KB_DIR = REPO_ROOT / "data" / "knowledge_base"


def test_vietnamese_normalization_and_search_text() -> None:
    decomposed = "Ca\u0300 phe\u0302   Đa\u0301   Ca\u0302\u0300u Đa\u0302\u0301t"
    assert normalize_nfc(decomposed) == "Cà phê Đá Cầu Đất"
    assert strip_vietnamese_accents("Cà phê Đá Cầu Đất") == "Ca phe Da Cau Dat"

    search_text = build_search_text("Cà Phê Muối Cầu Đất")
    lines = search_text.splitlines()
    assert len(lines) == 2
    assert lines[0] == "cà phê muối cầu đất"
    assert lines[1] == "ca phe muoi cau dat"

    assert normalize_query("  Cold Brew khác gì Espresso?  ") == "cold brew khác gì espresso"


def test_knowledge_base_has_at_least_25_valid_markdown_docs() -> None:
    docs = load_knowledge_directory(KB_DIR)
    assert len(docs) >= 25
    categories = {doc.category for doc in docs}
    assert {"MENU", "COFFEE_GUIDE", "FAQ", "POLICY", "BRAND"} <= categories
    for doc in docs:
        assert doc.title
        assert len(doc.content_hash) == 64
        assert doc.clean_body


def test_chunker_preserves_faq_qa_pairs_and_respects_token_limit() -> None:
    docs = load_knowledge_directory(KB_DIR)
    faq_docs = [d for d in docs if d.is_faq]
    assert len(faq_docs) >= 5

    for doc in docs:
        chunks = chunk_document(doc, target_tokens=320, max_tokens=400)
        assert len(chunks) >= 1
        for idx, chunk in enumerate(chunks):
            assert chunk.chunk_index == idx
            assert chunk.search_text
            assert chunk.token_count > 0
            assert chunk.token_count <= 420, (
                f"Chunk {idx} of {doc.source_key} too large: {chunk.token_count} tokens"
            )
            if doc.is_faq and "### Q:" in chunk.content:
                assert "\nA:" in chunk.content
