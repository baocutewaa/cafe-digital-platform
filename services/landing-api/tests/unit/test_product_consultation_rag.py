from __future__ import annotations

import uuid

from collections.abc import AsyncGenerator

from app.repositories.chat_repo import _is_safe_fuzzy_cache_hit
from app.schemas.menu import (
    CategorySummaryOut,
    ProductDetailOut,
    ProductIngredientOut,
    ProductVariantOut,
)
from app.services.cache_seed_service import load_answer_cache_seed, resolve_answer_cache_seed_path
from rag.generation.answer_generator import AnswerGenerator, looks_like_leaked_thinking
from rag.generation.fast_path import _clean_kb_chunk_text, build_offline_fallback_answer
from rag.generation.guards import is_corrupted_cached_answer
from rag.generation.intent_router import IntentType, classify_intent
from rag.retrieval import RetrievedChunk
from rag.retrieval.context_builder import RetrievalResult
from rag.retrieval.query_parser import parse_query


def _sample_macadamia_product() -> ProductDetailOut:
    return ProductDetailOut(
        id=uuid.uuid4(),
        slug="macadamia-espresso-cream",
        name_vi="Macadamia Espresso Cream",
        name_en="Macadamia Espresso Cream",
        short_description_vi=(
            "Latte mịn màng với sốt hạt Macca Tây Nguyên béo bùi và lớp kem tươi nhẹ."
        ),
        short_description_en=(
            "Silky espresso latte layered with highland macadamia syrup and light cream."
        ),
        story_vi=(
            "Hạt Macca Đắk Lắk rang thơm được xay nhuyễn làm sốt, giúp cân bằng độ đắng "
            "của espresso thành ly cà phê êm ái như món tráng miệng."
        ),
        image_url="/images/products/macadamia-espresso-cream.webp",
        category=CategorySummaryOut(
            id=uuid.uuid4(),
            slug="signature",
            name_vi="Signature",
            name_en="Signature",
        ),
        taste_tags=["nutty", "creamy", "less_bitter", "sweet"],
        caffeine_level="medium",
        bitterness_level=2,
        sweetness_level=3,
        has_milk=True,
        is_signature=True,
        is_featured=False,
        min_price_vnd=49000,
        max_price_vnd=62000,
        allergens=["DAIRY", "NUTS"],
        variants=[
            ProductVariantOut(
                id=uuid.uuid4(),
                sku="BB-MACA-S",
                size="small",
                temperature="both",
                price_vnd=49000,
                calories_kcal=195,
                is_available=True,
            ),
            ProductVariantOut(
                id=uuid.uuid4(),
                sku="BB-MACA-M",
                size="regular",
                temperature="both",
                price_vnd=55000,
                calories_kcal=240,
                is_available=True,
            ),
            ProductVariantOut(
                id=uuid.uuid4(),
                sku="BB-MACA-L",
                size="large",
                temperature="iced",
                price_vnd=62000,
                calories_kcal=290,
                is_available=True,
            ),
        ],
        ingredients=[
            ProductIngredientOut(
                code="arabica_caudat",
                name_vi="Hạt Arabica Cầu Đất",
                name_en="Cau Dat Arabica",
                allergen_code=None,
                is_optional=False,
            ),
            ProductIngredientOut(
                code="fresh_milk",
                name_vi="Sữa tươi thanh trùng",
                name_en="Pasteurized Fresh Milk",
                allergen_code="DAIRY",
                is_optional=False,
            ),
            ProductIngredientOut(
                code="macadamia_syrup",
                name_vi="Sốt hạt Macca",
                name_en="Macadamia Syrup",
                allergen_code="NUTS",
                is_optional=False,
            ),
            ProductIngredientOut(
                code="whipping_cream",
                name_vi="Kem tươi Whipping Cream",
                name_en="Whipping Cream",
                allergen_code="DAIRY",
                is_optional=False,
            ),
        ],
    )


def test_parse_product_detail_cta_prompt_cleanly() -> None:
    query = (
        "Mình đang xem Macadamia Espresso Cream (Vừa (M), 55.000đ). "
        "Tư vấn giúp mình cách thưởng thức hoặc điều chỉnh vị ngọt/đá phù hợp nhé!"
    )
    parsed = parse_query(query)

    assert parsed.max_price is None
    assert "sweet" not in parsed.taste_tags
    assert parsed.requested_size == "regular"
    assert parsed.is_customization_query is True
    assert "macadamia" in parsed.search_terms
    assert "espresso" in parsed.search_terms
    assert "cream" in parsed.search_terms


