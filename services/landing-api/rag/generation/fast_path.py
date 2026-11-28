from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.menu import ProductDetailOut
from rag.generation.intent_router import IntentType
from rag.retrieval.context_builder import RetrievalResult, _is_pairing_or_alternatives_query

_SIZE_LABEL_VI = {"small": "S (Nhỏ)", "regular": "M (Vừa)", "large": "L (Lớn)"}
_SIZE_LABEL_EN = {"small": "Small (S)", "regular": "Regular (M)", "large": "Large (L)"}

_CAFFEINE_LABEL_VI = {
    "none": "Không caffeine",
    "low": "Caffeine nhẹ",
    "medium": "Caffeine vừa",
    "high": "Caffeine đậm",
}

_ALLERGEN_NAME_VI = {
    "DAIRY": "Sữa bò (DAIRY)",
    "NUTS": "Các loại hạt (NUTS)",
    "SOY": "Đậu nành (SOY)",
    "GLUTEN": "Bột mì / Gluten (GLUTEN)",
}

_BRACKET_HEADER_RE = re.compile(r"(?m)^\s*\[[^\]\n]+\]\s*\n?")
_INLINE_SECTION_BRACKET_RE = re.compile(r"\[[^\]\n]+>[^\]\n]+\]\s*")
_TECH_TOKEN_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("`less_bitter`", "ít đắng"),
    ("less_bitter", "ít đắng"),
    ("`dairy_free`", "không sữa bò"),
    ("dairy_free", "không sữa bò"),
    ("`has_milk = false`", "không chứa sữa bò"),
    ("has_milk = false", "không chứa sữa bò"),
    ("`caffeine_level = none`", "không caffeine"),
    ("caffeine_level = none", "không caffeine"),
    ("`caffeine_level = low`", "caffeine nhẹ"),
    ("caffeine_level = low", "caffeine nhẹ"),
    ("`caffeine_level = medium`", "caffeine vừa"),
    ("caffeine_level = medium", "caffeine vừa"),
    ("`caffeine_level = high`", "caffeine đậm"),
    ("caffeine_level = high", "caffeine đậm"),
)

_AMENITY_VI = {
    "wifi": "Wi-Fi tốc độ cao",
    "parking": "Chỗ đậu xe",
    "ac": "Máy lạnh",
    "work_friendly": "Phù hợp làm việc",
    "power_outlets": "Nhiều ổ cắm điện",
    "pour_over_bar": "Quầy Pour-over Bar",
    "outdoor_garden": "Sân vườn ngoài trời",
    "pet_friendly": "Thân thiện thú cưng",
    "quiet_zone": "Khu vực yên tĩnh",
    "meeting_table": "Bàn họp nhóm",
}


@dataclass(slots=True)
class FastPathResponse:
    handled: bool
    answer: str
    intent: IntentType


def _fmt_vnd(amount: int) -> str:
    return f"{amount:,}đ".replace(",", ".")


def _format_product_prices_line(prod: ProductDetailOut, lang: str, req_size: str | None) -> str:
    avail = [v for v in prod.variants if v.is_available]
    if not avail:
        if lang == "vi":
            return f"- **{prod.name_vi}**: Tạm hết hàng."
        return f"- **{prod.name_en}**: Currently unavailable."

    size_map = _SIZE_LABEL_VI if lang == "vi" else _SIZE_LABEL_EN
    if req_size:
        matched = next((v for v in avail if v.size == req_size), None)
        others = ", ".join(f"{size_map[v.size]}: {_fmt_vnd(v.price_vnd)}" for v in avail)
        if matched:
            if lang == "vi":
                return (
                    f"- **{prod.name_vi}** — Size **{size_map[matched.size]}**: "
                    f"**{_fmt_vnd(matched.price_vnd)}** "
                    f"({matched.calories_kcal or '?'} kcal). Các size: {others}."
                )
            return (
                f"- **{prod.name_en}** — **{size_map[matched.size]}**: "
                f"**{_fmt_vnd(matched.price_vnd)}** "
                f"({matched.calories_kcal or '?'} kcal). All sizes: {others}."
            )

    all_sizes = " | ".join(f"{size_map[v.size]}: {_fmt_vnd(v.price_vnd)}" for v in avail)
    name = prod.name_vi if lang == "vi" else prod.name_en
    return f"- **{name}**: {all_sizes}"


