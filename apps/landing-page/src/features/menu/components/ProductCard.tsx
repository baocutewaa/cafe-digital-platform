import { AlertTriangle, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { LazyImage } from "@/components/shared/LazyImage";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useChatWidget } from "@/features/chat/context/ChatWidgetContext";
import type { ProductSummary } from "@/lib/api-client";
import { CAFFEINE_LABELS, formatVnd, TASTE_TAG_LABELS } from "@/lib/format";

interface ProductCardProps {
  product: ProductSummary;
}

export function ProductCard({ product }: ProductCardProps) {
  const { openChatWithPrompt } = useChatWidget();
  const caff = CAFFEINE_LABELS[product.caffeine_level];
  const priceText =
    product.min_price_vnd === product.max_price_vnd
      ? formatVnd(product.min_price_vnd)
      : `${formatVnd(product.min_price_vnd)} – ${formatVnd(product.max_price_vnd)}`;

  return (
    <Card className="group flex h-full flex-col overflow-hidden transition-colors hover:border-foreground/30">
      <Link to={`/menu/${product.slug}`} className="relative block aspect-[4/3] overflow-hidden bg-muted">
        <LazyImage
          src={product.image_url}
          alt={product.name_vi}
          width={800}
          height={600}
          className="h-full w-full transition-transform duration-500 group-hover:scale-[1.03]"
        />
        <div className="absolute left-3 top-3 flex flex-wrap gap-1.5">
          {product.is_signature && (
            <Badge className="bg-primary/90 text-[10px] uppercase tracking-[0.12em] text-primary-foreground">
              Signature
            </Badge>
          )}
          {!product.has_milk && (
            <Badge variant="success" className="text-[10px]">
              Không sữa bò
            </Badge>
          )}
        </div>
      </Link>

      <CardContent className="flex flex-1 flex-col justify-between gap-4 p-5">
        <div className="space-y-2.5">
          <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
            <span className="text-[10px] font-medium uppercase tracking-[0.16em]">
              {product.category.name_vi}
            </span>
            <span className={`rounded-sm border px-2 py-0.5 text-[10px] font-medium ${caff.tone}`}>
              {caff.label}
            </span>
          </div>

          <Link to={`/menu/${product.slug}`} className="block space-y-0.5">
            <h3 className="font-serif text-lg font-medium leading-snug text-foreground transition-colors group-hover:text-accent">
              {product.name_vi}
            </h3>
            <p className="text-xs text-muted-foreground">{product.name_en}</p>
          </Link>

          <p className="line-clamp-2 text-sm leading-relaxed text-muted-foreground">
            {product.short_description_vi}
          </p>

          <div className="flex flex-wrap gap-1.5 pt-0.5">
            {product.taste_tags.slice(0, 3).map((tag) => (
              <Badge key={tag} variant="secondary" className="text-[11px] font-normal">
                {TASTE_TAG_LABELS[tag] ?? tag}
              </Badge>
            ))}
          </div>

          {product.allergens.length > 0 && (
            <p className="flex items-center gap-1.5 text-xs text-amber-800">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
              <span>Dị ứng: {product.allergens.join(", ")}</span>
            </p>
          )}
        </div>

        <div className="space-y-3 border-t border-border/60 pt-3.5">
          <div className="flex items-baseline justify-between">
            <span className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
              Giá từ
            </span>
            <span className="font-serif text-base font-medium text-foreground">{priceText}</span>
          </div>

          <div className="flex gap-2">
            <Link
              to={`/menu/${product.slug}`}
              className="inline-flex h-9 flex-1 items-center justify-center rounded-sm border border-foreground/20 bg-transparent px-3 text-[11px] font-medium uppercase tracking-[0.12em] text-foreground transition-colors hover:border-foreground hover:bg-secondary/50"
            >
              Xem chi tiết
            </Link>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              className="gap-1.5 text-[11px] uppercase tracking-[0.1em]"
              onClick={() =>
                openChatWithPrompt(
                  `Tư vấn giúp mình về món ${product.name_vi}: vị thế nào và hợp khẩu vị nào?`
                )
              }
            >
              <Sparkles className="h-3.5 w-3.5 text-accent" />
              Hỏi AI
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
