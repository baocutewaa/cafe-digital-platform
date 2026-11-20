from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.endpoints import health
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import (
    RateLimitExceededError,
    ResourceNotFoundError,
    UnauthorizedSessionError,
)
from app.core.logging import setup_logging
from app.db.session import engine
from app.services.cache_seed_service import startup_seed_answer_cache

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    logger.info(
        "Starting %s (%s) — Ollama: %s | Model: %s",
        settings.APP_NAME,
        settings.APP_ENV,
        settings.OLLAMA_BASE_URL,
        settings.LLM_MODEL,
    )
    await startup_seed_answer_cache()
    yield
    await engine.dispose()
    logger.info("Shutdown complete.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(api_router, prefix="/api/v1")

    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found_handler(
        _request: Request, exc: ResourceNotFoundError
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(UnauthorizedSessionError)
    async def unauthorized_session_handler(
        _request: Request, exc: UnauthorizedSessionError
    ) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(RateLimitExceededError)
    async def rate_limit_handler(
        _request: Request, exc: RateLimitExceededError
    ) -> JSONResponse:
        return JSONResponse(status_code=429, content={"detail": str(exc)})

    return app


app = create_app()
