import { useQuery } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { SeoHead } from "@/components/shared/SeoHead";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useChatWidget } from "@/features/chat/context/ChatWidgetContext";
import { MenuFilters } from "@/features/menu/components/MenuFilters";
import { ProductGrid } from "@/features/menu/components/ProductGrid";
import { apiClient, type CaffeineLevel, type ProductFilterQuery } from "@/lib/api-client";

const VALID_CAFFEINE: CaffeineLevel[] = ["none", "low", "medium", "high"];

function parseFiltersFromSearchParams(params: URLSearchParams): ProductFilterQuery {
  const category = params.get("category") || undefined;
  const rawPrice = params.get("max_price");
  const parsedPrice = rawPrice ? Number(rawPrice) : undefined;
  const max_price =
    parsedPrice !== undefined && Number.isFinite(parsedPrice) && parsedPrice >= 0
      ? parsedPrice
      : undefined;

  const rawCaff = params.get("caffeine_level") as CaffeineLevel | null;
  const caffeine_level = rawCaff && VALID_CAFFEINE.includes(rawCaff) ? rawCaff : undefined;

  const rawMilk = params.get("has_milk");
  const has_milk = rawMilk === "true" ? true : rawMilk === "false" ? false : undefined;

  const taste_tag = params.get("taste_tag") || undefined;
  const signature = params.get("signature") === "true" ? true : undefined;
  const q = params.get("q") || undefined;

  return { category, max_price, caffeine_level, has_milk, taste_tag, signature, q };
}

export function MenuPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { openChatWithPrompt } = useChatWidget();

  const filters = useMemo(() => parseFiltersFromSearchParams(searchParams), [searchParams]);
  const [searchText, setSearchText] = useState(filters.q ?? "");

  useEffect(() => {
    setSearchText(filters.q ?? "");
  }, [filters.q]);

  // Debounce search text sync to URL query param `q`
  useEffect(() => {
    const timer = window.setTimeout(() => {
      const trimmed = searchText.trim();
      const currentQ = searchParams.get("q") ?? "";
      if (trimmed === currentQ) return;
      const next = new URLSearchParams(searchParams);
      if (trimmed) {
        next.set("q", trimmed);
      } else {
        next.delete("q");
      }
      setSearchParams(next, { replace: true });
    }, 250);
    return () => window.clearTimeout(timer);
  }, [searchText, searchParams, setSearchParams]);

  const updateFilter = (patch: Partial<ProductFilterQuery>) => {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(patch)) {
      if (value === undefined || value === "") {
        next.delete(key);
      } else {
        next.set(key, String(value));
      }
    }
    setSearchParams(next, { replace: true });
  };

  const resetFilters = () => {
    setSearchText("");
    setSearchParams(new URLSearchParams(), { replace: true });
  };

  const categoriesQuery = useQuery({
    queryKey: ["menu-categories"],
    queryFn: apiClient.getCategories,
  });

  const productsQuery = useQuery({
    queryKey: ["menu-products", filters],
    queryFn: () => apiClient.getProducts(filters),
  });

  const categories = categoriesQuery.data?.items ?? [];
  const products = productsQuery.data?.items ?? [];

  return (
    <>
      <SeoHead
        title="Thực đơn BREW & BEAN — Lọc theo khẩu vị, giá & caffeine"
        description="Khám phá 30 đồ uống cà phê đặc sản, Cold Brew ủ lạnh 18h, Matcha Uji, sữa hạt không caffeine và bánh ngọt thủ công."
      />

      <div className="mx-auto max-w-6xl space-y-8 px-4 py-12 sm:px-6">
        <div className="flex flex-col justify-between gap-4 border-b border-border/70 pb-6 sm:flex-row sm:items-end">
          <div className="space-y-2">
            <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Menu &amp; Dinh dưỡng
            </p>
            <h1 className="font-serif text-3xl font-medium tracking-[-0.02em] sm:text-4xl">
              Thực đơn BREW &amp; BEAN
            </h1>
            <p className="text-sm text-muted-foreground sm:text-base">
              Lọc nhanh theo danh mục, mức giá, lượng caffeine, đồ uống không sữa bò và tag hương vị.
            </p>
          </div>

          <Button
            type="button"
            variant="outline"
            className="gap-2 self-start text-[11px] uppercase tracking-[0.14em]"
            onClick={() =>
              openChatWithPrompt("Mình đang xem Menu, hãy gợi ý món hợp khẩu vị giúp mình!")
            }
          >
            <Sparkles className="h-3.5 w-3.5 text-accent" />
            Nhờ Bean AI gợi ý món
          </Button>
        </div>

        <MenuFilters
          categories={categories}
          filters={filters}
          searchText={searchText}
          onSearchTextChange={setSearchText}
          onUpdateFilter={updateFilter}
          onReset={resetFilters}
        />

        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            {productsQuery.isLoading
              ? "Đang tải thực đơn..."
              : `Hiển thị ${products.length} sản phẩm`}
          </span>
        </div>

        {productsQuery.isError ? (
          <Card className="p-6 text-sm text-destructive">
            Không tải được danh sách sản phẩm từ API. Vui lòng thử lại sau.
          </Card>
        ) : (
          <ProductGrid
            products={products}
            isLoading={productsQuery.isLoading}
            onResetFilters={resetFilters}
          />
        )}
      </div>
    </>
  );
}
