from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

REQUIRED_EXTENSIONS = ("vector", "pg_trgm", "unaccent", "pgcrypto")

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def check_db_connection() -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            ver_res = await session.execute(
                text("SELECT current_database(), current_setting('server_version')")
            )
            db_name, server_ver = ver_res.one()

            ext_res = await session.execute(
                text(
                    "SELECT extname, extversion FROM pg_extension "
                    "WHERE extname IN ('vector', 'pg_trgm', 'unaccent', 'pgcrypto') "
                    "ORDER BY extname"
                )
            )
            installed_exts = {row[0]: row[1] for row in ext_res.all()}

        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        missing = [ext for ext in REQUIRED_EXTENSIONS if ext not in installed_exts]
        return {
            "status": "connected" if not missing else "missing_extensions",
            "connected": True,
            "database": db_name,
            "server_version": server_ver,
            "latency_ms": latency_ms,
            "extensions": installed_exts,
            "missing_extensions": missing,
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return {
            "status": "disconnected",
            "connected": False,
            "latency_ms": latency_ms,
            "error": str(exc),
            "extensions": {},
            "missing_extensions": list(REQUIRED_EXTENSIONS),
        }
