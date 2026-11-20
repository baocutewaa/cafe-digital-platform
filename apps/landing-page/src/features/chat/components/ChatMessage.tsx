import { ThumbsDown, ThumbsUp, Zap } from "lucide-react";
import { Fragment, type ReactNode } from "react";
import type { OrderDraft } from "@/components/shared/OrderQuickModal";
import { Badge } from "@/components/ui/badge";
import { ProductRecommendationCard } from "@/features/chat/components/ProductRecommendationCard";
import { SourceCitationBadge } from "@/features/chat/components/SourceCitationBadge";
import type { ChatMessageItem } from "@/features/chat/types";

interface ChatMessageProps {
  message: ChatMessageItem;
  onFeedback: (localId: string, serverMessageId: string, rating: 1 | -1) => void;
  onOrderDraft: (draft: OrderDraft) => void;
  onNavigate?: () => void;
}

const INLINE_TOKEN_RE = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g;

function renderInlineMarkdown(text: string): ReactNode[] {
  const parts = text.split(INLINE_TOKEN_RE);
  return parts.map((part, idx) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return (
        <strong key={idx} className="font-semibold text-foreground">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      return (
        <code key={idx} className="rounded bg-muted px-1 py-0.5 font-mono text-xs text-primary">
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part.startsWith("*") && part.endsWith("*") && part.length > 2) {
      return (
        <em key={idx} className="italic text-muted-foreground">
          {part.slice(1, -1)}
        </em>
      );
    }
    return <Fragment key={idx}>{part}</Fragment>;
  });
}

function SafeMarkdown({ content }: { content: string }) {
  const lines = content.split("\n");
  return (
    <div className="space-y-1.5 text-sm leading-relaxed">
      {lines.map((rawLine, idx) => {
        const line = rawLine.trim();
        if (!line) return <div key={idx} className="h-1" />;
        if (line.startsWith("- ") || line.startsWith("• ")) {
          return (
            <div key={idx} className="flex gap-2 pl-1">
              <span className="text-accent">•</span>
              <span className="flex-1">{renderInlineMarkdown(line.slice(2))}</span>
            </div>
          );
        }
        return <p key={idx}>{renderInlineMarkdown(line)}</p>;
      })}
    </div>
  );
}

export function ChatMessage({
  message,
  onFeedback,
  onOrderDraft,
  onNavigate,
}: ChatMessageProps) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-primary px-3.5 py-2.5 text-sm text-primary-foreground shadow-sm">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      {/* Product Cards emitted before / alongside text */}
      {message.products && message.products.length > 0 && (
        <div className="space-y-2">
          {message.products.slice(0, 4).map((prod) => (
            <ProductRecommendationCard
              key={prod.id}
              product={prod}
              onOrderDraft={onOrderDraft}
              onNavigate={onNavigate}
            />
          ))}
        </div>
      )}

      {(message.content || message.isStreaming) && (
        <div className="rounded-2xl rounded-tl-sm border bg-card px-3.5 py-3 text-card-foreground shadow-sm">
          {message.content ? (
            <SafeMarkdown content={message.content} />
          ) : (
            <span className="text-xs text-muted-foreground">...</span>
          )}

          {message.citations && message.citations.length > 0 && (
            <div className="mt-2.5 border-t pt-2">
              <SourceCitationBadge citations={message.citations} />
            </div>
          )}

          {!message.isStreaming && (
            <div className="mt-2.5 flex items-center justify-between gap-2 border-t pt-2 text-[11px] text-muted-foreground">
              <div className="flex flex-wrap items-center gap-1.5">
                {message.cached && (
                  <Badge variant="secondary" className="gap-1 px-1.5 py-0 text-[10px]">
                    <Zap className="h-2.5 w-2.5 text-accent" />
                    Trả lời nhanh
                  </Badge>
                )}
                {message.degraded && (
                  <Badge variant="warning" className="px-1.5 py-0 text-[10px]">
                    Tra cứu nhanh
                  </Badge>
                )}
              </div>

              {message.serverMessageId && (
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    aria-label="Hài lòng"
                    onClick={() =>
                      onFeedback(message.id, message.serverMessageId!, 1)
                    }
                    className={`rounded p-1 transition-colors hover:bg-secondary ${
                      message.rating === 1 ? "text-emerald-700" : "text-muted-foreground"
                    }`}
                  >
                    <ThumbsUp className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    aria-label="Chưa hài lòng"
                    onClick={() =>
                      onFeedback(message.id, message.serverMessageId!, -1)
                    }
                    className={`rounded p-1 transition-colors hover:bg-secondary ${
                      message.rating === -1 ? "text-destructive" : "text-muted-foreground"
                    }`}
                  >
                    <ThumbsDown className="h-3.5 w-3.5" />
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