def test_parse_budget_and_allergen_vs_inspection_queries() -> None:
    budget_q = parse_query("Mình muốn đồ uống ít đắng, béo nhẹ, dưới 50k uống buổi chiều")
    assert budget_q.max_price == 50000
    assert "less_bitter" in budget_q.taste_tags
    assert "creamy" in budget_q.taste_tags
    assert budget_q.caffeine_level == "low"

    inspect_q = parse_query(
        "Món Macadamia Espresso Cream có chứa sữa bò hay chất gây dị ứng nào không?"
    )
    assert inspect_q.excluded_allergens == []
    assert inspect_q.has_milk is None
    assert classify_intent(inspect_q) == IntentType.ALLERGEN_INGREDIENT

    avoid_q = parse_query("Mình bị dị ứng sữa bò (DAIRY) thì uống món nào được?")
    assert "DAIRY" in avoid_q.excluded_allergens
    assert avoid_q.has_milk is False
    assert classify_intent(avoid_q) == IntentType.ALLERGEN_INGREDIENT


def test_customization_with_size_does_not_fall_into_price_only_lookup() -> None:
    parsed = parse_query("Macadamia Espresso Cream size M giảm ngọt được không?")
    assert parsed.requested_size == "regular"
    assert parsed.is_customization_query is True
    assert classify_intent(parsed) != IntentType.PRODUCT_LOOKUP


def test_fuzzy_cache_guard_blocks_cross_product_and_number_collisions() -> None:
    q_maca = (
        "mình đang xem macadamia espresso cream (vừa (m), 55.000đ). "
        "tư vấn giúp mình cách thưởng thức hoặc điều chỉnh vị ngọt/đá phù hợp nhé"
    )
    q_oat = (
        "mình đang xem latte sữa yến mạch mật ong (vừa (m), 55.000đ). "
        "tư vấn giúp mình cách thưởng thức hoặc điều chỉnh vị ngọt/đá phù hợp nhé"
    )
    q_maca_s = (
        "mình đang xem macadamia espresso cream (nhỏ (s), 49.000đ). "
        "tư vấn giúp mình cách thưởng thức hoặc điều chỉnh vị ngọt/đá phù hợp nhé"
    )
    assert _is_safe_fuzzy_cache_hit(q_oat, q_maca) is False
    assert _is_safe_fuzzy_cache_hit(q_maca_s, q_maca) is False
    assert _is_safe_fuzzy_cache_hit("đồ uống ít đắng dưới 45k", "đồ uống ít đắng dưới 50k") is False
    assert (
        _is_safe_fuzzy_cache_hit(
            "cold brew khác gì espresso pha đá thông thường",
            "cold brew khác gì với espresso pha đá thông thường vậy bạn",
        )
        is True
    )


def test_single_product_offline_consultation_is_focused_and_clean() -> None:
    query = (
        "Mình đang xem Macadamia Espresso Cream (Vừa (M), 55.000đ). "
        "Tư vấn giúp mình cách thưởng thức hoặc điều chỉnh vị ngọt/đá phù hợp nhé!"
    )
    parsed = parse_query(query)
    prod = _sample_macadamia_product()
    chunk = RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        source_key="coffee_guide/07_sweetness_ice_adjustment_guide.md",
        title="Hướng dẫn tùy chỉnh độ ngọt, lượng đá và shot espresso theo khẩu vị",
        category="COFFEE_GUIDE",
        section="Hướng dẫn tùy chỉnh độ ngọt, lượng đá và shot espresso theo khẩu vị",
        content=(
            "[Hướng dẫn tùy chỉnh độ ngọt, lượng đá và shot espresso theo khẩu vị]\n"
            "Mỗi vị khách có một khẩu vị riêng. Gắn nhãn `less_bitter` rõ ràng.\n"
            "- **Bạc Xỉu Cốt Dừa Nướng**"
        ),
    )
    retrieval = RetrievalResult(
        parsed_query=parsed,
        intent=IntentType.PRODUCT_RECOMMENDATION,
        chunks=[chunk],
        products=[prod],
        degraded=True,
    )

    answer = build_offline_fallback_answer(retrieval)
    assert "Macadamia Espresso Cream" in answer
    assert "M (Vừa): 55.000đ" in answer
    assert "240 kcal" in answer
    assert "70%" in answer
    assert "Đá riêng" in answer
    assert "DAIRY" in answer and "NUTS" in answer
    assert "Cà Phê Muối Cầu Đất" not in answer
    assert "[Hướng dẫn" not in answer
    assert "less_bitter" not in answer

    cleaned_chunk = _clean_kb_chunk_text(chunk.content, max_chars=85)
    assert "[Hướng dẫn" not in cleaned_chunk
    assert "less_bitter" not in cleaned_chunk
    assert cleaned_chunk.count("**") % 2 == 0


def test_parse_low_sweetness_with_45k_budget_and_typo() -> None:
    parsed = parse_query("Với 45k tôi có thể uống gì ít ngọtk")

    assert parsed.max_price == 45000
    assert parsed.max_sweetness == 2
    assert parsed.drinks_only is True
    assert parsed.is_customization_query is False
    assert "sweet" not in parsed.taste_tags
    assert "it" not in parsed.search_terms
    assert "45k" not in parsed.search_terms
    assert classify_intent(parsed) == IntentType.PRODUCT_RECOMMENDATION


