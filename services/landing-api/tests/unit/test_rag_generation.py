from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from app.core.exceptions import RateLimitExceededError
from app.integrations.ollama_client import OllamaClient
from app.schemas.menu import (
    CategorySummaryOut,
    ProductDetailOut,
    ProductIngredientOut,
    ProductVariantOut,
)
from app.services.cache_seed_service import (
    load_answer_cache_seed,
    resolve_answer_cache_seed_path,
    seed_answer_cache_from_file,
)
from app.services.rate_limit import SlidingWindowRateLimiter
from rag.generation.answer_generator import (
    AnswerGenerator,
    extract_mentioned_prices_vnd,
    looks_like_leaked_thinking,
    post_check_answer,
    strip_think_tags,
)
from rag.generation.intent_router import IntentType
from rag.generation.prompts.system_prompts import build_rag_messages
from rag.retrieval.context_builder import RetrievalResult
from rag.retrieval.query_parser import parse_query


def _sample_product() -> ProductDetailOut:
    return ProductDetailOut(
        id=uuid.uuid4(),
        slug="oat-milk-honey-latte",
        name_vi="Latte Sữa Yến Mạch Mật Ong",
        name_en="Oat Milk Honey Latte",
        short_description_vi="Không sữa bò.",
        image_url="/images/products/oat-milk-honey-latte.webp",
        category=CategorySummaryOut(
            id=uuid.uuid4(),
            slug="signature",
            name_vi="Món Đặc Trưng",
            name_en="Signature",
        ),
        taste_tags=["sweet", "dairy_free"],
        caffeine_level="medium",
        bitterness_level=2,
        sweetness_level=3,
        has_milk=False,
        is_signature=True,
        is_featured=False,
        min_price_vnd=49000,
        max_price_vnd=62000,
        allergens=[],
        variants=[
            ProductVariantOut(
                id=uuid.uuid4(),
                sku="BB-OATH-S",
                size="small",
                temperature="both",
                price_vnd=49000,
                calories_kcal=135,
                is_available=True,
            ),
            ProductVariantOut(
                id=uuid.uuid4(),
                sku="BB-OATH-M",
                size="regular",
                temperature="both",
                price_vnd=55000,
                calories_kcal=170,
                is_available=True,
            ),
        ],
        story_vi="Câu chuyện",
        ingredients=[
            ProductIngredientOut(
                code="oat_milk",
                name_vi="Sữa yến mạch",
                name_en="Oat Milk",
                allergen_code=None,
                is_optional=False,
            )
        ],
    )


def test_strip_think_tags_and_price_extraction() -> None:
    raw = "<think>suy nghĩ nội bộ</think>Giá Caramel Latte là 49.000đ hoặc size lớn 55k."
    assert strip_think_tags(raw) == "Giá Caramel Latte là 49.000đ hoặc size lớn 55k."
    assert extract_mentioned_prices_vnd(raw) == {49000, 55000}

    # Pre-opened <think> in template (only closing </think> in output) and unclosed trailing <think>
    assert strip_think_tags("internal reasoning...</think>\nCà phê ngon.") == "Cà phê ngon."
    assert strip_think_tags("Giá 45.000đ.<thought>internal</thought>") == "Giá 45.000đ."
    assert strip_think_tags("Okay, let's think<think>unfinished") == "Okay, let's think"
    assert looks_like_leaked_thinking("Okay, let's tackle this query.", "vi") is True
    assert looks_like_leaked_thinking("Cà Phê Đen Đá có vị đắng đậm.", "vi") is False


