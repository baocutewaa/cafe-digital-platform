from __future__ import annotations

import re
from enum import StrEnum

from rag.retrieval.query_parser import ParsedQuery


class IntentType(StrEnum):
    PRODUCT_LOOKUP = "PRODUCT_LOOKUP"
    STORE_INFO = "STORE_INFO"
    PROMOTION_LOOKUP = "PROMOTION_LOOKUP"
    PRODUCT_RECOMMENDATION = "PRODUCT_RECOMMENDATION"
    COFFEE_KNOWLEDGE = "COFFEE_KNOWLEDGE"
    ALLERGEN_INGREDIENT = "ALLERGEN_INGREDIENT"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


_OUT_OF_SCOPE_PATTERNS = (
    r"\b(?:python|javascript|typescript|java|c\+\+|html|css|sql query|react code)\b",
    r"\b(?:viet code|viet chuong trinh|sua loi code|debug code|lap trinh)\b",
    r"\b(?:giai phuong trinh|tich phan|dao ham|toan hoc|chung khoan|crypto|bitcoin)\b",
    r"\b(?:thoi tiet hom nay|du bao thoi tiet|gia vang|ty gia)\b",
)

_CAFE_DOMAIN_KEYWORDS = (
    "ca phe", "cafe", "coffee", "cold brew", "espresso", "latte", "cappuccino",
    "americano", "bac xiu", "matcha", "tra", "cacao", "sua", "croissant", "tiramisu",
    "cheesecake", "banh", "menu", "mon", "do uong", "gia", "size", "brew", "bean",
    "quan", "chi nhanh", "cua hang", "khuyen mai", "uu dai", "voucher", "caffeine",
    "di ung", "arabica", "robusta", "rang", "v60", "calo", "calories", "ngot", "dang",
)

_KNOWLEDGE_SIGNALS = (
    "khac gi", "khac nhau", "la gi", "tai sao", "vi sao", "nhu the nao", "cach pha",
    "quy trinh", "nguon goc", "vung trong", "arabica", "robusta", "medium roast",
    "rang vua", "da day", "con cao", "axit", "chinh sach", "quy dinh", "pha lai",
    "binh ca nhan", "mang binh", "ba ca phe", "cau chuyen", "difference between",
    "how is", "why",
)

_PRICE_OR_FACT_PATTERNS = (
    r"\bgia\b", r"\bbao nhieu\b", r"\bnhieu tien\b", r"\bprice\b", r"\bcost\b",
    r"\bhow much\b", r"\bcalo\b", r"\bcalories\b", r"\bsize\s*[sml]\b",
    r"\bco nhung mon nao\b", r"\bdanh sach mon\b", r"\blist menu\b",
)

_RECOMMENDATION_SIGNALS = (
    "goi y", "tu van", "nen chon", "nen uong", "chon mon", "mon nao hop", "mon nao ngon",
    "phu hop", "recommend", "suggest", "pair", "ghep cap", "thich hop",
)

_STORE_SIGNALS = (
    "gio mo cua", "gio dong cua", "may gio mo", "may gio dong", "dong cua", "mo cua",
    "dia chi", "o dau", "chi nhanh", "cua hang", "tay ho", "ho tay", "vanh dai",
    "ha noi", "nguyen dinh thi", "thuy khue", "quang an", "trich sai", "phuong buoi",
    "dau xe", "cho de xe", "parking", "wifi", "wi-fi", "o cam", "thu cung", "pet",
    "yen tinh", "lam viec", "opening hours", "address",
)

_PROMO_SIGNALS = (
    "khuyen mai", "uu dai", "ma giam gia", "voucher", "promo", "promotion", "discount",
    "combo", "giam gia", "morning20", "coldbrew10k", "chillduo",
)

_ALLERGEN_SIGNALS = (
    "di ung", "allergy", "allergic", "allergen", "thanh phan", "nguyen lieu",
    "lactose", "gluten", "chua sua", "khong sua", "dairy", "dau nanh", "thuan chay",
    "vegan", "nhiem cheo",
)


def classify_intent(parsed: ParsedQuery) -> IntentType:
    q = parsed.ascii_query

    # 1. Out of scope guard (unless clearly cafe-related)
    has_cafe_domain = any(kw in q for kw in _CAFE_DOMAIN_KEYWORDS)
    if any(re.search(pat, q) for pat in _OUT_OF_SCOPE_PATTERNS) and not has_cafe_domain:
        return IntentType.OUT_OF_SCOPE

    if not has_cafe_domain and len(parsed.search_terms) >= 2 and any(
        w in q for w in ("chinh tri", "bong da", "world cup", "phim", "tu vi", "xo so")
    ):
        return IntentType.OUT_OF_SCOPE

    # 2. Allergen & Ingredient safety
    if parsed.excluded_allergens or any(sig in q for sig in _ALLERGEN_SIGNALS):
        allergen_strict = (
            "di ung", "allergy", "allergic", "thanh phan", "nguyen lieu", "gluten", "lactose"
        )
        if any(sig in q for sig in allergen_strict):
            return IntentType.ALLERGEN_INGREDIENT

    # 3. Promotions
    if any(sig in q for sig in _PROMO_SIGNALS):
        return IntentType.PROMOTION_LOOKUP

    # 4. Store hours, address & amenities (unless explicitly asking about written policy)
    if (
        parsed.store_hint or any(sig in q for sig in _STORE_SIGNALS)
    ) and not any(p in q for p in ("chinh sach", "quy dinh", "policy")):
        return IntentType.STORE_INFO

    # 5. Coffee knowledge / policies / brand story
    if any(sig in q for sig in _KNOWLEDGE_SIGNALS):
        return IntentType.COFFEE_KNOWLEDGE

    # 6. Product recommendation / customization vs exact price/catalog lookup
    has_price_fact = any(re.search(pat, q) for pat in _PRICE_OR_FACT_PATTERNS)
    has_rec = any(sig in q for sig in _RECOMMENDATION_SIGNALS)

    if parsed.is_customization_query:
        return (
            IntentType.PRODUCT_RECOMMENDATION
            if has_rec
            else IntentType.COFFEE_KNOWLEDGE
        )

    if has_price_fact and not has_rec:
        return IntentType.PRODUCT_LOOKUP

    if (
        has_rec
        or parsed.taste_tags
        or parsed.max_bitterness is not None
        or parsed.max_sweetness is not None
        or parsed.caffeine_level is not None
        or parsed.has_milk is not None
        or (parsed.max_price is not None and parsed.drinks_only)
    ):
        return IntentType.PRODUCT_RECOMMENDATION

    if (
        parsed.max_price is not None
        or parsed.requested_size is not None
        or parsed.category_slug is not None
    ):
        return IntentType.PRODUCT_LOOKUP

    if has_cafe_domain:
        return IntentType.COFFEE_KNOWLEDGE

    return IntentType.OUT_OF_SCOPE
