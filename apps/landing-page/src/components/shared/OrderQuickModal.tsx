import { MapPin, Phone, ShoppingBag, X } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { formatVnd, SIZE_LABELS, TEMPERATURE_LABELS } from "@/lib/format";
import type { ProductSize, ProductTemperature } from "@/lib/api-client";

export interface OrderDraft {
  productName: string;
  productSlug: string;
  sku: string;
  size: ProductSize;
  temperature: ProductTemperature;
  priceVnd: number;
}

interface OrderQuickModalProps {
  draft: OrderDraft | null;
  onClose: () => void;
}

export function OrderQuickModal({ draft, onClose }: OrderQuickModalProps) {
  if (!draft) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="order-modal-title"
    >
      <div className="w-full max-w-md rounded-2xl border bg-card p-6 shadow-xl">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <ShoppingBag className="h-5 w-5" />
            </span>
            <div>
              <h2 id="order-modal-title" className="text-lg font-semibold">
                Đặt món tại quầy / Chi nhánh
              </h2>
              <p className="text-xs text-muted-foreground">SKU: {draft.sku}</p>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Đóng hộp thoại">
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="mt-4 space-y-2 rounded-xl border bg-secondary/40 p-4 text-sm">
          <div className="flex justify-between gap-2">
            <span className="text-muted-foreground">Sản phẩm</span>
            <span className="font-semibold text-foreground">{draft.productName}</span>
          </div>
          <div className="flex justify-between gap-2">
            <span className="text-muted-foreground">Kích cỡ &amp; Nhiệt độ</span>
            <span className="font-medium">
              {SIZE_LABELS[draft.size].full} · {TEMPERATURE_LABELS[draft.temperature]}
            </span>
          </div>
          <div className="flex justify-between gap-2 border-t pt-2">
            <span className="text-muted-foreground">Đơn giá niêm yết</span>
            <span className="text-base font-bold text-primary">{formatVnd(draft.priceVnd)}</span>
          </div>
        </div>

        <p className="mt-4 text-sm text-muted-foreground">
          Cổng đặt hàng trực tuyến (Ứng dụng 2) đang trong giai đoạn tích hợp. Bạn có thể gọi
          hotline chi nhánh để giữ món trước hoặc ghé quầy gần nhất.
        </p>

        <div className="mt-5 flex flex-col gap-2.5 sm:flex-row">
          <Link
            to="/visit"
            onClick={onClose}
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            <MapPin className="h-4 w-4" />
            Xem chi nhánh &amp; Giờ mở cửa
          </Link>
          <a
            href="tel:02838228899"
            className="inline-flex items-center justify-center gap-2 rounded-md border border-input bg-background px-4 py-2.5 text-sm font-medium transition-colors hover:bg-secondary/60"
          >
            <Phone className="h-4 w-4" />
            028 3822 8899
          </a>
        </div>
      </div>
    </div>
  );
}
