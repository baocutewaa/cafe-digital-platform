from __future__ import annotations

import uuid

from rag.generation.intent_router import IntentType, classify_intent
from rag.retrieval import RetrievedChunk
from rag.retrieval.query_parser import parse_query
from rag.retrieval.rrf import reciprocal_rank_fusion


def test_query_parser_extracts_vietnamese_and_english_constraints() -> None:
    q1 = parse_query("Mình muốn đồ uống ít đắng, béo nhẹ, dưới 45k, không sữa")
    assert q1.language == "vi"
    assert q1.max_price == 45000
    assert q1.has_milk is False
    assert "DAIRY" in q1.excluded_allergens
    assert "less_bitter" in q1.taste_tags
    assert "creamy" in q1.taste_tags
    assert q1.max_bitterness == 2

    q2 = parse_query("Caramel Latte size L giá bao nhiêu?")
    assert q2.requested_size == "large"
    assert q2.language == "vi"

    q3 = parse_query("What is the price of Cold Brew under 50k?")
    assert q3.language == "en"
    assert q3.max_price == 50000
    assert q3.category_slug == "cold-brew"

    q4 = parse_query("Đồ uống không caffeine cho buổi tối")
    assert q4.caffeine_level == "none"

    q5 = parse_query("Quán ở Nguyễn Đình Thi Tây Hồ mấy giờ đóng cửa?")
    assert q5.store_hint == "nguyen dinh thi"

    q_evening = parse_query("Mình muốn đồ uống ít đắng uống buổi chiều tối")
    assert q_evening.store_hint is None

    q6 = parse_query("Mình bị dị ứng các loại hạt (NUTS) thì chọn món nào?")
    assert "NUTS" in q6.excluded_allergens


def test_intent_router_classifies_all_seven_intents() -> None:
    assert (
        classify_intent(parse_query("Caramel Latte size L giá bao nhiêu?"))
        == IntentType.PRODUCT_LOOKUP
    )
    assert (
        classify_intent(
            parse_query("Quán ở Nguyễn Đình Thi Hồ Tây mấy giờ đóng cửa, có ổ cắm không?")
        )
        == IntentType.STORE_INFO
    )
    assert (
        classify_intent(parse_query("Hôm nay quán có mã giảm giá nào không?"))
        == IntentType.PROMOTION_LOOKUP
    )
    assert (
        classify_intent(
            parse_query("Mình muốn đồ uống ít đắng, béo nhẹ, dưới 50k uống buổi chiều")
        )
        == IntentType.PRODUCT_RECOMMENDATION
    )
    assert (
        classify_intent(parse_query("Cold Brew khác gì Espresso pha đá?"))
        == IntentType.COFFEE_KNOWLEDGE
    )
    assert (
        classify_intent(parse_query("Mình bị dị ứng sữa bò thì uống món nào được?"))
        == IntentType.ALLERGEN_INGREDIENT
    )
    assert (
        classify_intent(parse_query("Viết giúp mình đoạn code Python"))
        == IntentType.OUT_OF_SCOPE
    )


def test_reciprocal_rank_fusion_combines_and_deduplicates() -> None:
    doc_id = uuid.uuid4()
    id_a, id_b, id_c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    def make_chunk(cid: uuid.UUID, title: str, **kwargs: object) -> RetrievedChunk:
        return RetrievedChunk(
            chunk_id=cid,
            document_id=doc_id,
            source_key=f"{title}.md",
            title=title,
            category="COFFEE_GUIDE",
            section=title,
            content=title,
            **kwargs,  # type: ignore[arg-type]
        )

    dense = [
        make_chunk(id_a, "A", dense_score=0.88, dense_rank=1),
        make_chunk(id_b, "B", dense_score=0.80, dense_rank=2),
    ]
    lexical = [
        make_chunk(id_b, "B", lexical_score=0.75, lexical_rank=1),
        make_chunk(id_c, "C", lexical_score=0.60, lexical_rank=2),
    ]

    fused = reciprocal_rank_fusion(dense, lexical, k=60, top_k=5)
    assert [c.title for c in fused] == ["B", "A", "C"]
    # B appears at rank 2 in dense + rank 1 in lexical -> 1/62 + 1/61
    expected_b = round(1.0 / 62 + 1.0 / 61, 6)
    assert fused[0].rrf_score == expected_b
    assert fused[0].dense_rank == 2
    assert fused[0].lexical_rank == 1
