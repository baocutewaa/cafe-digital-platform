from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from rag.text.normalize import normalize_query, strip_vietnamese_accents

_PRICE_UNDER_RE = re.compile(
    r"(?:duoi|tu|toi da|khong qua|nho hon|re hon|tam|khoang|under|below|max|<=|<)\s*"
    r"(\d+(?:[.,]\d{3})?|\d+)\s*(k|ngan|nghin|d|vnd|dong)?\b"
)
_STANDALONE_K_RE = re.compile(r"\b(\d{2,3})\s*k\b")
_STANDALONE_VND_RE = re.compile(r"\b(\d{2,3}[.,]\d{3})\s*(?:d|vnd|dong)?\b")

_STOPWORDS = {
    "a", "an", "and", "are", "at", "bao", "ban", "banh", "bi", "bn", "bo", "buoi",
    "cac", "cai", "can", "cho", "chinh", "chua", "co", "con", "cua", "da", "dang",
    "de", "den", "di", "do", "duoc", "duoi", "em", "gia", "giup", "gi", "hay",
    "hien", "hom", "how", "is", "khac", "khong", "khi", "ko", "la", "lam", "loai",
    "ma", "may", "minh", "mon", "muon", "nao", "nay", "nen", "neu", "nhieu", "nhung",
    "o", "oi", "phai", "quan", "ra", "sao", "shop", "size", "tai", "the", "thi",
    "thong", "tin", "to", "toi", "trong", "tu", "uong", "va", "vay", "ve", "voi",
    "what", "which", "who", "why", "with", "you", "your",
}

_ENGLISH_MARKERS = {
    "what", "which", "where", "when", "how", "price", "cost", "much", "open",
    "close", "closing", "hours", "address", "store", "menu", "recommend",
    "suggest", "allergy", "allergic", "dairy", "nuts", "caffeine", "please",
    "difference", "between", "under", "below",
}

_VIETNAMESE_MARKERS = {
    "gia", "bao", "nhieu", "tien", "mon", "uong", "quan", "chi", "nhanh", "mo",
    "cua", "dong", "khuyen", "mai", "uu", "dai", "ma", "giam", "vi", "dang",
    "ngot", "sua", "di", "ung", "goi", "y", "tu", "van", "khac", "gi", "khong",
    "duoi", "minh", "ban", "tai", "sao", "nao", "o", "dau", "buoi",
}


@dataclass(slots=True)
class ParsedQuery:
    raw_query: str
    normalized_query: str
    ascii_query: str
    language: Literal["vi", "en"] = "vi"
    max_price: int | None = None
    category_slug: str | None = None
    taste_tags: list[str] = field(default_factory=list)
    max_bitterness: int | None = None
    caffeine_level: Literal["none", "low", "medium", "high"] | None = None
    has_milk: bool | None = None
    excluded_allergens: list[str] = field(default_factory=list)
    requested_size: Literal["small", "regular", "large"] | None = None
    is_signature_only: bool | None = None
    store_hint: str | None = None
    search_terms: list[str] = field(default_factory=list)


def _parse_amount(num_str: str, unit: str | None) -> int | None:
    cleaned = num_str.replace(".", "").replace(",", "")
    if not cleaned.isdigit():
        return None
    val = int(cleaned)
    if unit in ("k", "ngan", "nghin") or val < 1000:
        val *= 1000
    if 10_000 <= val <= 500_000:
        return val
    return None


def _detect_language(raw: str, ascii_tokens: set[str]) -> Literal["vi", "en"]:
    has_vi_diacritics = strip_vietnamese_accents(raw.lower()) != raw.lower()
    if has_vi_diacritics:
        return "vi"
    vi_hits = len(ascii_tokens & _VIETNAMESE_MARKERS)
    en_hits = len(ascii_tokens & _ENGLISH_MARKERS)
    if en_hits > vi_hits and en_hits >= 1:
        return "en"
    return "vi"


