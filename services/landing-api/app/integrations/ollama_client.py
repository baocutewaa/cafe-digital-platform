from __future__ import annotations

import asyncio
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
    Tích hợp Circuit Breaker và giới hạn đồng thời LLM_MAX_CONCURRENCY.
    """

    def __init__(self) -> None:
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self._failure_count = 0
        self._open_until = 0.0
        self._failure_threshold = 3
        self._cooldown_seconds = 15.0
        self._cached_health: dict[str, Any] | None = None
        self._cached_health_at: float = 0.0
        self._health_cache_ttl: float = 10.0
        self._llm_semaphore = asyncio.Semaphore(max(1, settings.LLM_MAX_CONCURRENCY))
        self._model_think_modes: dict[str, str] = {}

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

    async def check_health(self, use_cache: bool = False) -> dict[str, Any]:
        now = time.monotonic()
        if (
            use_cache
            and self._cached_health is not None
            and (now - self._cached_health_at) < self._health_cache_ttl
        ):
            return self._cached_health

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

            result = {
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
            self._cached_health = result
            self._cached_health_at = time.monotonic()
            return result
        except Exception as exc:
            self._record_failure()
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            result = {
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
            self._cached_health = result
            self._cached_health_at = time.monotonic()
            return result

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

    async def _acquire_llm_slot(self) -> None:
        try:
            await asyncio.wait_for(
                self._llm_semaphore.acquire(),
                timeout=settings.LLM_QUEUE_TIMEOUT_S,
            )
        except TimeoutError as exc:
            raise OllamaUnavailableError("Hàng đợi LLM quá tải (queue timeout).") from exc

    def can_promote_think_mode(self, model_name: str | None = None) -> bool:
        target = model_name or settings.LLM_MODEL
        return self._model_think_modes.get(target) != "separate"

    def promote_to_separate_thinking(self, model_name: str | None = None) -> None:
        """
        Upgrade model to `separate` (`think=True` + larger `num_predict`) when runtime
        detects that the model ignores `think=False` and emits raw reasoning in `content`
        (e.g. Qwen3-Thinking-2507 / DeepSeek-R1 variants).
        """
        target = model_name or settings.LLM_MODEL
        self._model_think_modes[target] = "separate"

    async def _resolve_think_mode(
        self, client: httpx.AsyncClient, model_name: str
    ) -> str:
        """
        Determine how Ollama handles thinking for the configured model:
        - 'none': non-thinking instruct model (e.g. qwen2.5:3b); omit `think`
        - 'separate': thinking-only model (or promoted at runtime); pass `think=True`
          so Ollama keeps reasoning in `message.thinking` instead of `message.content`
        - 'disable': dual-mode thinking model; pass `think=False` initially
        """
        cached = self._model_think_modes.get(model_name)
        if cached is not None:
            return cached

        lower_name = model_name.lower()
        if any(tag in lower_name for tag in ("thinking", "deepseek-r1", "qwq")):
            self._model_think_modes[model_name] = "separate"
            return "separate"

        mode = "disable" if "qwen3" in lower_name else "none"
        try:
            resp = await client.post(
                f"{self.base_url}/api/show",
                json={"model": model_name},
                timeout=2.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                capabilities = data.get("capabilities") or []
                model_info = data.get("model_info") or {}
                template = str(data.get("template") or "")
                finetune = str(model_info.get("general.finetune") or "").lower()

                has_think_cap = "thinking" in capabilities or "<think>" in template
                if not has_think_cap and finetune != "thinking" and "qwen3" not in lower_name:
                    mode = "none"
                elif finetune == "thinking" or (
                    "<think>" in template and ".Think" not in template
                ):
                    mode = "separate"
                else:
                    mode = "disable"
                self._model_think_modes[model_name] = mode
        except Exception:
            pass
        return mode

    def _build_chat_payload(
        self,
        messages: list[dict[str, str]],
        stream: bool,
        think_mode: str = "disable",
    ) -> dict[str, Any]:
        num_predict = (
            max(settings.LLM_NUM_PREDICT, settings.LLM_THINK_NUM_PREDICT)
            if think_mode == "separate"
            else settings.LLM_NUM_PREDICT
        )
        payload: dict[str, Any] = {
            "model": settings.LLM_MODEL,
            "messages": messages,
            "stream": stream,
            "options": {
                "num_ctx": settings.LLM_NUM_CTX,
                "num_predict": num_predict,
                "temperature": settings.LLM_TEMPERATURE,
            },
        }
        if think_mode == "separate":
            payload["think"] = True
        elif think_mode == "disable":
            payload["think"] = False
        return payload

    async def chat(self, messages: list[dict[str, str]]) -> str:
        """Non-streaming chat completion (used for cache prewarming & evaluations)."""
        if self.is_circuit_open:
            raise OllamaUnavailableError("Circuit breaker đang mở cho Ollama AI Node.")

        await self._acquire_llm_slot()
        timeout = httpx.Timeout(
            connect=settings.OLLAMA_CONNECT_TIMEOUT_S,
            read=settings.OLLAMA_READ_TIMEOUT_S,
            write=10.0,
            pool=5.0,
        )
        try:
            async with httpx.AsyncClient(timeout=timeout, headers=self._headers()) as client:
                think_mode = await self._resolve_think_mode(client, settings.LLM_MODEL)
                payload = self._build_chat_payload(
                    messages, stream=False, think_mode=think_mode
                )
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                if resp.status_code == 400 and "think" in payload:
                    payload.pop("think", None)
                    payload["options"]["num_predict"] = max(
                        settings.LLM_NUM_PREDICT, settings.LLM_THINK_NUM_PREDICT
                    )
                    resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
                self._record_success()
                return str(data.get("message", {}).get("content", "")).strip()
        except Exception as exc:
            self._record_failure()
            raise OllamaUnavailableError(f"Lỗi gọi Ollama /api/chat: {exc}") from exc
        finally:
            self._llm_semaphore.release()

    async def stream_chat(
        self, messages: list[dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        if self.is_circuit_open:
            raise OllamaUnavailableError("Circuit breaker đang mở cho Ollama AI Node.")

        await self._acquire_llm_slot()
        timeout = httpx.Timeout(
            connect=settings.OLLAMA_CONNECT_TIMEOUT_S,
            read=settings.OLLAMA_READ_TIMEOUT_S,
            write=10.0,
            pool=5.0,
        )
        try:
            async with httpx.AsyncClient(timeout=timeout, headers=self._headers()) as client:
                think_mode = await self._resolve_think_mode(client, settings.LLM_MODEL)
                payload = self._build_chat_payload(
                    messages, stream=True, think_mode=think_mode
                )
                async with client.stream(
                    "POST", f"{self.base_url}/api/chat", json=payload
                ) as resp:
                    if resp.status_code == 400 and "think" in payload:
                        fallback_payload = dict(payload)
                        fallback_payload.pop("think", None)
                        fallback_payload["options"] = {
                            **payload["options"],
                            "num_predict": max(
                                settings.LLM_NUM_PREDICT, settings.LLM_THINK_NUM_PREDICT
                            ),
                        }
                        async with client.stream(
                            "POST", f"{self.base_url}/api/chat", json=fallback_payload
                        ) as retry_resp:
                            retry_resp.raise_for_status()
                            self._record_success()
                            async for line in retry_resp.aiter_lines():
                                if not line.strip():
                                    continue
                                chunk = json.loads(line)
                                token = chunk.get("message", {}).get("content", "")
                                if token:
                                    yield token
                                if chunk.get("done"):
                                    break
                        return

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
        finally:
            self._llm_semaphore.release()


ollama_client = OllamaClient()
