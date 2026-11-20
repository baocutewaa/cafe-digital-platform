from __future__ import annotations

import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, engine
from rag.generation.fast_path import build_offline_fallback_answer, try_build_fast_path
from rag.generation.intent_router import IntentType
from rag.retrieval.context_builder import HybridRetriever


async def _run_retrieve(session: AsyncSession, query: str, offline: bool = False):
    retriever = HybridRetriever(session)
    return await retriever.retrieve(query, offline_fallback=offline)


async def test_sql_fast_path_queries_accurate_and_under_800ms() -> None:
    await engine.dispose()
    async with AsyncSessionLocal() as session:
        # 1. Exact product price by size (offline_fallback=True simulates Ollama off)
        t0 = time.perf_counter()
        res_price = await _run_retrieve(
            session, "Caramel Latte size L giá bao nhiêu?", offline=True
        )
        fp_price = try_build_fast_path(res_price)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert res_price.intent == IntentType.PRODUCT_LOOKUP
        assert fp_price.handled is True
        assert "55.000đ" in fp_price.answer
        assert elapsed_ms < 800.0, f"Fast-path price took {elapsed_ms:.1f}ms"

        # 2. Store hours & address
        t1 = time.perf_counter()
        res_store = await _run_retrieve(
            session, "Quán ở Quận 1 mấy giờ đóng cửa, có ổ cắm không?", offline=True
        )
        fp_store = try_build_fast_path(res_store)
        assert res_store.intent == IntentType.STORE_INFO
        assert fp_store.handled is True
        assert "Nguyễn Huệ" in fp_store.answer
        assert (time.perf_counter() - t1) * 1000.0 < 800.0

        # 3. Active promotions
        res_promo = await _run_retrieve(
            session, "Hôm nay quán có mã giảm giá nào không?", offline=True
        )
        fp_promo = try_build_fast_path(res_promo)
        assert res_promo.intent == IntentType.PROMOTION_LOOKUP
        assert fp_promo.handled is True
        assert "MORNING20" in fp_promo.answer
        assert "COLDBREW10K" in fp_promo.answer

        # 4. Out of scope
        res_oos = await _run_retrieve(session, "Viết giúp mình đoạn code Python", offline=True)
        fp_oos = try_build_fast_path(res_oos)
        assert res_oos.intent == IntentType.OUT_OF_SCOPE
        assert fp_oos.handled is True
        assert "Bean AI" in fp_oos.answer
    await engine.dispose()


async def test_allergen_and_multifilter_sql_safety() -> None:
    await engine.dispose()
    async with AsyncSessionLocal() as session:
        # Dairy allergy -> must NEVER include has_milk=True or DAIRY allergen
        res_dairy = await _run_retrieve(
            session, "Mình bị dị ứng sữa bò thì uống món nào được?", offline=True
        )
        assert res_dairy.intent == IntentType.ALLERGEN_INGREDIENT
        assert len(res_dairy.products) >= 3
        for prod in res_dairy.products:
            assert prod.has_milk is False
            assert "DAIRY" not in prod.allergens

        # Nuts allergy -> must NEVER include NUTS allergen
        res_nuts = await _run_retrieve(
            session, "Mình bị dị ứng các loại hạt (NUTS) thì chọn món nào?", offline=True
        )
        assert res_nuts.intent == IntentType.ALLERGEN_INGREDIENT
        assert len(res_nuts.products) >= 3
        for prod in res_nuts.products:
            assert "NUTS" not in prod.allergens

        # Compound taste + dairy-free + budget filter
        res_rec = await _run_retrieve(
            session, "Gợi ý đồ uống ít đắng, không sữa bò dưới 45k", offline=True
        )
        assert res_rec.intent == IntentType.PRODUCT_RECOMMENDATION
        assert len(res_rec.products) >= 2
        for prod in res_rec.products:
            assert prod.has_milk is False
            assert prod.bitterness_level <= 2
            assert prod.min_price_vnd <= 45000
    await engine.dispose()