def parse_query(raw_query: str) -> ParsedQuery:
    normalized = normalize_query(raw_query)
    ascii_q = strip_vietnamese_accents(normalized).lower()
    tokens = [tok for tok in re.findall(r"[a-z0-9]+", ascii_q) if tok]
    token_set = set(tokens)

    language = _detect_language(raw_query, token_set)

    # 1. Price parsing
    max_price: int | None = None
    m_price = _PRICE_UNDER_RE.search(ascii_q)
    if m_price:
        max_price = _parse_amount(m_price.group(1), m_price.group(2))
    if max_price is None:
        m_k = _STANDALONE_K_RE.search(ascii_q)
        if m_k:
            max_price = _parse_amount(m_k.group(1), "k")
    if max_price is None:
        m_vnd = _STANDALONE_VND_RE.search(ascii_q)
        if m_vnd:
            max_price = _parse_amount(m_vnd.group(1), "vnd")

    # 2. Taste tags & bitterness
    taste_tags: list[str] = []
    max_bitterness: int | None = None
    if any(
        p in ascii_q
        for p in ("it dang", "khong dang", "do dang thap", "less bitter", "not bitter", "de uong")
    ):
        taste_tags.append("less_bitter")
        max_bitterness = 2
    if any(p in ascii_q for p in ("ngot", "sweet")):
        taste_tags.append("sweet")
    if any(p in ascii_q for p in ("beo", "creamy", "kem")):
        taste_tags.append("creamy")
    if any(p in ascii_q for p in ("trai cay", "fruity", "cam", "yuzu", "vai", "dao")):
        taste_tags.append("fruity")
    if any(p in ascii_q for p in ("thanh mat", "giai nhiet", "refreshing")):
        taste_tags.append("refreshing")
    if any(p in ascii_q for p in ("dam vi", "dam da", "bold", "strong")):
        taste_tags.append("bold")

    # 3. Caffeine level
    caffeine_level: Literal["none", "low", "medium", "high"] | None = None
    if any(
        p in ascii_q
        for p in (
            "khong caffeine",
            "0 caffeine",
            "no caffeine",
            "caffeine free",
            "decaf",
            "khong mat ngu",
            "buoi toi",
            "toi muon",
        )
    ):
        caffeine_level = "none"
    elif any(
        p in ascii_q
        for p in ("it caffeine", "caffeine thap", "low caffeine", "nhe caffeine", "buoi chieu")
    ):
        caffeine_level = "low"
    elif any(p in ascii_q for p in ("nhieu caffeine", "high caffeine", "tinh tao manh")):
        caffeine_level = "high"

    # 4. Dairy / Milk & Allergens
    has_milk: bool | None = None
    excluded_allergens: list[str] = []
    allergy_ctx_terms = (
        "di ung", "kieng", "tranh", "allergy", "allergic", "intoleran", "khong an", "khong uong"
    )
    has_allergy_ctx = any(k in ascii_q for k in allergy_ctx_terms)
    if any(
        p in ascii_q
        for p in (
            "di ung sua",
            "kieng sua",
            "khong sua",
            "lactose",
            "dairy free",
            "dairy-free",
            "no milk",
            "no dairy",
            "thuan chay",
            "vegan",
        )
    ) or (has_allergy_ctx and any(w in ascii_q for w in ("sua bo", "dairy", " sua "))):
        has_milk = False
        excluded_allergens.append("DAIRY")
    elif "co sua" in ascii_q or "nhieu sua" in ascii_q:
        has_milk = True

    if (
        any(p in ascii_q for p in ("nut allergy", "no nuts", "khong hat"))
        or (has_allergy_ctx and re.search(r"\b(?:hat|nuts|macca|hanh nhan|hazelnut)\b", ascii_q))
    ):
        excluded_allergens.append("NUTS")
    if (
        any(p in ascii_q for p in ("soy allergy", "no soy", "khong dau nanh"))
        or (has_allergy_ctx and re.search(r"\b(?:dau nanh|soy)\b", ascii_q))
    ):
        excluded_allergens.append("SOY")
    if (
        any(p in ascii_q for p in ("gluten free", "gluten-free", "celiac"))
        or (has_allergy_ctx and re.search(r"\b(?:gluten|lua mi|bot mi)\b", ascii_q))
    ):
        excluded_allergens.append("GLUTEN")

    # 5. Category hint (explicit category queries)
    category_slug: str | None = None
    is_signature_only: bool | None = None
    if "signature" in ascii_q or "dac trung" in ascii_q:
        is_signature_only = True
    if "cold brew" in ascii_q or "coldbrew" in ascii_q or "u lanh" in ascii_q:
        category_slug = "cold-brew"
    elif re.search(r"\b(?:banh|pastry|croissant|tiramisu|cheesecake)\b", ascii_q):
        category_slug = "pastry"
    elif re.search(r"\b(?:matcha|tra)\b", ascii_q):
        category_slug = "matcha-tea"
    elif "cacao" in ascii_q or "sua hat" in ascii_q:
        category_slug = "non-coffee"

    # 6. Requested size
    requested_size: Literal["small", "regular", "large"] | None = None
    if re.search(r"\b(?:size\s*s|size nho|small)\b", ascii_q):
        requested_size = "small"
    elif re.search(r"\b(?:size\s*m|size vua|regular)\b", ascii_q):
        requested_size = "regular"
    elif re.search(r"\b(?:size\s*l|size lon|large)\b", ascii_q):
        requested_size = "large"

    # 7. Store hint
    store_hint: str | None = None
    if any(p in ascii_q for p in ("quan 1", "q1", "nguyen hue")):
        store_hint = "nguyen hue"
    elif any(p in ascii_q for p in ("thao dien", "thu duc", "quan 2", "q2", "xuan thuy")):
        store_hint = "thao dien"
    elif any(p in ascii_q for p in ("quan 3", "q3", "vo van tan")):
        store_hint = "vo van tan"

    # 8. Meaningful search terms
    search_terms: list[str] = []
    for tok in tokens:
        if (
            len(tok) >= 2
            and tok not in _STOPWORDS
            and not tok.isdigit()
            and tok not in search_terms
        ):
            search_terms.append(tok)

    return ParsedQuery(
        raw_query=raw_query,
        normalized_query=normalized,
        ascii_query=ascii_q,
        language=language,
        max_price=max_price,
        category_slug=category_slug,
        taste_tags=taste_tags,
        max_bitterness=max_bitterness,
        caffeine_level=caffeine_level,
        has_milk=has_milk,
        excluded_allergens=excluded_allergens,
        requested_size=requested_size,
        is_signature_only=is_signature_only,
        store_hint=store_hint,
        search_terms=search_terms,
    )
