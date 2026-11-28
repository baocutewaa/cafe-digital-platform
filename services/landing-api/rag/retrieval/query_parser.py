from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from rag.text.normalize import normalize_query, strip_vietnamese_accents

_PRICE_UNDER_RE = re.compile(
    r"(?:duoi|toi da|khong qua|nho hon|re hon|tam|khoang|muc gia|gia khoang|gia tam|"
    r"voi|cam|co|trong tam|trong khoang|under|below|max|with|<=|<)\s*"
    r"(\d+(?:[.,]\d{3})?|\d+)\s*(k|ngan|nghin|d|vnd|dong)\b"
)
_PRICE_COMPARE_LOOSE_RE = re.compile(
    r"(?:duoi|toi da|khong qua|nho hon|re hon|under|below|max|<=|<)\s*"
    r"(\d+(?:[.,]\d{3})?|\d+)\s*(k|ngan|nghin|d|vnd|dong)?\b"
)
_STANDALONE_K_RE = re.compile(r"\b(\d{2,3})\s*k\b")
_STANDALONE_VND_RE = re.compile(r"\b(\d{2,3}[.,]\d{3})\s*(?:d|vnd|dong)?\b")
_PAREN_VARIANT_PRICE_RE = re.compile(
    r"\([^)]*\b(?:nho|vua|lon|small|regular|large|s|m|l)\b[^)]*"
    r"\b\d{2,3}(?:[.,]\d{3}|\s*k)\b[^)]*\)"
)
_SWEET_NON_PREFERENCE_RE = re.compile(
    r"(?:"
    r"(?:dieu\s+chinh|tuy\s+chinh|muc|do|luong|giam|bot|it|khong|han\s+che|kieng)"
    r"\s+(?:vi\s+|do\s+|muc\s+)?(?:ngot|duong)[a-z]?"
    r"|ngot\s*/\s*da"
    r"|banh\s+ngot"
    r"|(?:less|no|not|adjust|reduce|customize)\s+sweet\w*"
    r"|sweetness(?:\s+level)?"
    r")"
)
_LOW_SWEETNESS_STRICT_RE = re.compile(
    r"(?:\b(?:khong|0)\s+(?:vi\s+)?(?:ngot|duong)[a-z]?\b|"
    r"\b(?:unsweetened|sugar[\s-]*free|no\s+sugar|zero\s+sugar)\b)"
)
_LOW_SWEETNESS_MILD_RE = re.compile(
    r"(?:\b(?:it|bot|nhe|giam|han\s+che|khong\s+hao|khong\s+thich)\s+"
    r"(?:vi\s+|do\s+)?(?:ngot|duong)[a-z]?\b|"
    r"\b(?:less\s+sweet|not\s+too\s+sweet|not\s+sweet|low\s+sugar|lightly\s+sweet)\b)"
)

_CUSTOMIZATION_SIGNALS = (
    "cach thuong thuc",
    "cach uong",
    "thuong thuc",
    "uong sao cho ngon",
    "dieu chinh",
    "tuy chinh",
    "giam ngot",
    "giam duong",
    "pha khong duong",
    "co ho tro giam",
    "muc ngot",
    "do ngot",
    "ngot/da",
    "luong da",
    "it da",
    "da rieng",
    "nhieu da",
    "doi sua",
    "doi sang sua",
    "thay sua",
    "them shot",
    "extra shot",
    "giam shot",
    "customize",
    "customization",
    "adjust sweetness",
    "sugar level",
    "ice level",
)

_PRONOUN_PRODUCT_SIGNALS = (
    "mon nay",
    "ly nay",
    "do uong nay",
    "san pham nay",
    "banh nay",
    "this drink",
    "this item",
)

