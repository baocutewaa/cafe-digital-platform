from __future__ import annotations

from httpx import AsyncClient


async def test_ready_endpoint_reports_postgres_and_ollama_status(
    async_client: AsyncClient,
) -> None:
    resp = await async_client.get("/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["docker_used"] is False
    assert body["postgresql"]["connected"] is True
    assert body["postgresql"]["missing_extensions"] == []
    assert set(body["postgresql"]["extensions"].keys()) >= {
        "vector",
        "pg_trgm",
        "unaccent",
        "pgcrypto",
    }
    assert body["ollama"]["connected"] is True
    assert body["ready"] is True
    assert body["ai_mode"] == "online"


async def test_storefront_overview_endpoint(async_client: AsyncClient) -> None:
    resp = await async_client.get("/api/v1/storefront")
    assert resp.status_code == 200
    body = resp.json()
    assert body["brand_name"] == "BREW & BEAN"
    assert body["ai_mode"] in ("online", "fast_lookup_only")