def _format_store_info(retrieval: RetrievalResult) -> str:
    lang = retrieval.parsed_query.language
    stores = retrieval.stores
    if not stores:
        return (
            "Hiện tại hệ thống chưa tìm thấy chi nhánh phù hợp."
            if lang == "vi"
            else "No matching store branch was found."
        )

    lines: list[str] = [
        "Thông tin chi nhánh BREW & BEAN:" if lang == "vi" else "BREW & BEAN Store Information:"
    ]
    for s in stores:
        today = s.today_hours
        if today and not today.is_closed:
            hours_str = f"{today.open_time.strftime('%H:%M')}–{today.close_time.strftime('%H:%M')}"
        else:
            hours_str = "Nghỉ hôm nay" if lang == "vi" else "Closed today"

        status = (
            ("Đang mở cửa" if s.is_open_now else "Đã đóng cửa")
            if lang == "vi"
            else ("Open now" if s.is_open_now else "Closed")
        )
        amenities_str = (
            ", ".join(_AMENITY_VI.get(a, a) for a in s.amenities)
            if lang == "vi"
            else ", ".join(s.amenities)
        )
        if lang == "vi":
            lines.append(
                f"- **{s.name}** ({status} · Hôm nay: {hours_str})\n"
                f"  Địa chỉ: {s.address} | SĐT: {s.phone or '—'}\n"
                f"  Tiện ích: {amenities_str}"
            )
        else:
            lines.append(
                f"- **{s.name}** ({status} · Today: {hours_str})\n"
                f"  Address: {s.address} | Phone: {s.phone or '—'}\n"
                f"  Amenities: {amenities_str}"
            )
    return "\n".join(lines)


def _format_promotions(retrieval: RetrievalResult) -> str:
    lang = retrieval.parsed_query.language
    promos = retrieval.promotions
    if not promos:
        return (
            "Hiện tại chưa có chương trình khuyến mãi nào đang áp dụng."
            if lang == "vi"
            else "There are no active promotions right now."
        )

    lines: list[str] = [
        "Các chương trình ưu đãi đang áp dụng tại BREW & BEAN:"
        if lang == "vi"
        else "Active promotions at BREW & BEAN:"
    ]
    for p in promos:
        code_part = f" | Mã: `{p.promo_code}`" if p.promo_code else ""
        title = p.title_vi if lang == "vi" else (p.title_en or p.title_vi)
        lines.append(
            f"- **{title}**{code_part}\n  {p.summary_vi}\n  *Điều kiện:* {p.conditions_vi}"
        )
    return "\n".join(lines)


def try_build_fast_path(retrieval: RetrievalResult) -> FastPathResponse:
    """Build deterministic SQL/template responses for fast-path intents without calling LLM."""
    lang = retrieval.parsed_query.language
    intent = retrieval.intent

    if intent == IntentType.OUT_OF_SCOPE:
        if lang == "vi":
            msg = (
                "Mình là **Bean AI Barista** của **BREW & BEAN**, chỉ hỗ trợ tư vấn thực đơn, "
                "giá đồ uống, thành phần dị ứng, giờ mở cửa chi nhánh, ưu đãi và kiến thức "
                "pha chế cà phê. Bạn muốn khám phá món nào hôm nay?"
            )
        else:
            msg = (
                "I am **Bean AI Barista** for **BREW & BEAN**, specialized in our menu, prices, "
                "allergens, store hours, promotions, and specialty coffee craft. "
                "How can I help you with our menu?"
            )
        return FastPathResponse(handled=True, answer=msg, intent=intent)

    if intent == IntentType.STORE_INFO:
        return FastPathResponse(handled=True, answer=_format_store_info(retrieval), intent=intent)

    if intent == IntentType.PROMOTION_LOOKUP:
        return FastPathResponse(handled=True, answer=_format_promotions(retrieval), intent=intent)

    if intent == IntentType.PRODUCT_LOOKUP:
        prods = retrieval.products
        if not prods:
            msg = (
                "Mình chưa tìm thấy món khớp chính xác trong thực đơn hiện tại. "
                "Bạn có thể cho mình biết tên món hoặc mức giá bạn muốn tìm (ví dụ: dưới 45k) nhé!"
                if lang == "vi"
                else "I couldn't find an exact matching item on our current menu. "
                "Please share the drink name or budget (e.g., under 45k) you are looking for."
            )
            return FastPathResponse(handled=True, answer=msg, intent=intent)

        header = (
            "Thông tin giá niêm yết từ hệ thống BREW & BEAN:"
            if lang == "vi"
            else "Official menu pricing from BREW & BEAN:"
        )
        req_size = retrieval.parsed_query.requested_size
        lines = [header, *(_format_product_prices_line(p, lang, req_size) for p in prods)]
        return FastPathResponse(handled=True, answer="\n".join(lines), intent=intent)

    return FastPathResponse(handled=False, answer="", intent=intent)


