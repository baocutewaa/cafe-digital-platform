import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Flame,
  ShoppingBag,
  Sparkles,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { LazyImage } from "@/components/shared/LazyImage";
import { OrderQuickModal, type OrderDraft } from "@/components/shared/OrderQuickModal";
import { SeoHead } from "@/components/shared/SeoHead";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useChatWidget } from "@/features/chat/context/ChatWidgetContext";
import { FlavorMeter } from "@/features/menu/components/FlavorMeter";
import { apiClient, type ProductTemperature } from "@/lib/api-client";
import {
  ALLERGEN_LABELS,
  formatVnd,
  getOrderingAppUrl,
  SIZE_LABELS,
  TASTE_TAG_LABELS,
  TEMPERATURE_LABELS,
} from "@/lib/format";

export function ProductDetailPage() {
  const { slug = "" } = useParams();
  const { openChatWithPrompt } = useChatWidget();

  const productQuery = useQuery({
    queryKey: ["product-detail", slug],
    queryFn: () => apiClient.getProductBySlug(slug),
    enabled: Boolean(slug),
  });

  const product = productQuery.data;
  const [selectedVariantId, setSelectedVariantId] = useState<string>("");
  const [selectedTemp, setSelectedTemp] = useState<"hot" | "iced">("iced");
  const [orderDraft, setOrderDraft] = useState<OrderDraft | null>(null);

  useEffect(() => {
    if (!product || product.variants.length === 0) return;
    const defaultVariant =
      product.variants.find((v) => v.size === "regular" && v.is_available) ??
      product.variants.find((v) => v.is_available) ??
      product.variants[0];
    setSelectedVariantId(defaultVariant.id);
    if (defaultVariant.temperature === "hot") {
      setSelectedTemp("hot");
    } else {
      setSelectedTemp("iced");
    }
  }, [product]);

  if (productQuery.isLoading) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 px-4 py-10 sm:px-6">
        <Skeleton className="h-6 w-48" />
        <div className="grid gap-8 md:grid-cols-2">
          <Skeleton className="aspect-[4/3] w-full rounded-2xl" />
          <div className="space-y-4">
            <Skeleton className="h-10 w-3/4" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (productQuery.isError || !product) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center">
        <h1 className="font-serif text-2xl font-bold">Không tìm thấy sản phẩm</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Món bạn đang tìm không tồn tại hoặc tạm ngừng phục vụ.
        </p>
        <Link
          to="/menu"
          className="mt-6 inline-flex h-10 items-center gap-2 rounded-md bg-primary px-5 text-sm font-medium text-primary-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Quay lại Menu
        </Link>
      </div>
    );
  }

  const activeVariant =
    product.variants.find((v) => v.id === selectedVariantId) ?? product.variants[0];
  const allowedTemps: Array<"hot" | "iced"> =
    activeVariant.temperature === "both"
      ? ["iced", "hot"]
      : [activeVariant.temperature === "hot" ? "hot" : "iced"];
  const effectiveTemp: ProductTemperature = allowedTemps.includes(selectedTemp)
    ? selectedTemp
    : allowedTemps[0];

  const handleOrderClick = () => {
    const externalUrl = getOrderingAppUrl(activeVariant.sku, product.slug);
    if (externalUrl) {
      window.open(externalUrl, "_blank", "noopener,noreferrer");
      return;
    }
    setOrderDraft({
      productName: product.name_vi,
      productSlug: product.slug,
      sku: activeVariant.sku,
      size: activeVariant.size,
      temperature: effectiveTemp,
      priceVnd: activeVariant.price_vnd,
    });
  };

  return (
    <>
      <SeoHead
        title={`${product.name_vi} — BREW & BEAN`}
        description={product.short_description_vi}
      />

      <div className="mx-auto max-w-6xl space-y-8 px-4 py-8 sm:px-6 sm:py-12">
        <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-sm text-muted-foreground">
          <Link to="/menu" className="inline-flex items-center gap-1 hover:text-primary">
            <ArrowLeft className="h-4 w-4" />
            Thực đơn
          </Link>
          <span>/</span>
          <Link
            to={`/menu?category=${product.category.slug}`}
            className="hover:text-primary"
          >
            {product.category.name_vi}
          </Link>
          <span>/</span>
          <span className="font-medium text-foreground">{product.name_vi}</span>
        </nav>

        <div className="grid gap-10 lg:grid-cols-12">
          {/* Left column: Image & Story */}
          <div className="space-y-6 lg:col-span-6">
            <div className="overflow-hidden rounded-3xl border bg-card shadow-sm">
              <LazyImage
                src={product.image_url}
                alt={product.name_vi}
                width={800}
                height={600}
                priority
                className="aspect-[4/3] w-full"
              />
            </div>

            {product.story_vi && (
              <Card>
                <CardContent className="space-y-2 p-6">
                  <p className="text-xs font-semibold uppercase tracking-wider text-accent">
                    Câu chuyện đồ uống
                  </p>
                  <p className="leading-relaxed text-muted-foreground">{product.story_vi}</p>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right column: Specs, Variants, Allergens, CTAs */}
          <div className="space-y-6 lg:col-span-6">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">{product.category.name_vi}</Badge>
                {product.is_signature && (
                  <Badge className="bg-accent text-accent-foreground">Signature</Badge>
                )}
                {!product.has_milk && <Badge variant="success">Không sữa bò</Badge>}
              </div>

              <h1 className="font-serif text-3xl font-bold text-foreground sm:text-4xl">
                {product.name_vi}
              </h1>
              <p className="text-sm font-medium text-muted-foreground">{product.name_en}</p>
              <p className="text-base leading-relaxed text-foreground/90">
                {product.short_description_vi}
              </p>

              <div className="flex flex-wrap gap-1.5">
                {product.taste_tags.map((tag) => (
                  <Badge key={tag} variant="outline" className="text-xs font-normal">
                    {TASTE_TAG_LABELS[tag] ?? tag}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Flavor Meter */}
            <FlavorMeter
              bitterness={product.bitterness_level}
              sweetness={product.sweetness_level}
              caffeineLevel={product.caffeine_level}
            />

            {/* Size & Temp Selector */}
            <div className="space-y-4 rounded-2xl border bg-card p-5">
              <div className="flex items-baseline justify-between">
                <div>
                  <p className="text-xs text-muted-foreground">Giá bán niêm yết</p>
                  <p className="text-2xl font-bold text-primary">
                    {formatVnd(activeVariant.price_vnd)}
                  </p>
                </div>
                {activeVariant.calories_kcal !== null &&
                  activeVariant.calories_kcal !== undefined && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-secondary px-3 py-1 text-xs font-medium">
                      <Flame className="h-3.5 w-3.5 text-accent" />
                      {activeVariant.calories_kcal} kcal
                    </span>
                  )}
              </div>

              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Chọn Size
                </p>
                <div className="grid grid-cols-3 gap-2">
                  {product.variants.map((variant) => {
                    const selected = variant.id === activeVariant.id;
                    return (
                      <button
                        key={variant.id}
                        type="button"
                        disabled={!variant.is_available}
                        onClick={() => {
                          setSelectedVariantId(variant.id);
                          if (variant.temperature === "hot") setSelectedTemp("hot");
                          if (variant.temperature === "iced") setSelectedTemp("iced");
                        }}
                        className={`rounded-xl border px-3 py-2.5 text-left transition-colors ${
                          selected
                            ? "border-primary bg-primary/10 text-primary"
                            : "border-input bg-background hover:bg-secondary/50"
                        } disabled:cursor-not-allowed disabled:opacity-50`}
                      >
                        <div className="text-sm font-bold">{SIZE_LABELS[variant.size].full}</div>
                        <div className="text-xs font-medium">{formatVnd(variant.price_vnd)}</div>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Nhiệt độ phục vụ
                </p>
                <div className="flex gap-2">
                  {allowedTemps.map((temp) => (
                    <Button
                      key={temp}
                      type="button"
                      size="sm"
                      variant={effectiveTemp === temp ? "default" : "outline"}
                      onClick={() => setSelectedTemp(temp)}
                    >
                      {TEMPERATURE_LABELS[temp]}
                    </Button>
                  ))}
                </div>
              </div>

              <p className="text-xs text-muted-foreground">
                Mã SKU: <code className="font-mono">{activeVariant.sku}</code>
              </p>
            </div>

            {/* Ingredients & Allergen Warnings */}
            <div className="space-y-3 rounded-2xl border bg-card p-5">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground">
                Thành phần &amp; Cảnh báo dị ứng
              </h2>

              {product.allergens.length > 0 ? (
                <div className="rounded-xl border border-amber-300 bg-amber-50 p-3.5 text-sm text-amber-950">
                  <div className="flex items-center gap-2 font-semibold">
                    <AlertTriangle className="h-4 w-4 shrink-0 text-amber-700" />
                    <span>Lưu ý dị ứng: {product.allergens.join(", ")}</span>
                  </div>
                  <ul className="mt-1.5 space-y-0.5 text-xs text-amber-900">
                    {product.allergens.map((code) => (
                      <li key={code}>
                        • <strong>{ALLERGEN_LABELS[code]?.label ?? code}:</strong>{" "}
                        {ALLERGEN_LABELS[code]?.description ?? "Có trong công thức chuẩn."}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3.5 text-sm text-emerald-900">
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-700" />
                  <span>Không chứa các nhóm chất gây dị ứng phổ biến (Sữa bò, Hạt, Đậu nành, Gluten).</span>
                </div>
              )}

              <ul className="grid gap-1.5 text-sm sm:grid-cols-2">
                {product.ingredients.map((ing) => (
                  <li key={ing.code} className="flex items-center justify-between rounded-lg bg-secondary/40 px-3 py-1.5">
                    <span>
                      {ing.name_vi}
                      {ing.is_optional ? " (Tùy chọn)" : ""}
                    </span>
                    {ing.allergen_code && (
                      <Badge variant="warning" className="text-[10px]">
                        {ing.allergen_code}
                      </Badge>
                    )}
                  </li>
                ))}
              </ul>
            </div>

            {/* 2 Primary CTAs */}
            <div className="flex flex-col gap-3 sm:flex-row">
              <Button
                type="button"
                size="lg"
                className="flex-1 gap-2"
                onClick={handleOrderClick}
              >
                <ShoppingBag className="h-4 w-4" />
                Đặt món ngay
              </Button>
              <Button
                type="button"
                size="lg"
                variant="outline"
                className="flex-1 gap-2"
                onClick={() =>
                  openChatWithPrompt(
                    `Mình đang xem ${product.name_vi} (${SIZE_LABELS[activeVariant.size].full}, ${formatVnd(activeVariant.price_vnd)}). Tư vấn giúp mình cách thưởng thức hoặc điều chỉnh vị ngọt/đá phù hợp nhé!`
                  )
                }
              >
                <Sparkles className="h-4 w-4 text-accent" />
                Hỏi Bean AI cách thưởng thức
              </Button>
            </div>
          </div>
        </div>
      </div>

      <OrderQuickModal draft={orderDraft} onClose={() => setOrderDraft(null)} />
    </>
  );
}
