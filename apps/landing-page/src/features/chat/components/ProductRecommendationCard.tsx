import { ExternalLink, ShoppingBag } from "lucide-react";
import { Link } from "react-router-dom";
import { LazyImage } from "@/components/shared/LazyImage";
import type { OrderDraft } from "@/components/shared/OrderQuickModal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ProductSize, ProductSummary } from "@/lib/api-client";
import { formatVnd, getOrderingAppUrl, SIZE_LABELS } from "@/lib/format";

interface ProductRecommendationCardProps {
  product: ProductSummary;
  preferredSize?: ProductSize;
  onOrderDraft: (draft: OrderDraft) => void;
  onNavigate?: () => void;
}

export function ProductRecommendationCard({
  product,
  preferredSize,
  onOrderDraft,
  onNavigate,
}: ProductRecommendationCardProps) {
  const matchedPreferred = preferredSize
    ? product.variants.find((v) => v.size === preferredSize && v.is_available)
    : undefined;

  const activeVariant =
    matchedPreferred ??
    product.variants.find((v) => v.size === "regular" && v.is_available) ??
    product.variants.find((v) => v.is_available) ??
    product.variants[0];

  const priceBadgeText = matchedPreferred
    ? `${SIZE_LABELS[matchedPreferred.size].full} · ${formatVnd(matchedPreferred.price_vnd)}`
    : product.min_price_vnd === product.max_price_vnd
      ? formatVnd(product.min_price_vnd)
      : `Từ ${formatVnd(product.min_price_vnd)}`;

  const handleOrder = () => {
    if (!activeVariant) return;
    const ext = getOrderingAppUrl(activeVariant.sku, product.slug);
    if (ext) {
      window.open(ext, "_blank", "noopener,noreferrer");
      return;
    }
    onOrderDraft({
      productName: product.name_vi,
      productSlug: product.slug,
      sku: activeVariant.sku,
      size: activeVariant.size,
      temperature: activeVariant.temperature === "hot" ? "hot" : "iced",
      priceVnd: activeVariant.price_vnd,
    });
  };

  return (
    <div className="flex gap-3 rounded-sm border border-border/80 bg-background p-2.5">
      <Link
        to={`/menu/${product.slug}`}
        onClick={onNavigate}
        className="h-16 w-16 shrink-0 overflow-hidden rounded-sm bg-muted"
      >
        <LazyImage
          src={product.image_url}
          alt={product.name_vi}
          width={800}
          height={600}
          className="h-full w-full"
        />
      </Link>

      <div className="flex min-w-0 flex-1 flex-col justify-between">
        <div>
          <div className="flex items-start justify-between gap-2">
            <Link
              to={`/menu/${product.slug}`}
              onClick={onNavigate}
              className="truncate text-xs font-bold text-foreground hover:text-primary"
            >
              {product.name_vi}
            </Link>
            <span className="shrink-0 text-xs font-bold text-primary">
              {" "}
              {priceBadgeText}
            </span>
          </div>
          <div className="mt-1 flex flex-wrap gap-1">
            {!product.has_milk && (
              <Badge variant="success" className="px-1.5 py-0 text-[10px]">
                Không sữa bò
              </Badge>
            )}
            <Badge variant="outline" className="px-1.5 py-0 text-[10px]">
              Đắng {product.bitterness_level}/5
            </Badge>
            <Badge variant="outline" className="px-1.5 py-0 text-[10px]">
              Ngọt {product.sweetness_level}/5
            </Badge>
          </div>
        </div>

        <div className="mt-2 flex items-center gap-1.5">
          <Link
            to={`/menu/${product.slug}`}
            onClick={onNavigate}
            className="inline-flex h-7 items-center gap-1 rounded-md border border-input px-2 text-[11px] font-medium hover:bg-secondary/60"
          >
            <ExternalLink className="h-3 w-3" />
            Chi tiết
          </Link>{" "}
          {activeVariant && (
            <Button
              type="button"
              size="sm"
              className="h-7 gap-1 px-2.5 text-[11px]"
              onClick={handleOrder}
            >
              <ShoppingBag className="h-3 w-3" />
              {matchedPreferred
                ? `Đặt size ${SIZE_LABELS[activeVariant.size].short}`
                : "Đặt món"}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