def _clean_kb_chunk_text(raw_text: str, max_chars: int = 420) -> str:
    """Strip internal `[Header]` tags, replace DB code tokens, and truncate cleanly."""
    cleaned = _BRACKET_HEADER_RE.sub("", raw_text)
    cleaned = _INLINE_SECTION_BRACKET_RE.sub("", cleaned)
    cleaned = re.sub(r"(?m)^###\s+Q:\s*", "**Hỏi:** ", cleaned)
    cleaned = re.sub(r"(?m)^A:\s*", "**Đáp:** ", cleaned)
    for src, dst in _TECH_TOKEN_REPLACEMENTS:
        cleaned = cleaned.replace(src, dst)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    if len(cleaned) <= max_chars:
        return cleaned

    window = cleaned[:max_chars]
    # Cut cleanly at the last complete line or sentence boundary
    cut_pos = max(window.rfind(".\n"), window.rfind(". "), window.rfind("\n"))
    if cut_pos < max_chars // 2:
        cut_pos = window.rfind(" ")
    truncated = (window[: cut_pos + 1] if cut_pos > 0 else window).rstrip(" ,;:-•*")
    # Strip dangling incomplete bullet markers at the end
    truncated = re.sub(r"\n\s*(?:[-•*]|\d+\.)\s*(?:\*\*[^*\n]*)?$", "", truncated).rstrip()

    if truncated.count("**") % 2 == 1:
        last_bold = truncated.rfind("**")
        truncated = truncated[:last_bold].rstrip(" -•:,")
    if truncated.count("`") % 2 == 1:
        last_tick = truncated.rfind("`")
        truncated = truncated[:last_tick].rstrip()

    return f"{truncated}..." if not truncated.endswith(".") else truncated


def _build_single_product_allergen_answer(prod: ProductDetailOut, lang: str) -> str:
    req_ings = [ing for ing in prod.ingredients if not ing.is_optional]
    opt_ings = [ing for ing in prod.ingredients if ing.is_optional]
    req_str = ", ".join(
        f"{ing.name_vi}" + (f" (`{ing.allergen_code}`)" if ing.allergen_code else "")
        for ing in req_ings
    )
    opt_str = ", ".join(
        f"{ing.name_vi}" + (f" (`{ing.allergen_code}`)" if ing.allergen_code else "")
        for ing in opt_ings
    )

    if lang == "en":
        allergen_info = (
            ", ".join(prod.allergens) if prod.allergens else "none of the 4 major allergens"
        )
        dairy_text = "Contains dairy" if prod.has_milk else "Dairy-free"
        price_en = _format_product_prices_line(prod, "en", None).lstrip("- ")
        return (
            f"**{prod.name_en}** ({price_en})\n"
            f"- **Dairy (`DAIRY`):** {dairy_text}.\n"
            f"- **Verified allergens:** {allergen_info}.\n"
            "*Safety note:* Prepared at a shared bar handling dairy, nuts, soy, and gluten."
        )

    lines = [f"Thông tin thành phần & dị ứng của **{prod.name_vi}**:"]
    if prod.allergens:
        labels = ", ".join(_ALLERGEN_NAME_VI.get(a, a) for a in prod.allergens)
        lines.append(f"- **Cảnh báo dị ứng:** Có chứa **{labels}** trong công thức chuẩn.")
    else:
        lines.append(
            "- **An toàn dị ứng:** Không chứa 4 nhóm chất gây dị ứng phổ biến "
            "(Sữa bò, Các loại hạt, Đậu nành, Gluten) trong công thức chuẩn."
        )
    if req_str:
        lines.append(f"- **Thành phần chính:** {req_str}.")
    if opt_str:
        lines.append(f"- **Thành phần tùy chọn (có thể dặn bỏ):** {opt_str}.")
    if prod.has_milk and any(ing.code == "fresh_milk" for ing in prod.ingredients):
        lines.append(
            "- **Tùy chỉnh sữa:** Bạn có thể yêu cầu đổi sữa tươi sang **Sữa Yến Mạch Barista** "
            "hoặc **Sữa Hạnh Nhân** (lưu ý phần kem phủ nếu có vẫn chứa sữa bò)."
        )
    lines.append(
        "*Lưu ý an toàn:* Quầy bar sử dụng chung khu vực pha chế với sữa bò, hạt, đậu nành "
        "và gluten; nếu dị ứng nặng vui lòng báo trực tiếp Barista."
    )
    return "\n".join(lines)


