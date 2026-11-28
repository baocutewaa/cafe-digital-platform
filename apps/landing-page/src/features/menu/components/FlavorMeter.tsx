import { cn } from "@/lib/utils";
import { CAFFEINE_LABELS } from "@/lib/format";
import type { CaffeineLevel } from "@/lib/api-client";

interface FlavorMeterProps {
  bitterness: number;
  sweetness: number;
  caffeineLevel: CaffeineLevel;
  compact?: boolean;
}

function LevelDots({
  label,
  value,
  activeColor,
}: {
  label: string;
  value: number;
  activeColor: string;
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <div className="flex items-center gap-1" aria-label={`${label}: ${value}/5`}>
        {[1, 2, 3, 4, 5].map((step) => (
          <span
            key={step}
            className={cn(
              "h-1.5 w-4 rounded-[1px] transition-colors",
              step <= value ? activeColor : "bg-muted"
            )}
          />
        ))}
        <span className="ml-1.5 text-xs font-medium text-foreground">{value}/5</span>
      </div>
    </div>
  );
}

export function FlavorMeter({
  bitterness,
  sweetness,
  caffeineLevel,
  compact = false,
}: FlavorMeterProps) {
  const caff = CAFFEINE_LABELS[caffeineLevel];
  return (
    <div
      className={cn(
        "space-y-2.5",
        compact ? "text-xs" : "rounded-sm border border-border/80 bg-secondary/35 p-4"
      )}
    >
      <LevelDots label="Độ đắng" value={bitterness} activeColor="bg-primary" />
      <LevelDots label="Độ ngọt" value={sweetness} activeColor="bg-accent" />
      <div className="flex items-center justify-between gap-2 pt-1">
        <span className="text-xs font-medium text-muted-foreground">Caffeine</span>
        <span
          className={cn(
            "inline-flex items-center rounded-sm border px-2 py-0.5 text-[11px] font-medium",
            caff.tone
          )}
        >
          {caff.label}
        </span>
      </div>
    </div>
  );
}
