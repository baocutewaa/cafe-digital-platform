from __future__ import annotations

import json
import uuid

from httpx import AsyncClient

from app.integrations.ollama_client import ollama_client
from app.services.rate_limit import chat_rate_limiter


def _parse_sse_events(raw_body: str) -> list[tuple[str, object]]:
    events: list[tuple[str, object]] = []
    for block in raw_body.strip().split("\n\n"):
        if not block.strip():
            continue
        ev_name = "message"
        data_lines: list[str] = []
        for line in block.splitlines():
            if line.startswith("event:"):
                ev_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].strip())
        if data_lines:
            events.append((ev_name, json.loads("\n".join(data_lines))))
    return events


async def test_chat_session_fast_path_idempotency_and_feedback(
    async_client: AsyncClient,
) -> None:
    chat_rate_limiter.reset()

    # 1. Create session
    sess_resp = await async_client.post("/api/v1/chat/sessions", json={"language": "vi"})
    assert sess_resp.status_code == 201
    sess = sess_resp.json()
    session_id = sess["session_id"]
    token = sess["session_token"]

    # Unauthorized without valid token
    bad_resp = await async_client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "Xin chào"},
        headers={"X-Session-Token": "wrong-token"},
    )
    assert bad_resp.status_code == 401

    # 2. SQL Fast-path message via SSE
    client_msg_id = str(uuid.uuid4())
    msg_resp = await async_client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={
            "content": "Caramel Latte size L giá bao nhiêu?",
            "client_message_id": client_msg_id,
        },
        headers={"X-Session-Token": token},
    )
    assert msg_resp.status_code == 200
    events = _parse_sse_events(msg_resp.text)
    event_names = [name for name, _ in events]
    assert "meta" in event_names
    assert "products" in event_names
    assert "token" in event_names
    assert "done" in event_names
    # Product cards MUST be emitted before streaming text
    assert event_names.index("products") < event_names.index("token")

    full_text = "".join(
        str(data.get("delta", ""))
        for name, data in events
        if name == "token" and isinstance(data, dict)
    )
    assert "55.000đ" in full_text

    done_payload = next(data for name, data in events if name == "done")
    assert isinstance(done_payload, dict)
    assistant_msg_id = str(done_payload["message_id"])

    # 3. Idempotent replay with same client_message_id
    replay_resp = await async_client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={
            "content": "Caramel Latte size L giá bao nhiêu?",
            "client_message_id": client_msg_id,
        },
        headers={"X-Session-Token": token},
    )
    assert replay_resp.status_code == 200
    replay_events = _parse_sse_events(replay_resp.text)
    meta_payload = next(data for name, data in replay_events if name == "meta")
    assert isinstance(meta_payload, dict)
    assert meta_payload.get("replayed") is True

    # 4. Feedback submission (1 then -1)
    fb_resp = await async_client.post(
        f"/api/v1/chat/messages/{assistant_msg_id}/feedback",
        json={"rating": 1, "comment": "Rất chính xác"},
        headers={"X-Session-Token": token},
    )
    assert fb_resp.status_code == 200
    assert fb_resp.json()["rating"] == 1


async def test_chat_rag_streaming_cache_hit_and_offline_fallback(
    async_client: AsyncClient,
) -> None:
    chat_rate_limiter.reset()
    sess_resp = await async_client.post("/api/v1/chat/sessions", json={"language": "vi"})
    sess = sess_resp.json()
    session_id = sess["session_id"]
    token = sess["session_token"]

    # 1. Live RAG + qwen3:4b streaming (or cache hit if prewarmed)
    q = "Cold Brew khác gì Espresso pha đá thông thường?"
    resp1 = await async_client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": q},
        headers={"X-Session-Token": token},
    )
    assert resp1.status_code == 200
    events1 = _parse_sse_events(resp1.text)
    assert any(name == "sources" for name, _ in events1)
    done1 = next(data for name, data in events1 if name == "done")
    assert isinstance(done1, dict)
    assert done1["degraded"] is False

    # 2. Second identical query hits answer_cache
    resp2 = await async_client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": q},
        headers={"X-Session-Token": token},
    )
    assert resp2.status_code == 200
    events2 = _parse_sse_events(resp2.text)
    done2 = next(data for name, data in events2 if name == "done")
    assert isinstance(done2, dict)
    assert done2["cached"] is True

    # 3. Simulated offline Ollama (open circuit breaker) -> graceful degraded fallback
    prev_open_until = ollama_client._open_until
    try:
        ollama_client._open_until = 9e18
        resp3 = await async_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"content": "Gợi ý đồ uống ít đắng dưới 45k không sữa"},
            headers={"X-Session-Token": token},
        )
        assert resp3.status_code == 200
        events3 = _parse_sse_events(resp3.text)
        done3 = next(data for name, data in events3 if name == "done")
        assert isinstance(done3, dict)
        assert done3["degraded"] is True
        assert any(name == "products" for name, _ in events3)
    finally:
        ollama_client._open_until = prev_open_until


async def test_chat_rate_limit_blocks_excess_messages(
    async_client: AsyncClient,
) -> None:
    chat_rate_limiter.reset()
    sess_resp = await async_client.post("/api/v1/chat/sessions", json={"language": "vi"})
    sess = sess_resp.json()
    session_id = sess["session_id"]
    token = sess["session_token"]

    try:
        for _ in range(8):
            r = await async_client.post(
                f"/api/v1/chat/sessions/{session_id}/messages",
                json={"content": "Viết giúp mình code Python"},
                headers={"X-Session-Token": token},
            )
            assert r.status_code == 200

        r_blocked = await async_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"content": "Viết giúp mình code Python"},
            headers={"X-Session-Token": token},
        )
        assert r_blocked.status_code == 429
    finally:
        chat_rate_limiter.reset()
