export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1"
).replace(/\/+$/, "");

export const BACKEND_ORIGIN = API_BASE_URL.replace(/\/api\/v1$/, "");

export type CaffeineLevel = "none" | "low" | "medium" | "high";
export type ProductSize = "small" | "regular" | "large";
export type ProductTemperature = "hot" | "iced" | "both";
export type DiscountType = "percentage" | "fixed_amount" | "bundle";

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

export interface CategorySummary {
  id: string;
  slug: string;
  name_vi: string;
  name_en: string;
}

export interface MenuCategory extends CategorySummary {
  description_vi?: string | null;
  description_en?: string | null;
  display_order: number;
  product_count: number;
}

export interface ProductVariant {
  id: string;
  sku: string;
  size: ProductSize;
  temperature: ProductTemperature;
  price_vnd: number;
  calories_kcal?: number | null;
  is_available: boolean;
}

export interface ProductIngredient {
  code: string;
  name_vi: string;
  name_en: string;
  allergen_code?: string | null;
  is_optional: boolean;
}

export interface ProductSummary {
  id: string;
  slug: string;
  name_vi: string;
  name_en: string;
  short_description_vi: string;
  short_description_en?: string | null;
  image_url: string;
  category: CategorySummary;
  taste_tags: string[];
  caffeine_level: CaffeineLevel;
  bitterness_level: number;
  sweetness_level: number;
  has_milk: boolean;
  is_signature: boolean;
  is_featured: boolean;
  min_price_vnd: number;
  max_price_vnd: number;
  allergens: string[];
  variants: ProductVariant[];
}

export interface ProductDetail extends ProductSummary {
  story_vi?: string | null;
  ingredients: ProductIngredient[];
}

export interface PromotionProductRef {
  id: string;
  slug: string;
  name_vi: string;
  name_en: string;
  image_url: string;
}

export interface Promotion {
  id: string;
  slug: string;
  title_vi: string;
  title_en?: string | null;
  summary_vi: string;
  conditions_vi: string;
  promo_code?: string | null;
  discount_type: DiscountType;
  discount_value: number;
  banner_image_url?: string | null;
  start_at: string;
  end_at: string;
  products: PromotionProductRef[];
}

export interface StoreHour {
  day_of_week: number;
  open_time: string;
  close_time: string;
  is_closed: boolean;
}

export interface Store {
  id: string;
  slug: string;
  name: string;
  address: string;
  district?: string | null;
  city: string;
  phone?: string | null;
  google_maps_url?: string | null;
  latitude?: string | null;
  longitude?: string | null;
  amenities: string[];
  image_url?: string | null;
  is_active: boolean;
  is_open_now: boolean;
  today_hours?: StoreHour | null;
  hours: StoreHour[];
}

export interface StorefrontOverview {
  brand_name: string;
  tagline_vi: string;
  tagline_en: string;
  story_summary_vi: string;
  ai_mode: "online" | "fast_lookup_only";
  ai_model?: string | null;
  embedding_model?: string | null;
  phase: string;
  stats: {
    stores_count: number;
    categories_count: number;
    products_count: number;
    active_promotions_count: number;
  };
  signature_products: ProductSummary[];
  active_promotions: Promotion[];
}

export interface ListResponse<T> {
  items: T[];
  total: number;
}

export interface ProductFilterQuery {
  category?: string;
  max_price?: number;
  caffeine_level?: CaffeineLevel;
  has_milk?: boolean;
  taste_tag?: string;
  signature?: boolean;
  featured?: boolean;
  q?: string;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new ApiError(response.status, `HTTP ${response.status}: ${response.statusText}`);
  }
  return (await response.json()) as T;
}

function buildQueryString(params: Record<string, string | number | boolean | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, val] of Object.entries(params)) {
    if (val !== undefined && val !== "") {
      search.set(key, String(val));
    }
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export const apiClient = {
  getHealth: () => fetchJson<HealthResponse>(`${BACKEND_ORIGIN}/health`),
  getReady: () => fetchJson<ReadyResponse>(`${BACKEND_ORIGIN}/ready`),
  getStorefront: () => fetchJson<StorefrontOverview>(`${API_BASE_URL}/storefront`),
  getStores: () => fetchJson<ListResponse<Store>>(`${API_BASE_URL}/stores`),
  getStoreBySlug: (slug: string) => fetchJson<Store>(`${API_BASE_URL}/stores/${encodeURIComponent(slug)}`),
  getCategories: () => fetchJson<ListResponse<MenuCategory>>(`${API_BASE_URL}/menu/categories`),
  getProducts: (filters: ProductFilterQuery = {}) => {
    const qs = buildQueryString({
      category: filters.category,
      max_price: filters.max_price,
      caffeine_level: filters.caffeine_level,
      has_milk: filters.has_milk,
      taste_tag: filters.taste_tag,
      signature: filters.signature,
      featured: filters.featured,
      q: filters.q?.trim() || undefined,
    });
    return fetchJson<ListResponse<ProductSummary>>(`${API_BASE_URL}/menu/products${qs}`);
  },
  getProductBySlug: (slug: string) =>
    fetchJson<ProductDetail>(`${API_BASE_URL}/menu/products/${encodeURIComponent(slug)}`),
  getActivePromotions: () => fetchJson<ListResponse<Promotion>>(`${API_BASE_URL}/promotions/active`),
};
