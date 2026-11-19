from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter

from app.core.config import settings
from app.db.session import check_db_connection
from app.integrations.ollama_client import ollama_client

router = APIRouter(tags=["Health"])


@router.get("/health")
async def liveness_check() -> dict[str, Any]:
    """Liveness check & warm-up endpoint (không chạm Database hoặc Ollama)."""
    return {
        "status": "ok",
        "service": "brew-bean-landing-api",
        "version": settings.APP_VERSION,
        "env": settings.APP_ENV,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/ready")
async def readiness_check() -> dict[str, Any]:
    """
    Readiness check (Giai đoạn P0):
    Kiểm tra kết nối đồng thời tới PostgreSQL 17 (localhost:5432 + extensions)
    và Ollama AI Node (127.0.0.1:11434 + models Qwen3 & BGE-M3).
    """
    db_info, ollama_info = await asyncio.gather(
        check_db_connection(),
        ollama_client.check_health(),
    )

    is_db_ready = bool(db_info.get("connected")) and not db_info.get("missing_extensions")
    is_ollama_online = bool(ollama_info.get("connected"))
    ai_mode = "online" if is_ollama_online else "fast_lookup_only"

    overall_status = "ready" if is_db_ready else "degraded"

    return {
        "status": overall_status,
        "ready": is_db_ready,
        "ai_mode": ai_mode,
        "environment": settings.APP_ENV,
        "docker_used": False,
        "postgresql": db_info,
        "ollama": ollama_info,
        "timestamp": datetime.now(UTC).isoformat(),
    }
