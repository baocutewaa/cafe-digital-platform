import { Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { StoreHour } from "@/lib/api-client";
import { formatShortTime } from "@/lib/format";

interface OpeningStatusBadgeProps {
  isOpenNow: boolean;
  todayHours?: StoreHour | null;
}

export function OpeningStatusBadge({ isOpenNow, todayHours }: OpeningStatusBadgeProps) {
  const timeRange =
    todayHours && !todayHours.is_closed
      ? ` · ${formatShortTime(todayHours.open_time)}–${formatShortTime(todayHours.close_time)}`
      : "";

  return (
    <Badge variant={isOpenNow ? "success" : "warning"} className="gap-1.5">
      <Clock className="h-3 w-3" />
      {isOpenNow ? "Đang mở cửa" : "Đã đóng cửa"}
      {timeRange}
    </Badge>
  );
}