def _build_single_product_consultation(
    prod: ProductDetailOut,
    retrieval: RetrievalResult,
) -> str:
    """
    Build a rich, grounded Barista consultation for a single named menu item
    using verified SQL variants, flavor levels, ingredients, and customization rules.
    """
    lang = retrieval.parsed_query.language
    req_size = retrieval.parsed_query.requested_size
    avail = [v for v in prod.variants if v.is_available]

    if lang == "en":
        price_line = _format_product_prices_line(prod, "en", req_size).lstrip("- ")
        allergen_note = (
            f"Contains {', '.join(prod.allergens)}."
            if prod.allergens
            else "Free of major allergens (Dairy, Nuts, Soy, Gluten)."
        )
        return (
            f"Barista guide for {price_line}\n"
            f"- **Flavor profile:** {prod.short_description_en or prod.short_description_vi} "
            f"(Bitterness `{prod.bitterness_level}/5` · Sweetness `{prod.sweetness_level}/5` · "
            f"Caffeine `{prod.caffeine_level}`).\n"
            "- **Sweetness & Ice:** Adjustable to **100% (standard) / 70% (less sweet) / "
            "50% / 30% / 0%**, with **Regular ice**, **Less ice**, or **Separate ice** for takeaway.\n"
            f"- **Allergen note:** {allergen_note}"
        )

    matched_var = (
        next((v for v in avail if v.size == req_size), None)
        if req_size
        else next((v for v in avail if v.size == "regular"), avail[0] if avail else None)
    )
    all_sizes_str = " · ".join(
        f"{_SIZE_LABEL_VI[v.size]}: {_fmt_vnd(v.price_vnd)}" for v in avail
    )
    if req_size and matched_var:
        kcal_part = f" · {matched_var.calories_kcal} kcal" if matched_var.calories_kcal else ""
        header = (
            f"Tư vấn thưởng thức **{prod.name_vi}** — Size **{_SIZE_LABEL_VI[matched_var.size]}: "
            f"{_fmt_vnd(matched_var.price_vnd)}**{kcal_part} *(Các size: {all_sizes_str})*:"
        )
    else:
        header = f"Tư vấn thưởng thức **{prod.name_vi}** *({all_sizes_str})*:"

    caff_vi = _CAFFEINE_LABEL_VI.get(prod.caffeine_level, prod.caffeine_level)
    ing_codes = {ing.code for ing in prod.ingredients}
    lines: list[str] = [header]

    # 1. Flavor & Serving recommendation
    flavor_desc = prod.short_description_vi.rstrip(".")
    has_cream_top = bool(ing_codes & {"whipping_cream", "salted_foam", "cream_cheese"})
    if prod.category.slug == "pastry":
        pastry_story = (
            prod.story_vi
            or "Bánh ngon nhất khi dùng ngay cùng Espresso, Americano hoặc Cold Brew."
        )
        lines.append(
            f"- **Hương vị & Thưởng thức:** {flavor_desc} (`Độ ngọt {prod.sweetness_level}/5`). "
            f"{pastry_story}"
        )
    else:
        if has_cream_top:
            sip_tip = (
                "Bạn nên **nhấp trực tiếp qua lớp kem mịn ở 2–3 ngụm đầu** để cảm nhận vị béo bùi "
                "hòa quyện nền cà phê/trà, sau đó khuấy nhẹ và thưởng thức ngon nhất trong "
                "**15–20 phút đầu**."
            )
        elif "cold_brew_base" in ing_codes:
            sip_tip = (
                "Khuấy nhẹ cùng đá viên trước khi uống để hương thơm trái cây tự nhiên của hạt "
                "Arabica Cầu Đất ủ lạnh 18 giờ lan tỏa trọn vẹn, êm dịu cho dạ dày."
            )
        else:
            sip_tip = (
                "Thưởng thức ngay khi vừa pha để cảm nhận trọn vẹn lớp hương thơm "
                "và hậu vị êm mượt."
            )

        temp_target = matched_var.temperature if matched_var else "iced"
        if temp_target == "both":
            temp_tip = (
                " Món phục vụ cả **Uống đá** (sảng khoái, vị béo thanh mượt) và **Uống nóng** "
                "(ấm áp, dậy hương hạt rang rõ nét)."
            )
        elif temp_target == "hot":
            temp_tip = " Món phục vụ **Uống nóng** để giữ độ sánh mịn và hương thơm chuẩn nhất."
        else:
            temp_tip = " Món phục vụ **Uống lạnh với đá** để cân bằng độ sánh và vị thanh mát."

        lines.append(
            f"- **Hương vị & Cách thưởng thức:** {flavor_desc} "
            f"(`Độ đắng {prod.bitterness_level}/5` · `Độ ngọt chuẩn {prod.sweetness_level}/5` · "
            f"`{caff_vi}`). {sip_tip}{temp_tip}"
        )

        # 2. Sweetness adjustment advice tailored to recipe
        if "condensed_milk" in ing_codes:
            sweet_tip = (
                "Mức **100% (mặc định)** đậm đà béo ngọt; nếu không hảo ngọt bạn nên chọn **70%** "
                "hoặc **50%** *(lưu ý món dùng sữa đặc nên vẫn giữ vị ngọt dịu tự nhiên, "
                "có thể đổi sang nền sữa tươi hoặc sữa yến mạch nếu muốn ít ngọt hẳn)*."
            )
        elif prod.sweetness_level >= 3:
            sweet_tip = (
                "Mức **100% (chuẩn Barista)** cân bằng êm dịu; nếu muốn tôn rõ vị cà phê/trà và "
                "thanh nhẹ hơn, mức **70% (ít ngọt)** là lựa chọn lý tưởng nhất mà vẫn giữ hương "
                "thơm đặc trưng của nguyên liệu (ngoài ra quán hỗ trợ cả **50% / 30% / 0%**)."
            )
        else:
            sweet_tip = (
                "Công thức chuẩn vốn **ít ngọt / không đường tinh luyện**; bạn có thể giữ nguyên "
                "mức mặc định để thưởng thức vị nguyên bản hoặc dặn Barista thêm chút mật ong/siro."
            )
        lines.append(f"- **Điều chỉnh vị ngọt:** {sweet_tip}")

        # 3. Ice & extra bar customization advice
        extra_parts = [
            "Chọn **Đá bình thường** khi dùng ngay tại quán, **Ít đá** nếu ngồi lâu trong "
            "phòng máy lạnh để không loãng vị, hoặc **Đá riêng** khi mang đi xa"
            + (" nhằm giữ nguyên lớp kem phủ." if has_cream_top else ".")
        ]
        if "fresh_milk" in ing_codes:
            extra_parts.append(
                "Có thể đổi sữa tươi sang **Sữa Yến Mạch Barista** / **Sữa Hạnh Nhân**"
                + (
                    " *(lưu ý lớp kem phủ vẫn chứa sữa bò nếu không dặn bỏ kem)*"
                    if has_cream_top
                    else ""
                )
                + " hoặc tăng/giảm shot Espresso theo gu tỉnh táo."
            )
        elif "arabica_caudat" in ing_codes and "cold_brew_base" not in ing_codes:
            extra_parts.append("Có thể yêu cầu giảm xuống 1 shot hoặc thêm extra shot Espresso.")
        lines.append(f"- **Lượng đá & Tùy chỉnh thêm:** {' '.join(extra_parts)}")

    # 4. Grounded allergen notice
    if prod.allergens:
        allergen_ings = [
            f"{ing.name_vi} (`{ing.allergen_code}`)"
            for ing in prod.ingredients
            if ing.allergen_code and not ing.is_optional
        ]
        detail_str = (
            ", ".join(allergen_ings)
            if allergen_ings
            else ", ".join(_ALLERGEN_NAME_VI.get(a, a) for a in prod.allergens)
        )
        lines.append(f"- **Lưu ý thành phần:** Công thức chuẩn có chứa {detail_str}.")
    else:
        lines.append(
            "- **Lưu ý thành phần:** Không chứa 4 nhóm dị ứng phổ biến "
            "(`DAIRY`, `NUTS`, `SOY`, `GLUTEN`)."
        )

    return "\n".join(lines)