async def test_offline_lexical_fallback_works_without_ollama() -> None:
    await engine.dispose()
    async with AsyncSessionLocal() as session:
        res = await _run_retrieve(
            session, "Cold Brew khác gì Espresso pha đá thông thường?", offline=True
        )
        assert res.intent == IntentType.COFFEE_KNOWLEDGE
        assert res.degraded is True
        assert len(res.chunks) >= 1
        assert any(
            c.source_key == "coffee_guide/02_cold_brew_vs_iced_espresso.md"
            for c in res.chunks
        )
        fallback_text = build_offline_fallback_answer(res)
        assert "Cold Brew" in fallback_text
    await engine.dispose()


async def test_hybrid_retrieval_recall_at_5_meets_slo() -> None:
    benchmark = [
        (
            "Cold Brew ủ lạnh 18 giờ khác gì với Espresso pha đá?",
            "coffee_guide/02_cold_brew_vs_iced_espresso.md",
        ),
        (
            "So sánh hạt Arabica Cầu Đất và Robusta Buôn Ma Thuột",
            "coffee_guide/01_arabica_cau_dat_vs_robusta_bmt.md",
        ),
        (
            "Vì sao BREW & BEAN chọn rang vừa Medium Roast?",
            "coffee_guide/03_roasting_profiles_and_flavor.md",
        ),
        (
            "Buổi tối muộn nên uống món gì không mất ngủ?",
            "faq/03_caffeine_and_health_faq.md",
        ),
        (
            "Mình bị dị ứng sữa bò thì uống món nào được?",
            "faq/02_allergens_and_dietary_faq.md",
        ),
        (
            "Quy định không gian làm việc, giữ chỗ và đón thú cưng của quán",
            "policies/03_wifi_workspace_and_pet_policy.md",
        ),
        (
            "Hướng dẫn tùy chỉnh độ ngọt 70% và lượng đá khi gọi món",
            "coffee_guide/07_sweetness_ice_adjustment_guide.md",
        ),
        (
            "Mình không quen uống đắng, thích vị béo nhẹ chọn món nào?",
            "faq/01_menu_taste_and_customization_faq.md",
        ),
        (
            "Quán có pha lại miễn phí nếu đồ uống không hợp khẩu vị không?",
            "policies/02_quality_guarantee_and_remake.md",
        ),
        (
            "Chính sách nhiễm chéo dị ứng thực phẩm tại quầy bar",
            "policies/01_allergen_safety_and_cross_contact.md",
        ),
        (
            "Mang bình cá nhân và xin bã cà phê tại quán như thế nào?",
            "policies/04_sustainability_and_packaging.md",
        ),
        (
            "Cà Phê Muối Cầu Đất và Cold Brew Cam Sả có hương vị ra sao?",
            "menu/01_signature_drinks_guide.md",
        ),
        (
            "Bánh Croissant và Tiramisu nên ghép cặp với đồ uống nào?",
            "menu/06_artisan_pastry_pairings.md",
        ),
        (
            "Sữa yến mạch, sữa hạnh nhân và sữa đậu nành khác nhau thế nào?",
            "coffee_guide/06_milk_and_plant_milk_pairings.md",
        ),
        (
            "Câu chuyện thương hiệu BREW & BEAN và giá trị cốt lõi",
            "brand/01_brew_and_bean_story.md",
        ),
        (
            "ca phe u lanh 18h co bi con cao da day khong",
            "faq/03_caffeine_and_health_faq.md",
        ),
    ]

    await engine.dispose()
    hits = 0
    async with AsyncSessionLocal() as session:
        retriever = HybridRetriever(session)
        for query, expected_source in benchmark:
            res = await retriever.retrieve(query, top_k=5, offline_fallback=False)
            retrieved_sources = [c.source_key for c in res.chunks[:5]]
            if expected_source in retrieved_sources:
                hits += 1
    await engine.dispose()

    recall_at_5 = hits / len(benchmark)
    assert recall_at_5 >= 0.85, (
        f"Hybrid Recall@5 = {recall_at_5:.2f} ({hits}/{len(benchmark)}) < 0.85"
    )
