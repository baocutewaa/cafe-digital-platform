from __future__ import annotations

import httpx

from app.core.config import settings
from rag.ingestion import IngestionError


class OllamaEmbedder:
    """Batch embedder calling Ollama Local /api/embed (bge-m3, 1024 dims)."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        expected_dim: int | None = None,
        timeout_s: float = 120.0,
    ) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.EMBEDDING_MODEL
        self.expected_dim = expected_dim or settings.EMBEDDING_DIMENSION
        self.timeout_s = timeout_s

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if settings.CF_ACCESS_CLIENT_ID and settings.CF_ACCESS_CLIENT_SECRET:
            headers["CF-Access-Client-Id"] = settings.CF_ACCESS_CLIENT_ID
            headers["CF-Access-Client-Secret"] = settings.CF_ACCESS_CLIENT_SECRET
        return headers

    async def embed_batch(self, texts: list[str], batch_size: int = 16) -> list[list[float]]:
        if not texts:
            return []

        all_embeddings: list[list[float]] = []
        timeout = httpx.Timeout(connect=5.0, read=self.timeout_s, write=30.0, pool=10.0)

        async with httpx.AsyncClient(timeout=timeout, headers=self._headers()) as client:
            for start in range(0, len(texts), batch_size):
                batch = texts[start : start + batch_size]
                payload = {"model": self.model, "input": batch}
                try:
                    resp = await client.post(f"{self.base_url}/api/embed", json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as exc:
                    raise IngestionError(
                        f"Lỗi gọi Ollama {self.base_url}/api/embed ({self.model}): {exc}"
                    ) from exc

                vectors = data.get("embeddings") or []
                if len(vectors) != len(batch):
                    raise IngestionError(
                        f"Số vector trả về ({len(vectors)}) không khớp batch ({len(batch)})."
                    )
                for vec in vectors:
                    if len(vec) != self.expected_dim:
                        raise IngestionError(
                            f"Số chiều embedding ({len(vec)}) khác kỳ vọng ({self.expected_dim})."
                        )
                    all_embeddings.append([float(x) for x in vec])

        return all_embeddings
