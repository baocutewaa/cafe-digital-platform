from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.integrations.ollama_client import ollama_client

router = APIRouter(tags=["Storefront"])


@router.get("/storefront")
async def get_storefront_overview() -> dict[str, Any]:
    """Thông tin tổng quan thương hiệu BREW & BEAN và trạng thái Bean AI."""
    ollama_health = await ollama_client.check_health()
    return {
        "brand_name": "BREW & BEAN",
        "tagline_vi": "Nghệ thuật Cà phê Đặc sản & Trợ lý Barista AI",
        "tagline_en": "Specialty Coffee Craft & Personal AI Barista",
        "ai_mode": ollama_health.get("ai_mode", "fast_lookup_only"),
        "ai_model": ollama_health.get("llm_model"),
        "embedding_model": ollama_health.get("embedding_model"),
        "phase": "P0 — Local Native Walking Skeleton (No-Docker)",
    }
