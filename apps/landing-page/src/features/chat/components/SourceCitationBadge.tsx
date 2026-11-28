import { BookOpen, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import type { ChatCitation } from "@/features/chat/types";

interface SourceCitationBadgeProps {
  citations: ChatCitation[];
}

export function SourceCitationBadge({ citations }: SourceCitationBadgeProps) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  if (citations.length === 0) return null;

  return (
    <div className="space-y-1.5 pt-1">
      <div className="flex flex-wrap gap-1.5">
        {citations.map((cit, idx) => {
          const isOpen = expandedIdx === idx;
          return (
            <button
              key={`${cit.source_key}-${idx}`}
              type="button"
              onClick={() => setExpandedIdx(isOpen ? null : idx)}
              className="inline-flex items-center gap-1 rounded-sm border border-border/80 bg-secondary/50 px-2.5 py-0.5 text-[11px] font-medium text-secondary-foreground transition-colors hover:bg-secondary"
            >
              <BookOpen className="h-3 w-3 text-accent" />
              <span className="max-w-[190px] truncate">{cit.title}</span>
              {isOpen ? (
                <ChevronUp className="h-3 w-3" />
              ) : (
                <ChevronDown className="h-3 w-3" />
              )}
            </button>
          );
        })}
      </div>

      {expandedIdx !== null && citations[expandedIdx] && (
        <div className="rounded-lg border bg-background p-2.5 text-[11px] leading-relaxed text-muted-foreground">
          <p className="font-semibold text-foreground">{citations[expandedIdx].section}</p>
          <p className="mt-1">{citations[expandedIdx].snippet}...</p>
        </div>
      )}
    </div>
  );
}
