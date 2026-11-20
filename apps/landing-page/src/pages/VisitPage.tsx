import { useQuery } from "@tanstack/react-query";
import { MapPin, Sparkles } from "lucide-react";
import { SeoHead } from "@/components/shared/SeoHead";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useChatWidget } from "@/features/chat/context/ChatWidgetContext";
import { StoreCard } from "@/features/store/components/StoreCard";
import { apiClient } from "@/lib/api-client";

export function VisitPage() {
  const { openChatWithPrompt } = useChatWidget();

  const storesQuery = useQuery({
    queryKey: ["stores-list"],
    queryFn: apiClient.getStores,
  });

  const stores = storesQuery.data?.items ?? [];

  return (
    <>
      <SeoHead
        title="Chi nhánh & Giờ mở cửa — BREW & BEAN"
        description="Địa chỉ, giờ mở cửa theo ngày, trạng thái đang mở cửa và tiện ích Wi-Fi, chỗ đậu xe tại các chi nhánh BREW & BEAN TP. Hồ Chí Minh."
      />

      <div className="mx-auto max-w-6xl space-y-8 px-4 py-10 sm:px-6">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div className="space-y-2">
            <p className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-accent">
              <MapPin className="h-3.5 w-3.5" />
              Hệ thống cửa hàng TP. Hồ Chí Minh
            </p>
            <h1 className="font-serif text-3xl font-bold sm:text-4xl">
              Ghé thăm không gian BREW &amp; BEAN
            </h1>
            <p className="text-sm text-muted-foreground sm:text-base">
              Trạng thái mở cửa được cập nhật tự động theo giờ địa phương (UTC+7).
            </p>
          </div>

          <Button
            type="button"
            variant="outline"
            className="gap-2 self-start"
            onClick={() =>
              openChatWithPrompt("Chi nhánh BREW & BEAN nào yên tĩnh, có ổ cắm điện và chỗ đậu xe?")
            }
          >
            <Sparkles className="h-4 w-4 text-accent" />
            Hỏi Bean AI chọn chi nhánh
          </Button>
        </div>

        {storesQuery.isError ? (
          <Card className="p-6 text-sm text-destructive">
            Không thể tải danh sách chi nhánh. Vui lòng thử lại sau.
          </Card>
        ) : storesQuery.isLoading ? (
          <div className="grid gap-6 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, idx) => (
              <Skeleton key={idx} className="h-[460px] w-full rounded-2xl" />
            ))}
          </div>
        ) : (
          <div className="grid gap-6 lg:grid-cols-3">
            {stores.map((store) => (
              <StoreCard key={store.id} store={store} showFullSchedule />
            ))}
          </div>
        )}
      </div>
    </>
  );
}
