#!/usr/bin/env python3
"""
BREW & BEAN — Ollama Local Benchmark Utility (Giai đoạn P0)
Đo tốc độ Embedding (bge-m3) và Generation (qwen3:4b / qwen3:8b với think=false)
trên máy tính cá nhân thông qua http://127.0.0.1:11434.
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3")
CANDIDATE_LLM_MODELS = ["qwen3:4b", "qwen3:8b"]

TEST_EMBED_TEXTS = [
    "Mình muốn tìm đồ uống ít đắng, béo nhẹ, có sữa dưới 50k uống buổi chiều.",
    "Cold Brew ủ lạnh 18 giờ từ hạt Arabica Cầu Đất mang hương cam thảo và hậu vị ngọt thanh.",
    "Khách dị ứng sữa bò (lactose/dairy) có thể chọn Americano, Cold Brew Cam Sả hoặc Trà Ô Long Đào.",
]

TEST_CHAT_PROMPTS = [
    {
        "name": "Tư vấn khẩu vị (Taste Recommendation)",
        "system": (
            "Bạn là Bean AI — Barista tư vấn trực tuyến của thương hiệu cà phê BREW & BEAN. "
            "Trả lời ngắn gọn (3-4 câu), thân thiện bằng tiếng Việt, chỉ dựa trên menu được cung cấp."
        ),
        "user": (
            "Menu hiện có:\n"
            "1. Caramel Macchiato (Size M: 45.000đ) - Độ đắng 2/5, ngọt dịu, có sữa tươi & sốt caramel.\n"
            "2. Bạc Xỉu Đá Cầu Đất (Size M: 39.000đ) - Độ đắng 2/5, béo ngọt, nhiều sữa.\n"
            "3. Cold Brew Truyền Thống (Size M: 45.000đ) - Độ đắng 3/5, không sữa, thanh mát.\n\n"
            "Khách hỏi: Mình không quen uống đắng, thích vị béo nhẹ và ngân sách dưới 50k thì nên chọn món nào?"
        ),
    },
    {
        "name": "Kiến thức cà phê (Coffee Knowledge)",
        "system": (
            "Bạn là Bean AI — Barista của BREW & BEAN. Giải thích kiến thức cà phê dễ hiểu, "
            "súc tích trong khoảng 80-120 từ."
        ),
        "user": "Cold Brew khác gì với Espresso pha đá thông thường vậy bạn?",
    },
]


def http_json(method: str, path: str, payload: dict[str, Any] | None = None, timeout: float = 30.0) -> Any:
    url = f"{OLLAMA_BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_installed_models() -> list[str]:
    data = http_json("GET", "/api/tags", timeout=5.0)
    return [m.get("name", "") for m in data.get("models", [])]


def benchmark_embedding(model: str) -> dict[str, Any]:
    print(f"\n[1/2] Đang benchmark Embedding model: {model} ...")
    # Warm-up call
    http_json("POST", "/api/embed", {"model": model, "input": "Warm up BGE-M3"}, timeout=60.0)

    latencies_ms: list[float] = []
    dimension = 0
    for idx, text in enumerate(TEST_EMBED_TEXTS, start=1):
        t0 = time.perf_counter()
        res = http_json("POST", "/api/embed", {"model": model, "input": text}, timeout=30.0)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        embeddings = res.get("embeddings") or []
        if embeddings:
            dimension = len(embeddings[0])
        latencies_ms.append(round(elapsed_ms, 2))
        print(f"  - Câu mẫu #{idx}: {elapsed_ms:.1f} ms (dim={dimension})")

    avg_ms = round(statistics.mean(latencies_ms), 2)
    print(f"  => Trung bình Embedding: {avg_ms:.1f} ms | Số chiều vector: {dimension}")
    return {
        "model": model,
        "dimension": dimension,
        "latencies_ms": latencies_ms,
        "avg_latency_ms": avg_ms,
    }


def benchmark_chat_model(model: str) -> dict[str, Any]:
    print(f"\n[2/2] Đang benchmark Generation model: {model} (stream=True, think=False) ...")
    # Warm-up model in memory
    warmup_payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Xin chào"}],
        "stream": False,
        "think": False,
        "options": {"num_ctx": 4096, "num_predict": 16, "temperature": 0.3},
    }
    try:
        http_json("POST", "/api/chat", warmup_payload, timeout=90.0)
    except Exception as exc:
        print(f"  ! Không thể warm-up {model}: {exc}")
        return {"model": model, "error": str(exc)}

    runs: list[dict[str, Any]] = []
    for item in TEST_CHAT_PROMPTS:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": item["system"]},
                {"role": "user", "content": item["user"]},
            ],
            "stream": True,
            "think": False,
            "options": {
                "num_ctx": 4096,
                "num_predict": 220,
                "temperature": 0.3,
            },
        }
        url = f"{OLLAMA_BASE_URL}/api/chat"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        t0 = time.perf_counter()
        ttft_ms: float | None = None
        chunks: list[str] = []
        eval_count = 0
        eval_duration_ns = 0

        with urllib.request.urlopen(req, timeout=120.0) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                chunk_obj = json.loads(line)
                content_piece = chunk_obj.get("message", {}).get("content", "")
                if content_piece:
                    if ttft_ms is None:
                        ttft_ms = (time.perf_counter() - t0) * 1000.0
                    chunks.append(content_piece)
                if chunk_obj.get("done"):
                    eval_count = chunk_obj.get("eval_count", len(chunks))
                    eval_duration_ns = chunk_obj.get("eval_duration", 0)
                    break

        total_ms = (time.perf_counter() - t0) * 1000.0
        if ttft_ms is None:
            ttft_ms = total_ms
        if eval_duration_ns > 0:
            tps = eval_count / (eval_duration_ns / 1e9)
        else:
            gen_time_s = max((total_ms - ttft_ms) / 1000.0, 0.001)
            tps = max(eval_count, len(chunks)) / gen_time_s

        answer_preview = "".join(chunks).strip().replace("\n", " ")[:140]
        print(
            f"  - [{item['name']}] TTFT: {ttft_ms:.0f} ms | "
            f"Tổng: {total_ms:.0f} ms | Tốc độ: {tps:.1f} tokens/s | Tokens: {eval_count}"
        )
        print(f"    Trích phản hồi: \"{answer_preview}...\"")
        runs.append(
            {
                "test_name": item["name"],
                "ttft_ms": round(ttft_ms, 2),
                "total_ms": round(total_ms, 2),
                "tokens_per_sec": round(tps, 2),
                "eval_count": eval_count,
                "preview": answer_preview,
            }
        )

    avg_ttft = round(statistics.mean(r["ttft_ms"] for r in runs), 2)
    avg_tps = round(statistics.mean(r["tokens_per_sec"] for r in runs), 2)
    avg_total = round(statistics.mean(r["total_ms"] for r in runs), 2)
    print(f"  => Trung bình {model}: TTFT = {avg_ttft:.0f} ms | Tốc độ = {avg_tps:.1f} tokens/s")
    return {
        "model": model,
        "avg_ttft_ms": avg_ttft,
        "avg_total_ms": avg_total,
        "avg_tokens_per_sec": avg_tps,
        "runs": runs,
    }


def main() -> int:
    print("=" * 72)
    print("BREW & BEAN — OLLAMA LOCAL BENCHMARK (GIAI ĐOẠN P0)")
    print(f"Target Ollama Endpoint: {OLLAMA_BASE_URL}")
    print("=" * 72)

    try:
        version_info = http_json("GET", "/api/version", timeout=5.0)
        print(f"Ollama Version: {version_info.get('version', 'unknown')}")
    except Exception as exc:
        print(f"[LỖI] Không thể kết nối tới Ollama tại {OLLAMA_BASE_URL}: {exc}")
        return 1

    installed = get_installed_models()
    print(f"Models đã cài đặt: {', '.join(installed) if installed else '(trống)'}")

    embed_result = benchmark_embedding(EMBEDDING_MODEL)

    # Benchmark các model Qwen3 có sẵn trên máy
    available_llms = []
    for candidate in CANDIDATE_LLM_MODELS:
        if any(m == candidate or m.startswith(candidate) for m in installed):
            available_llms.append(candidate)

    if not available_llms:
        # Fallback tìm bất kỳ model qwen nào có sẵn
        available_llms = [m for m in installed if "qwen" in m.lower()][:2]

    llm_results: list[dict[str, Any]] = []
    for llm in available_llms:
        res = benchmark_chat_model(llm)
        if "error" not in res:
            llm_results.append(res)

    recommended_model = "qwen3:4b"
    if llm_results:
        # Ưu tiên model đạt SLO TTFT <= 2500ms (GPU) hoặc <= 9000ms (CPU) với tốc độ tốt nhất
        passing = [r for r in llm_results if r["avg_ttft_ms"] <= 2500]
        if passing:
            # Nếu qwen3:8b đạt TTFT <= 2500ms và >= 15 tok/s thì chọn, ngược lại chọn model nhanh nhất
            q8 = next((r for r in passing if r["model"].startswith("qwen3:8b") and r["avg_tokens_per_sec"] >= 15), None)
            recommended_model = q8["model"] if q8 else sorted(passing, key=lambda x: x["avg_ttft_ms"])[0]["model"]
        else:
            recommended_model = sorted(llm_results, key=lambda x: x["avg_ttft_ms"])[0]["model"]

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "ollama_base_url": OLLAMA_BASE_URL,
        "ollama_version": version_info.get("version", "unknown"),
        "embedding_benchmark": embed_result,
        "llm_benchmarks": llm_results,
        "recommended_llm_model": recommended_model,
        "recommended_embedding_model": EMBEDDING_MODEL,
    }

    out_path = Path(__file__).resolve().parent / "benchmark_results.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 72)
    print(f"KẾT LUẬN BENCHMARK P0:")
    print(f"  - Embedding Model chốt : {EMBEDDING_MODEL} ({embed_result['dimension']} dims, avg {embed_result['avg_latency_ms']} ms)")
    print(f"  - Generation Model chốt: {recommended_model} (think=false)")
    print(f"  - File báo cáo         : {out_path}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
