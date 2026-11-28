import { Calendar, Tag } from "lucide-react";
import { Link } from "react-router-dom";
import { LazyImage } from "@/components/shared/LazyImage";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { PromoCodeCopy } from "@/features/promotion/components/PromoCodeCopy";
import type { Promotion } from "@/lib/api-client";
import { formatVnd } from "@/lib/format";

interface PromotionBannerProps {
  promotion: Promotion;
}

function formatDiscountLabel(promo: Promotion): string {
  if (promo.discount_type === "percentage") {
    return `Giảm ${promo.discount_value}%`;
  }
  if (promo.discount_type === "fixed_amount") {
    return `Giảm ${formatVnd(promo.discount_value)}`;
  }
  return `Tặng ${promo.discount_value} món kèm`;
}

export function PromotionBanner({ promotion }: PromotionBannerProps) {
  const endDate = new Date(promotion.end_at).toLocaleDateString("vi-VN");

  return (
    <Card className="overflow-hidden">
      <div className="grid md:grid-cols-5">
        {promotion.banner_image_url && (
          <div className="aspect-[16/9] bg-muted md:col-span-2 md:aspect-auto">
            <LazyImage
              src={promotion.banner_image_url}
              alt={promotion.title_vi}
              width={1200}
              height={675}
              className="h-full w-full"
            />
          </div>
        )}
        <CardContent className="flex flex-col justify-between space-y-4 p-6 md:col-span-3">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="gap-1 bg-accent text-accent-foreground">
                <Tag className="h-3 w-3" />
                {formatDiscountLabel(promotion)}
              </Badge>
              <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                <Calendar className="h-3.5 w-3.5" />
                Hiệu lực đến {endDate}
              </span>
            </div>

            <h3 className="font-serif text-xl font-medium text-foreground">{promotion.title_vi}</h3>
            <p className="text-sm text-foreground/85">{promotion.summary_vi}</p>
            <p className="rounded-sm border border-border/60 bg-secondary/45 p-3 text-xs leading-relaxed text-muted-foreground">
              <strong className="text-foreground">Điều kiện:</strong> {promotion.conditions_vi}
            </p>
          </div>

          <div className="space-y-3 border-t border-border/60 pt-4">
            {promotion.promo_code && (
              <div className="flex flex-wrap items-center gap-3">
                <span className="text-xs font-medium text-muted-foreground">Mã ưu đãi:</span>
                <PromoCodeCopy code={promotion.promo_code} />
              </div>
            )}

            {promotion.products.length > 0 && (
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-muted-foreground">Món áp dụng:</p>
                <div className="flex flex-wrap gap-1.5">
                  {promotion.products.map((prod) => (
                    <Link
                      key={prod.id}
                      to={`/menu/${prod.slug}`}
                      className="rounded-sm border border-border/80 bg-background px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:border-foreground/50"
                    >
                      {prod.name_vi}
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </div>
    </Card>
  );
}
