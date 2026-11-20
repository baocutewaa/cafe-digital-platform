from __future__ import annotations

from dataclasses import dataclass

from app.schemas.menu import ProductDetailOut
from rag.generation.intent_router import IntentType
from rag.retrieval.context_builder import RetrievalResult

_SIZE_LABEL_VI = {"small": "S (Nhỏ)", "regular": "M (Vừa)", "large": "L (Lớn)"}
_SIZE_LABEL_EN = {"small": "Small (S)", "regular": "Regular (M)", "large": "Large (L)"}

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


def build_offline_fallback_answer(retrieval: RetrievalResult) -> str:
    """
    Deterministic fallback answer when Ollama Local is offline (Lexical + SQL mode).
    """
    lang = retrieval.parsed_query.language
    sections: list[str] = []

    if retrieval.intent == IntentType.ALLERGEN_INGREDIENT:
        excluded = ", ".join(retrieval.parsed_query.excluded_allergens)
        if retrieval.products:
            header = (
                f"Các món đã xác minh **không chứa ({excluded})** trong công thức chuẩn:"
                if excluded and lang == "vi"
                else "Các món phù hợp từ dữ liệu thành phần BREW & BEAN:"
            )
            prod_lines = [
                _format_product_prices_line(p, lang, retrieval.parsed_query.requested_size)
                for p in retrieval.products
            ]
            sections.append("\n".join([header, *prod_lines]))
            sections.append(
                "*Lưu ý an toàn:* Quầy bar có sử dụng chung khu vực pha chế với sữa bò, hạt, "
                "đậu nành và gluten; nếu dị ứng nặng vui lòng báo trực tiếp Barista."
            )
        else:
            sections.append(
                "Hiện chưa tìm thấy món thỏa mãn hoàn toàn điều kiện dị ứng bạn yêu cầu. "
                "Vui lòng kiểm tra trực tiếp cùng Barista tại quầy để được tư vấn an toàn."
            )
    elif retrieval.products:
        header = (
            "Gợi ý đồ uống phù hợp từ thực đơn BREW & BEAN (chế độ Tra cứu nhanh):"
            if lang == "vi"
            else "Matching drinks from BREW & BEAN menu (Fast Lookup mode):"
        )
        prod_lines = [
            _format_product_prices_line(p, lang, retrieval.parsed_query.requested_size)
            for p in retrieval.products
        ]
        sections.append("\n".join([header, *prod_lines]))

    if retrieval.chunks:
        snippet_lines = [
            "Thông tin tham khảo từ cẩm nang BREW & BEAN:"
            if lang == "vi"
            else "Reference from BREW & BEAN Knowledge Base:"
        ]
        for chunk in retrieval.chunks[:2]:
            clean = chunk.content.strip()
            suffix = "..." if len(clean) > 380 else ""
            snippet_lines.append(f"- **{chunk.title}:** {clean[:380]}{suffix}")
        sections.append("\n".join(snippet_lines))

    if not sections:
        return (
            "Mình chưa tìm thấy thông tin khớp trong tài liệu hiện tại (chế độ Tra cứu nhanh). "
            "Bạn có thể hỏi về giá đồ uống, thành phần dị ứng, chi nhánh hoặc khuyến mãi."
        )

    return "\n\n".join(sections)