def test_leaked_thinking_detector_catches_english_monologue() -> None:
    leaked = (
        'Okay, let’s tackle this query. The user is asking, "Với 45k tôi có thể uống gì ít ngọt" '
        'which translates to "With 45k, what can I drink that\'s less sweet?"'
    )
    assert looks_like_leaked_thinking(leaked, "vi") is True
    assert looks_like_leaked_thinking("Hmm, let me check the menu prices first.", "vi") is True
    assert (
        looks_like_leaked_thinking(
            "Với **45.000đ** và gu **ít ngọt**, bạn có thể chọn **Cold Brew Sữa Tươi** (42.000đ).",
            "vi",
        )
        is False
    )


async def test_stream_answer_auto_promotes_when_think_false_leaks_reasoning() -> None:
    class _StubThinkingClient:
        base_url = "http://127.0.0.1:11434"
        is_circuit_open = False

        def __init__(self) -> None:
            self.mode = "disable"
            self.calls = 0

        def can_promote_think_mode(self) -> bool:
            return self.mode != "separate"

        def promote_to_separate_thinking(self) -> None:
            self.mode = "separate"

        async def stream_chat(
            self, _messages: list[dict[str, str]]
        ) -> AsyncGenerator[str, None]:
            self.calls += 1
            if self.mode != "separate":
                for tok in ("Okay, ", "let's tackle ", "this query. ", "First, I need..."):
                    yield tok
                return
            for tok in (
                "Với ngân sách **45.000đ** và gu **ít ngọt**, ",
                "bạn nên thử **Macadamia Espresso Cream** chỉnh mức **50% ngọt**.",
            ):
                yield tok

    parsed = parse_query("Với 45k tôi có thể uống gì ít ngọtk")
    retrieval = RetrievalResult(
        parsed_query=parsed,
        intent=IntentType.PRODUCT_RECOMMENDATION,
        products=[_sample_macadamia_product()],
        degraded=False,
    )

    stub = _StubThinkingClient()
    gen = AnswerGenerator(ai_client=stub)  # type: ignore[arg-type]
    emitted: list[str] = []
    final_degraded: bool | None = None

    async for delta, metrics in gen.stream_answer(retrieval):
        if delta:
            emitted.append(delta)
        if metrics is not None:
            final_degraded = metrics.degraded

    full_reply = "".join(emitted)
    assert stub.calls == 2
    assert stub.mode == "separate"
    assert final_degraded is False
    assert "Okay, let's tackle" not in full_reply
    assert "45.000đ" in full_reply


async def test_stream_answer_strips_untagged_thinking_before_close_tag() -> None:
    class _UntaggedCloseThinkClient:
        base_url = "http://127.0.0.1:11434"
        is_circuit_open = False

        def can_promote_think_mode(self) -> bool:
            return False

        def promote_to_separate_thinking(self) -> None:
            pass

        async def stream_chat(
            self, _messages: list[dict[str, str]]
        ) -> AsyncGenerator[str, None]:
            yield "Okay, let's tackle this query and check SQL VERIFIED MENU DATA.\n"
            yield "Still thinking about items...</think>\n"
            yield (
                "Gợi ý chuẩn gu **ít ngọt** dưới **49.000đ**: "
                "**Macadamia Espresso Cream** (size S: 49.000đ)."
            )

    parsed = parse_query("Gợi ý đồ uống dưới 50k")
    retrieval = RetrievalResult(
        parsed_query=parsed,
        intent=IntentType.PRODUCT_RECOMMENDATION,
        products=[_sample_macadamia_product()],
        degraded=False,
    )

    gen = AnswerGenerator(ai_client=_UntaggedCloseThinkClient())  # type: ignore[arg-type]
    emitted = [delta async for delta, _ in gen.stream_answer(retrieval) if delta]
    full_reply = "".join(emitted)

    assert "Okay, let's tackle" not in full_reply
    assert "SQL VERIFIED MENU DATA" not in full_reply
    assert "Macadamia Espresso Cream" in full_reply


def test_corrupted_cache_guard_catches_poisoned_signature_cache_and_allows_clean_seed() -> None:
    poisoned_signature = (
        "Okay, let's tackle this query. The user wants me to suggest 2-3 signature drinks "
        "from BREW & BEAN that are easy to drink. I need to check the SQL data and the "
        "knowledge base to make sure I don't add any info that's not there.\n"
        "First, looking at the SQL VERIFIED MENU DATA.\n"
        "3.Macadamia Espresso Cream: Caffeine=medium, độ đắng=2/5, độ ngọt=3/5, has dairy and"
    )
    assert is_corrupted_cached_answer(poisoned_signature, "vi") is True
    assert is_corrupted_cached_answer("1. Cà Phê Muối Cầu Đất (", "vi") is True
    assert is_corrupted_cached_answer("<think>reasoning</think>Trả lời", "vi") is True

    seed_path = resolve_answer_cache_seed_path()
    assert seed_path is not None
    seed_items = load_answer_cache_seed(seed_path)
    assert len(seed_items) >= 25
    for item in seed_items:
        assert is_corrupted_cached_answer(item.answer, item.language) is False