_STOPWORDS = {
    "a", "ad", "an", "and", "are", "at", "ban", "banh", "bao", "barista", "beo", "bi",
    "bn", "bo", "bot", "buoi", "cac", "cach", "cai", "cam", "can", "chinh", "cho",
    "chon", "chua", "co", "con", "cua", "da", "dam", "dang", "de", "den", "di", "dieu",
    "do", "duoc", "duoi", "duong", "em", "gi", "gia", "giam", "giup", "goi", "hay",
    "hien", "hoac", "hom", "hop", "how", "is", "it", "khac", "khau", "khi", "khong",
    "khoang", "ko", "la", "lam", "loai", "lon", "ly", "ma", "mat", "may", "minh", "mon",
    "mua", "muc", "muon", "nao", "nay", "nen", "neu", "nha", "nhe", "nhieu", "nho",
    "nhung", "nuoc", "o", "oi", "phai", "phu", "quan", "ra", "re", "sao", "shop", "size",
    "tai", "tam", "thanh", "the", "them", "thi", "thich", "thong", "thuc", "thuong",
    "tin", "tim", "to", "toi", "trong", "tu", "tuy", "uong", "va", "van", "vay", "ve",
    "vi", "voi", "vua", "what", "which", "who", "why", "with", "xem", "you", "your",
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
    max_sweetness: int | None = None
    caffeine_level: Literal["none", "low", "medium", "high"] | None = None
    has_milk: bool | None = None
    excluded_allergens: list[str] = field(default_factory=list)
    requested_size: Literal["small", "regular", "large"] | None = None
    is_signature_only: bool | None = None
    store_hint: str | None = None
    is_customization_query: bool = False
    has_pronoun_reference: bool = False
    drinks_only: bool = False
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
    has_vi_diacritics = strip_vietnamese_accents(raw_query.lower()) != raw_query.lower()

    is_customization_query = any(sig in ascii_q for sig in _CUSTOMIZATION_SIGNALS) or bool(
        re.search(r"\b(?:sua\s+hat|it\s+ngot|khong\s+duong)\b.*\bduoc\s+khong\b", ascii_q)
    )
    has_pronoun_reference = any(sig in ascii_q for sig in _PRONOUN_PRODUCT_SIGNALS)

    # 1. Price parsing (ignore descriptive variant prices like "(Vừa (M), 55.000đ)")
    price_scan_q = _PAREN_VARIANT_PRICE_RE.sub(" ", ascii_q)
    is_viewing_context = "minh dang xem" in ascii_q or "dang xem" in ascii_q
    max_price: int | None = None
    m_price = _PRICE_UNDER_RE.search(price_scan_q) or _PRICE_COMPARE_LOOSE_RE.search(price_scan_q)
    if m_price:
        max_price = _parse_amount(m_price.group(1), m_price.group(2))
    elif not is_viewing_context:
        budget_cues = (
            "gia",
            "ngan sach",
            "budget",
            "re",
            "tiet kiem",
            "tim mon",
            "do uong",
            "uong gi",
            "mon gi",
            "mon nao",
            "chon gi",
            "mua gi",
        )
        has_budget_cue = any(cue in price_scan_q for cue in budget_cues)
        m_k = _STANDALONE_K_RE.search(price_scan_q)
        if m_k and has_budget_cue:
            max_price = _parse_amount(m_k.group(1), "k")
        if max_price is None and has_budget_cue:
            m_vnd = _STANDALONE_VND_RE.search(price_scan_q)
            if m_vnd:
                max_price = _parse_amount(m_vnd.group(1), "vnd")

    # 2. Taste tags, bitterness & sweetness ceiling
    taste_tags: list[str] = []
    max_bitterness: int | None = None
    max_sweetness: int | None = None
    if any(
        p in ascii_q
        for p in (
            "it dang",
            "khong dang",
            "do dang thap",
            "khong quen uong dang",
            "ngai dang",
            "less bitter",
            "not bitter",
            "de uong",
        )
    ):
        taste_tags.append("less_bitter")
        max_bitterness = 2

    if not is_customization_query:
        if _LOW_SWEETNESS_STRICT_RE.search(ascii_q):
            max_sweetness = 1
        elif _LOW_SWEETNESS_MILD_RE.search(ascii_q):
            max_sweetness = 2

    sweet_scan_q = _SWEET_NON_PREFERENCE_RE.sub(" ", ascii_q)
    if max_sweetness is None and re.search(r"\b(?:ngot|sweet)\b", sweet_scan_q):
        taste_tags.append("sweet")

    creamy_vi_re = r"\b(?:béo|kem\s+(?:muối|cheese|phô\s*mai|tươi)|sánh\s+mịn|ngậy)\b"
    if (
        (has_vi_diacritics and re.search(creamy_vi_re, normalized))
        or (not has_vi_diacritics and re.search(r"\b(?:beo|creamy)\b", ascii_q))
        or ("creamy" in token_set)
    ):
        taste_tags.append("creamy")

    fruity_vi_re = r"\b(?:trái\s+cây|cam\s+sả|cam\s+vàng|hương\s+cam|vải|đào|dâu|yuzu)\b"
    if (
        (has_vi_diacritics and re.search(fruity_vi_re, normalized))
        or (
            not has_vi_diacritics
            and re.search(r"\b(?:trai\s+cay|cam\s+sa|fruity|citrus|yuzu|lychee|peach)\b", ascii_q)
        )
        or bool(token_set & {"fruity", "citrus", "yuzu", "lychee", "peach"})
    ):
        taste_tags.append("fruity")

    if any(p in ascii_q for p in ("thanh mat", "giai nhiet", "tuoi mat", "refreshing")):
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

    # 4. Dairy / Milk & Allergens (distinguish personal avoidance vs ingredient inspection)
    has_milk: bool | None = None
    excluded_allergens: list[str] = []
    allergy_avoidance_terms = (
        "bi di ung",
        "minh di ung",
        "toi di ung",
        "khach di ung",
        "nguoi di ung",
        "di ung voi",
        "di ung cac",
        "di ung sua",
        "di ung hat",
        "di ung dau nanh",
        "kieng",
        "tranh",
        "allergy to",
        "allergic",
        "intoleran",
        "khong an duoc",
        "khong uong duoc",
    )
    is_inspection_question = bool(
        re.search(r"\bco\s+chua\b|\bchua\s+chat\s+gay\s+di\s+ung\b", ascii_q)
    )
    has_allergy_ctx = (
        any(k in ascii_q for k in allergy_avoidance_terms) and not is_inspection_question
    )
    if (
        any(
            p in ascii_q
            for p in (
                "di ung sua",
                "kieng sua",
                "khong sua",
                "khong chua sua",
                "lactose",
                "dairy free",
                "dairy-free",
                "no milk",
                "no dairy",
                "thuan chay",
                "vegan",
            )
        )
        and not is_inspection_question
    ) or (has_allergy_ctx and any(w in ascii_q for w in ("sua bo", "dairy", " sua "))):
        has_milk = False
        excluded_allergens.append("DAIRY")
    elif ("co sua" in ascii_q or "nhieu sua" in ascii_q) and not is_inspection_question:
        has_milk = True

    nut_avoid_phrases = ("nut allergy", "no nuts", "khong hat", "khong chua cac loai hat")
    if (any(p in ascii_q for p in nut_avoid_phrases) and not is_inspection_question) or (
        has_allergy_ctx and re.search(r"\b(?:hat|nuts|macca|hanh nhan|hazelnut)\b", ascii_q)
    ):
        excluded_allergens.append("NUTS")
    if (
        any(p in ascii_q for p in ("soy allergy", "no soy", "khong dau nanh"))
        and not is_inspection_question
    ) or (has_allergy_ctx and re.search(r"\b(?:dau nanh|soy)\b", ascii_q)):
        excluded_allergens.append("SOY")
    if (
        any(p in ascii_q for p in ("gluten free", "gluten-free", "celiac", "khong chua gluten"))
        and not is_inspection_question
    ) or (has_allergy_ctx and re.search(r"\b(?:gluten|lua mi|bot mi)\b", ascii_q)):
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
    elif (
        has_vi_diacritics
        and re.search(r"\b(?:matcha|trà|ô\s*long|hibiscus|oolong|tea)\b", normalized)
    ) or (
        not has_vi_diacritics
        and re.search(
            r"\b(?:matcha|tra|oolong|hibiscus|tea)\b",
            re.sub(r"\b(?:kiem\s+tra|tra\s+cuu|tra\s+loi|tra\s+tien)\b", " ", ascii_q),
        )
    ):
        category_slug = "matcha-tea"
    elif "cacao" in ascii_q or ("sua hat" in ascii_q and not is_customization_query):
        category_slug = "non-coffee"

    # 6. Requested size (supports "Size M", "Vừa (M)", "(M)", etc.)
    requested_size: Literal["small", "regular", "large"] | None = None
    if re.search(
        r"(?:\bsize\s*s\b|\bsize\s+nho\b|\bnho\s*\(\s*s\s*\)|\(\s*s\s*\)|\bsmall\b)",
        ascii_q,
    ):
        requested_size = "small"
    elif re.search(
        r"(?:\bsize\s*m\b|\bsize\s+vua\b|\bvua\s*\(\s*m\s*\)|\(\s*m\s*\)|\bregular\b)",
        ascii_q,
    ):
        requested_size = "regular"
    elif re.search(
        r"(?:\bsize\s*l\b|\bsize\s+lon\b|\blon\s*\(\s*l\s*\)|\(\s*l\s*\)|\blarge\b)",
        ascii_q,
    ):
        requested_size = "large"

    # 7. Store hint (avoid ambiguous tokens like bare "buoi", which collides with "buổi chiều/tối")
    store_hint: str | None = None
    if any(p in ascii_q for p in ("nguyen dinh thi", "thuy khue", "nam ho tay")):
        store_hint = "nguyen dinh thi"
    elif any(p in ascii_q for p in ("quang an", "tu hoa", "ban dao", "bac ho tay")):
        store_hint = "quang an"
    elif any(p in ascii_q for p in ("trich sai", "phuong buoi", "tay nam ho tay")):
        store_hint = "trich sai"

    has_pastry_word = bool(
        re.search(r"\b(?:banh|pastry|croissant|tiramisu|cheesecake)\b", ascii_q)
    )
    drinks_only = not has_pastry_word and any(
        cue in ascii_q
        for cue in ("uong gi", "uong mon", "do uong", "thuc uong", "mon nuoc", "drink")
    )

    # 8. Meaningful search terms
    search_terms: list[str] = []
    for tok in tokens:
        if (
            len(tok) >= 2
            and tok not in _STOPWORDS
            and not tok.isdigit()
            and not re.fullmatch(r"\d+(?:k|d|vnd|ngan|nghin)", tok)
            and not re.fullmatch(r"ngot[a-z]?", tok)
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
        max_sweetness=max_sweetness,
        caffeine_level=caffeine_level,
        has_milk=has_milk,
        excluded_allergens=excluded_allergens,
        requested_size=requested_size,
        is_signature_only=is_signature_only,
        store_hint=store_hint,
        is_customization_query=is_customization_query,
        has_pronoun_reference=has_pronoun_reference,
        drinks_only=drinks_only,
        search_terms=search_terms,
    )