def build_offline_fallback_answer(retrieval: RetrievalResult) -> str:
    """
    Deterministic fallback answer when Ollama Local is offline (Lexical + SQL mode).
    """
    lang = retrieval.parsed_query.language
    parsed = retrieval.parsed_query
    single_product_focus = len(retrieval.products) == 1 and not _is_pairing_or_alternatives_query(
        parsed.ascii_query
    )

    if retrieval.intent == IntentType.ALLERGEN_INGREDIENT:
        if single_product_focus and not parsed.excluded_allergens:
            return _build_single_product_allergen_answer(retrieval.products[0], lang)

        excluded = ", ".join(parsed.excluded_allergens)
        sections: list[str] = []
        if retrieval.products:
            header = (
                f"Các món đã xác minh **không chứa ({excluded})** trong công thức chuẩn:"
                if excluded and lang == "vi"
                else "Các món phù hợp từ dữ liệu thành phần BREW & BEAN:"
            )
            prod_lines = [
                _format_product_prices_line(p, lang, parsed.requested_size)
                for p in retrieval.products[:4]
            ]
            sections.append("\n".join([header, *prod_lines]))
            sections.append(
                "*Lưu ý an toàn:* Quầy bar có sử dụng chung khu vực pha chế với sữa bò, hạt, "
                "đậu nành và gluten; nếu dị ứng nặng vui lòng báo trực tiếp Barista."
            )
            return "\n\n".join(sections)

        return (
            "Hiện chưa tìm thấy món thỏa mãn hoàn toàn điều kiện dị ứng bạn yêu cầu. "
            "Vui lòng kiểm tra trực tiếp cùng Barista tại quầy để được tư vấn an toàn."
        )

    if single_product_focus:
        return _build_single_product_consultation(retrieval.products[0], retrieval)

    sections = []
    if retrieval.products:
        header = (
            "Gợi ý đồ uống phù hợp từ thực đơn BREW & BEAN:"
            if lang == "vi"
            else "Recommended items from BREW & BEAN menu:"
        )
        prod_lines = [
            f"{_format_product_prices_line(p, lang, parsed.requested_size)} "
            f"*(Độ đắng {p.bitterness_level}/5 · Độ ngọt {p.sweetness_level}/5 · "
            f"{_CAFFEINE_LABEL_VI.get(p.caffeine_level, p.caffeine_level)})*"
            if lang == "vi"
            else _format_product_prices_line(p, lang, parsed.requested_size)
            for p in retrieval.products[:4]
        ]
        sections.append("\n".join([header, *prod_lines]))

    if retrieval.chunks:
        seen_titles: set[str] = set()
        snippet_blocks: list[str] = []
        max_chunks = 1 if retrieval.products else 2
        for chunk in retrieval.chunks:
            if chunk.title in seen_titles:
                continue
            cleaned_body = _clean_kb_chunk_text(chunk.content, max_chars=420)
            if not cleaned_body:
                continue
            seen_titles.add(chunk.title)
            snippet_blocks.append(f"**{chunk.title}**\n{cleaned_body}")
            if len(snippet_blocks) >= max_chunks:
                break

        if snippet_blocks:
            ref_header = (
                "Thông tin từ cẩm nang BREW & BEAN:"
                if lang == "vi"
                else "From the BREW & BEAN Guide:"
            )
            sections.append(f"{ref_header}\n\n" + "\n\n".join(snippet_blocks))

    if not sections:
        return (
            "Mình chưa tìm thấy thông tin khớp trong tài liệu hiện tại. "
            "Bạn có thể hỏi về giá đồ uống, cách tùy chỉnh ngọt/đá, thành phần dị ứng, "
            "chi nhánh hoặc khuyến mãi nhé!"
        )

    return "\n\n".join(sections)
