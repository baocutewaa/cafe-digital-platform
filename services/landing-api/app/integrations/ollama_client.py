from __future__ import annotations

import json
import time
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import OllamaUnavailableError


class OllamaClient:
    """
    Client kết nối Ollama AI Node:
    - Giai đoạn P0-P6 (Local No-Docker): http://127.0.0.1:11434
    - Giai đoạn P7 (Cloudflare Tunnel): https://ai.<domain> kèm CF-Access-Client-Id/Secret
    Tích hợp Circuit Breaker để chuyển sang chế độ Fast Lookup khi tắt Ollama/PC.
    """

    def __init__(self) -> None:
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self._failure_count = 0
        self._open_until = 0.0
        self._failure_threshold = 3
        self._cooldown_seconds = 15.0

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if settings.CF_ACCESS_CLIENT_ID and settings.CF_ACCESS_CLIENT_SECRET:
            headers["CF-Access-Client-Id"] = settings.CF_ACCESS_CLIENT_ID
            headers["CF-Access-Client-Secret"] = settings.CF_ACCESS_CLIENT_SECRET
        return headers

    @property
    def is_circuit_open(self) -> bool:
        if self._open_until <= 0:
            return False
        if time.monotonic() >= self._open_until:
            self._open_until = 0.0
            self._failure_count = 0
            return False
        return True

    def _record_success(self) -> None:
        self._failure_count = 0
        self._open_until = 0.0

    def _record_failure(self) -> None:
        self._failure_count += 1
        if self._failure_count >= self._failure_threshold:
            self._open_until = time.monotonic() + self._cooldown_seconds

    async def check_health(self) -> dict[str, Any]:
        t0 = time.perf_counter()
        timeout = httpx.Timeout(
            connect=settings.OLLAMA_CONNECT_TIMEOUT_S,
            read=5.0,
            write=5.0,
            pool=5.0,
        )
        try:
            async with httpx.AsyncClient(timeout=timeout, headers=self._headers()) as client:
                ver_resp = await client.get(f"{self.base_url}/api/version")
                ver_resp.raise_for_status()
                version_data = ver_resp.json()

                installed_models: list[str] = []
                try:
                    tags_resp = await client.get(f"{self.base_url}/api/tags")
                    if tags_resp.status_code == 200:
                        installed_models = [
                            m.get("name", "") for m in tags_resp.json().get("models", [])
                        ]
                except Exception:
                    pass

            self._record_success()
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            has_llm = any(
                m == settings.LLM_MODEL or m.startswith(settings.LLM_MODEL)
                for m in installed_models
            )
            has_embed = any(
                m == settings.EMBEDDING_MODEL or m.startswith(settings.EMBEDDING_MODEL)
                for m in installed_models
            )

            return {
                "status": "online",
                "connected": True,
                "ai_mode": "online",
                "base_url": self.base_url,
                "version": version_data.get("version", "unknown"),
                "latency_ms": latency_ms,
                "llm_model": settings.LLM_MODEL,
                "embedding_model": settings.EMBEDDING_MODEL,
                "llm_model_ready": has_llm,
                "embedding_model_ready": has_embed,
                "installed_models": installed_models,
                "circuit_breaker": "closed",
            }
        except Exception as exc:
            self._record_failure()
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            return {
                "status": "offline",
                "connected": False,
                "ai_mode": "fast_lookup_only",
                "base_url": self.base_url,
                "latency_ms": latency_ms,
                "llm_model": settings.LLM_MODEL,
                "embedding_model": settings.EMBEDDING_MODEL,
                "llm_model_ready": False,
                "embedding_model_ready": False,
                "installed_models": [],
                "circuit_breaker": "open" if self.is_circuit_open else "half_open",
                "error": str(exc),
            }

    async def embed(self, texts: str | list[str]) -> list[list[float]]:
        if self.is_circuit_open:
            raise OllamaUnavailableError("Circuit breaker đang mở cho Ollama AI Node.")

        timeout = httpx.Timeout(
            connect=settings.OLLAMA_CONNECT_TIMEOUT_S,
            read=settings.OLLAMA_READ_TIMEOUT_S,
            write=10.0,
            pool=5.0,
        )
        payload = {"model": settings.EMBEDDING_MODEL, "input": texts}
        try:
            async with httpx.AsyncClient(timeout=timeout, headers=self._headers()) as client:
                resp = await client.post(f"{self.base_url}/api/embed", json=payload)
                resp.raise_for_status()
                data = resp.json()
                self._record_success()
                return data.get("embeddings", [])
        except Exception as exc:
            self._record_failure()
            raise OllamaUnavailableError(f"Lỗi gọi Ollama /api/embed: {exc}") from exc

    async def stream_chat(
        self, messages: list[dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        if self.is_circuit_open:
            raise OllamaUnavailableError("Circuit breaker đang mở cho Ollama AI Node.")

        timeout = httpx.Timeout(
            connect=settings.OLLAMA_CONNECT_TIMEOUT_S,
            read=settings.OLLAMA_READ_TIMEOUT_S,
            write=10.0,
            pool=5.0,
        )
        payload = {
            "model": settings.LLM_MODEL,
            "messages": messages,
            "stream": True,
            "think": False,
            "options": {
                "num_ctx": settings.LLM_NUM_CTX,
                "num_predict": settings.LLM_NUM_PREDICT,
                "temperature": settings.LLM_TEMPERATURE,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=timeout, headers=self._headers()) as client:
                async with client.stream(
                    "POST", f"{self.base_url}/api/chat", json=payload
                ) as resp:
                    resp.raise_for_status()
                    self._record_success()
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        chunk = json.loads(line)
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            yield token
                        if chunk.get("done"):
                            break
        except Exception as exc:
            self._record_failure()
            raise OllamaUnavailableError(f"Lỗi stream Ollama /api/chat: {exc}") from exc


ollama_client = OllamaClient()
