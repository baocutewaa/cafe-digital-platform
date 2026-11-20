import { ExternalLink, ShoppingBag } from "lucide-react";
import { Link } from "react-router-dom";
import { LazyImage } from "@/components/shared/LazyImage";
import type { OrderDraft } from "@/components/shared/OrderQuickModal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ProductSummary } from "@/lib/api-client";
import { formatVnd, getOrderingAppUrl } from "@/lib/format";

interface ProductRecommendationCardProps {
  product: ProductSummary;
  onOrderDraft: (draft: OrderDraft) => void;
  onNavigate?: () => void;
}

export function ProductRecommendationCard({
  product,
  onOrderDraft,
  onNavigate,
}: ProductRecommendationCardProps) {
  const defaultVariant =
    product.variants.find((v) => v.size === "regular" && v.is_available) ??
    product.variants.find((v) => v.is_available) ??
    product.variants[0];

  const handleOrder = () => {
    if (!defaultVariant) return;
    const ext = getOrderingAppUrl(defaultVariant.sku, product.slug);
    if (ext) {
      window.open(ext, "_blank", "noopener,noreferrer");
      return;
    }
    onOrderDraft({
      productName: product.name_vi,
      productSlug: product.slug,
      sku: defaultVariant.sku,
      size: defaultVariant.size,
      temperature: defaultVariant.temperature === "hot" ? "hot" : "iced",
      priceVnd: defaultVariant.price_vnd,
    });
  };

  return (
    <div className="flex gap-3 rounded-xl border bg-background p-2.5 shadow-sm">
      <Link
        to={`/menu/${product.slug}`}
        onClick={onNavigate}
        className="h-16 w-16 shrink-0 overflow-hidden rounded-lg bg-muted"
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
              {formatVnd(product.min_price_vnd)}
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
          </Link>
          {defaultVariant && (
            <Button
              type="button"
              size="sm"
              className="h-7 gap-1 px-2.5 text-[11px]"
              onClick={handleOrder}
            >
              <ShoppingBag className="h-3 w-3" />
              Đặt món
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
