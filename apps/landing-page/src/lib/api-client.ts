const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1"
).replace(/\/+$/, "");

export const BACKEND_ORIGIN = API_BASE_URL.replace(/\/api\/v1$/, "");

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  env: string;
  timestamp: string;
}

export interface PostgresReadyInfo {
  status: string;
  connected: boolean;
  database?: string;
  server_version?: string;
  latency_ms: number;
  extensions: Record<string, string>;
  missing_extensions: string[];
  error?: string;
}

export interface OllamaReadyInfo {
  status: string;
  connected: boolean;
  ai_mode: "online" | "fast_lookup_only";
  base_url: string;
  version?: string;
  latency_ms: number;
  llm_model: string;
  embedding_model: string;
  llm_model_ready: boolean;
  embedding_model_ready: boolean;
  installed_models: string[];
  circuit_breaker: string;
  error?: string;
}

export interface ReadyResponse {
  status: "ready" | "degraded";
  ready: boolean;
  ai_mode: "online" | "fast_lookup_only";
  environment: string;
  docker_used: boolean;
  postgresql: PostgresReadyInfo;
  ollama: OllamaReadyInfo;
  timestamp: string;
}

export interface StorefrontOverview {
  brand_name: string;
  tagline_vi: string;
  tagline_en: string;
  ai_mode: "online" | "fast_lookup_only";
  ai_model: string;
  embedding_model: string;
  phase: string;
}

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export const apiClient = {
  getHealth: () => fetchJson<HealthResponse>(`${BACKEND_ORIGIN}/health`),
  getReady: () => fetchJson<ReadyResponse>(`${BACKEND_ORIGIN}/ready`),
  getStorefront: () => fetchJson<StorefrontOverview>(`${API_BASE_URL}/storefront`),
};
