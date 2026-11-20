import { useQuery } from "@tanstack/react-query";
import { Sparkles, Tag } from "lucide-react";
import { SeoHead } from "@/components/shared/SeoHead";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useChatWidget } from "@/features/chat/context/ChatWidgetContext";
import { PromotionBanner } from "@/features/promotion/components/PromotionBanner";
import { apiClient } from "@/lib/api-client";

export function PromotionPage() {
  const { openChatWithPrompt } = useChatWidget();

  const promotionsQuery = useQuery({
    queryKey: ["active-promotions"],
    queryFn: apiClient.getActivePromotions,
  });

  const promotions = promotionsQuery.data?.items ?? [];

  return (
    <>
      <SeoHead
        title="Ưu đãi & Khuyến mãi — BREW & BEAN"
        description="Tổng hợp các chương trình ưu đãi, combo sáng, tuần lễ Cold Brew 18h và mã giảm giá đang áp dụng tại BREW & BEAN."
      />

      <div className="mx-auto max-w-6xl space-y-8 px-4 py-10 sm:px-6">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div className="space-y-2">
            <p className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-accent">
              <Tag className="h-3.5 w-3.5" />
              Khuyến mãi đang áp dụng
            </p>
            <h1 className="font-serif text-3xl font-bold sm:text-4xl">
              Ưu đãi đặc biệt tại BREW &amp; BEAN
            </h1>
            <p className="text-sm text-muted-foreground sm:text-base">
              Sao chép mã ưu đãi để sử dụng trực tiếp tại quầy bar ở mọi chi nhánh.
            </p>
          </div>

          <Button
            type="button"
            variant="outline"
            className="gap-2 self-start"
            onClick={() =>
              openChatWithPrompt("Hôm nay BREW & BEAN có mã giảm giá hay combo nào áp dụng cho Cold Brew không?")
            }
          >
            <Sparkles className="h-4 w-4 text-accent" />
            Hỏi Bean AI về ưu đãi
          </Button>
        </div>

        {promotionsQuery.isError ? (
          <Card className="p-6 text-sm text-destructive">
            Không thể tải danh sách khuyến mãi. Vui lòng thử lại sau.
          </Card>
        ) : promotionsQuery.isLoading ? (
          <div className="space-y-6">
            {Array.from({ length: 3 }).map((_, idx) => (
              <Skeleton key={idx} className="h-64 w-full rounded-2xl" />
            ))}
          </div>
        ) : promotions.length === 0 ? (
          <Card className="p-10 text-center text-muted-foreground">
            Hiện chưa có chương trình khuyến mãi nào đang diễn ra.
          </Card>
        ) : (
          <div className="space-y-6">
            {promotions.map((promo) => (
              <PromotionBanner key={promo.id} promotion={promo} />
            ))}
          </div>
        )}
      </div>
    </>
  );
}