async def test_stream_answer_filters_think_blocks_and_recovers_from_leaked_thinking() -> None:
    class _FakeThinkTagClient:
        base_url = "http://fake"
        is_circuit_open = False

        async def stream_chat(self, _messages: list[dict[str, str]]):
            tokens = [
                "<thi",
                "nk>secret ",
                "reasoning</th",
                "ink>\nChào ",
                "bạn, món này rất đậm.",
            ]
            for tok in tokens:
                yield tok

    parsed = parse_query("Cà Phê Đen Đá Buôn Ma Thuột vị thế nào?")
    retrieval = RetrievalResult(
        parsed_query=parsed,
        intent=IntentType.PRODUCT_RECOMMENDATION,
        products=[_sample_product()],
    )
    gen = AnswerGenerator(ai_client=_FakeThinkTagClient())  # type: ignore[arg-type]
    chunks: list[str] = []
    final_metrics = None
    async for delta, metrics in gen.stream_answer(retrieval):
        if delta:
            chunks.append(delta)
        if metrics is not None:
            final_metrics = metrics

    combined = "".join(chunks)
    assert "secret" not in combined
    assert "<think>" not in combined
    assert combined == "Chào bạn, món này rất đậm."
    assert final_metrics is not None
    assert final_metrics.degraded is False

    class _FakeLeakedClient:
        base_url = "http://fake"
        is_circuit_open = False

        async def stream_chat(self, _messages: list[dict[str, str]]):
            tokens = [
                "Okay, ",
                "let's tackle ",
                "this query. Looking at SQL VERIFIED MENU DATA...",
            ]
            for tok in tokens:
                yield tok

    gen_leaked = AnswerGenerator(ai_client=_FakeLeakedClient())  # type: ignore[arg-type]
    leaked_chunks: list[str] = []
    leaked_metrics = None
    async for delta, metrics in gen_leaked.stream_answer(retrieval):
        if delta:
            leaked_chunks.append(delta)
        if metrics is not None:
            leaked_metrics = metrics

    leaked_text = "".join(leaked_chunks)
    assert "Okay, let's" not in leaked_text
    assert "Latte Sữa Yến Mạch Mật Ong" in leaked_text
    assert leaked_metrics is not None
    assert leaked_metrics.degraded is True


async def test_ollama_client_think_payload_modes() -> None:
    client = OllamaClient()
    client._model_think_modes["qwen2.5:3b"] = "none"
    client._model_think_modes["qwen3:4b"] = "separate"
    client._model_think_modes["qwen3:hybrid"] = "disable"

    p_none = client._build_chat_payload([], stream=True, think_mode="none")
    assert "think" not in p_none

    p_sep = client._build_chat_payload([], stream=False, think_mode="separate")
    assert p_sep["think"] is True
    assert p_sep["options"]["num_predict"] >= 1024

    p_dis = client._build_chat_payload([], stream=False, think_mode="disable")
    assert p_dis["think"] is False


def test_post_check_guards_hallucinated_price_and_unsafe_allergen() -> None:
    parsed = parse_query("Mình bị dị ứng sữa bò, gợi ý món không sữa")
    retrieval = RetrievalResult(
        parsed_query=parsed,
        intent=IntentType.ALLERGEN_INGREDIENT,
        products=[_sample_product()],
    )
    hallucinated = "Bạn hãy thử Bạc Xỉu Cốt Dừa Nướng giá 99.000đ nhé!"
    checked = post_check_answer(
        hallucinated,
        retrieval,
        unsafe_product_names=["Bạc Xỉu Cốt Dừa Nướng"],
    )
    assert "Lưu ý giá niêm yết chính xác" in checked
    assert "49.000đ" in checked
    assert "Cảnh báo kiểm tra dị ứng (DAIRY)" in checked


def test_build_rag_messages_includes_history() -> None:
    msgs = build_rag_messages(
        user_query="Món đó giá bao nhiêu?",
        formatted_context="[SQL VERIFIED MENU DATA]\n- Latte: 49.000đ",
        intent=IntentType.PRODUCT_RECOMMENDATION,
        language="vi",
        history=[
            {"role": "user", "content": "Gợi ý món ít đắng"},
            {"role": "assistant", "content": "Bạn có thể thử Caramel Latte."},
        ],
    )
    assert msgs[0]["role"] == "system"
    assert msgs[1]["content"] == "Gợi ý món ít đắng"
    assert msgs[2]["content"] == "Bạn có thể thử Caramel Latte."
    assert msgs[3]["role"] == "user"
    assert "Món đó giá bao nhiêu?" in msgs[3]["content"]


