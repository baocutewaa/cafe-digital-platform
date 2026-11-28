import { ExternalLink, MapPin, Phone } from "lucide-react";
import { LazyImage } from "@/components/shared/LazyImage";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { OpeningStatusBadge } from "@/features/store/components/OpeningStatusBadge";
import type { Store } from "@/lib/api-client";
import { AMENITY_LABELS, DAY_NAMES_VI, formatShortTime } from "@/lib/format";

interface StoreCardProps {
  store: Store;
  showFullSchedule?: boolean;
}

export function StoreCard({ store, showFullSchedule = true }: StoreCardProps) {
  const todayIndex = (new Date().getDay() + 6) % 7; // Convert JS Sunday=0 -> Monday=0

  return (
    <Card className="flex h-full flex-col overflow-hidden">
      {store.image_url && (
        <div className="aspect-[16/9] bg-muted">
          <LazyImage
            src={store.image_url}
            alt={store.name}
            width={1200}
            height={675}
            className="h-full w-full"
          />
        </div>
      )}

      <CardContent className="flex flex-1 flex-col justify-between space-y-4 p-6">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            {store.district && <Badge variant="secondary">{store.district}</Badge>}
            <OpeningStatusBadge isOpenNow={store.is_open_now} todayHours={store.today_hours} />
          </div>

          <h3 className="font-serif text-xl font-medium text-foreground">{store.name}</h3>

          <p className="flex items-start gap-2 text-sm text-muted-foreground">
            <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
            <span>{store.address}</span>
          </p>

          {store.phone && (
            <p className="flex items-center gap-2 text-sm">
              <Phone className="h-4 w-4 shrink-0 text-accent" />
              <a href={`tel:${store.phone.replace(/\s+/g, "")}`} className="font-medium hover:underline">
                {store.phone}
              </a>
            </p>
          )}

          {store.amenities.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {store.amenities.map((item) => (
                <Badge key={item} variant="outline" className="text-[11px] font-normal">
                  {AMENITY_LABELS[item] ?? item}
                </Badge>
              ))}
            </div>
          )}

          {showFullSchedule && store.hours.length > 0 && (
            <div className="rounded-sm border border-border/70 bg-secondary/35 p-3.5 text-xs">
              <p className="mb-2 text-[10px] font-medium uppercase tracking-[0.16em] text-foreground">
                Giờ mở cửa trong tuần
              </p>
              <ul className="space-y-1">
                {store.hours.map((h) => {
                  const isToday = h.day_of_week === todayIndex;
                  return (
                    <li
                      key={h.day_of_week}
                      className={`flex justify-between ${
                        isToday ? "font-semibold text-primary" : "text-muted-foreground"
                      }`}
                    >
                      <span>
                        {DAY_NAMES_VI[h.day_of_week] ?? `Ngày ${h.day_of_week}`}
                        {isToday ? " (Hôm nay)" : ""}
                      </span>
                      <span>
                        {h.is_closed
                          ? "Nghỉ"
                          : `${formatShortTime(h.open_time)} – ${formatShortTime(h.close_time)}`}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </div>

        {store.google_maps_url && (
          <a
            href={store.google_maps_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-sm border border-foreground/20 bg-transparent px-4 text-[11px] font-medium uppercase tracking-[0.14em] text-foreground transition-colors hover:border-foreground hover:bg-secondary/50"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Chỉ đường trên Google Maps
          </a>
        )}
      </CardContent>
    </Card>
  );
}