def test_sliding_window_rate_limiter_enforces_session_limit() -> None:
    limiter = SlidingWindowRateLimiter(session_limit=3, ip_limit=10, window_seconds=60.0)
    limiter.check_and_record("sess-1", "127.0.0.1")
    limiter.check_and_record("sess-1", "127.0.0.1")
    limiter.check_and_record("sess-1", "127.0.0.1")
    with pytest.raises(RateLimitExceededError):
        limiter.check_and_record("sess-1", "127.0.0.1")


def test_load_answer_cache_seed_and_resolve(tmp_path: Path) -> None:
    seed_file = tmp_path / "answer_cache.json"
    seed_file.write_text(
        json.dumps(
            [
                {
                    "normalized_query": "cold brew khac gi espresso",
                    "language": "vi",
                    "intent": "COFFEE_KNOWLEDGE",
                    "answer": "Cold Brew ủ lạnh 18 giờ, êm mượt và ít axit hơn Espresso.",
                    "product_slugs": ["cold-brew-truyen-thong"],
                    "citations": [],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    resolved = resolve_answer_cache_seed_path(seed_file)
    assert resolved == seed_file
    items = load_answer_cache_seed(seed_file)
    assert len(items) == 1
    assert items[0].intent == "COFFEE_KNOWLEDGE"
    assert items[0].product_slugs == ["cold-brew-truyen-thong"]


async def test_seed_answer_cache_from_file_handles_empty_seed(tmp_path: Path) -> None:
    empty_file = tmp_path / "empty.json"
    empty_file.write_text("[]", encoding="utf-8")

    class _DummySession:
        pass

    stats = await seed_answer_cache_from_file(_DummySession(), seed_path=empty_file)  # type: ignore[arg-type]
    assert stats == {"total": 0, "seeded": 0, "skipped": 0}


async def test_seed_answer_cache_from_file_skips_existing_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_file = tmp_path / "seed.json"
    seed_file.write_text(
        json.dumps(
            [
                {
                    "normalized_query": "q1",
                    "language": "vi",
                    "intent": "COFFEE_KNOWLEDGE",
                    "answer": "ans1",
                },
                {
                    "normalized_query": "q2",
                    "language": "vi",
                    "intent": "PRODUCT_RECOMMENDATION",
                    "answer": "ans2",
                    "product_slugs": ["bac-xiu-cot-dua-nuong"],
                },
            ]
        ),
        encoding="utf-8",
    )

    upserted: list[str] = []

    class _FakeRepo:
        def __init__(self, _session: object) -> None:
            pass

        async def purge_corrupted_answer_cache(self) -> int:
            return 0

        async def get_current_knowledge_version(self) -> int:
            return 2

        async def get_active_answer_cache_keys(self, _kv: int) -> set[tuple[str, str, str]]:
            return {("q1", "vi", "COFFEE_KNOWLEDGE")}

        async def upsert_answer_cache(self, **kwargs: object) -> None:
            upserted.append(str(kwargs["normalized_query"]))

    class _FakeSession:
        def __init__(self) -> None:
            self.committed = False

        async def commit(self) -> None:
            self.committed = True

    monkeypatch.setattr("app.services.cache_seed_service.ChatRepository", _FakeRepo)
    fake_session = _FakeSession()
    stats = await seed_answer_cache_from_file(fake_session, seed_path=seed_file)  # type: ignore[arg-type]
    assert stats == {"total": 2, "seeded": 1, "skipped": 1, "purged": 0}
    assert upserted == ["q2"]
    assert fake_session.committed is True


def test_repo_answer_cache_seed_json_has_44_valid_entries() -> None:
    seed_path = resolve_answer_cache_seed_path()
    assert seed_path is not None
    items = load_answer_cache_seed(seed_path)
    assert len(items) == 44
    assert all(item.answer.strip() for item in items)
