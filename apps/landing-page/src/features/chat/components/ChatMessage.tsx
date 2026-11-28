import { ThumbsDown, ThumbsUp, Zap } from "lucide-react";
import { Fragment, type ReactNode } from "react";
import type { OrderDraft } from "@/components/shared/OrderQuickModal";
import { Badge } from "@/components/ui/badge";
import { ProductRecommendationCard } from "@/features/chat/components/ProductRecommendationCard";
import { SourceCitationBadge } from "@/features/chat/components/SourceCitationBadge";
import type { ChatMessageItem } from "@/features/chat/types";
import type { ProductSize } from "@/lib/api-client";

interface ChatMessageProps {
  message: ChatMessageItem;
  precedingUserContent?: string;
  onFeedback: (localId: string, serverMessageId: string, rating: 1 | -1) => void;
  onOrderDraft: (draft: OrderDraft) => void;
  onNavigate?: () => void;
}

const INLINE_TOKEN_RE = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g;
const BULLET_LINE_RE = /^([-•*])\s*(.+)$/;
const NUMBERED_LINE_RE = /^(\d+)\.\s+(.+)$/;
const HEADING_LINE_RE = /^#{1,4}\s+(.+)$/;
const STRAY_SECTION_TAG_RE = /^\[[^\]\n]+\]$/;

function inferPreferredSize(userText?: string): ProductSize | undefined {
  if (!userText) return undefined;
  const lower = userText.toLowerCase();
  if (/(?:\bsize\s*s\b|\bsize\s+nhỏ\b|\bnhỏ\s*\(\s*s\s*\)|\(\s*s\s*\)|\bsmall\b)/i.test(lower)) {
    return "small";
  }
  if (/(?:\bsize\s*m\b|\bsize\s+vừa\b|\bvừa\s*\(\s*m\s*\)|\(\s*m\s*\)|\bregular\b)/i.test(lower)) {
    return "regular";
  }
  if (/(?:\bsize\s*l\b|\bsize\s+lớn\b|\blớn\s*\(\s*l\s*\)|\(\s*l\s*\)|\blarge\b)/i.test(lower)) {
    return "large";
  }
  return undefined;
}

function sanitizeIncompleteInlineTokens(line: string): string {
  let cleaned = line;
  const boldCount = (cleaned.match(/\*\*/g) ?? []).length;
  if (boldCount % 2 === 1) {
    const lastIdx = cleaned.lastIndexOf("**");
    cleaned = `${cleaned.slice(0, lastIdx)}${cleaned.slice(lastIdx + 2)}`;
  }
  const tickCount = (cleaned.match(/`/g) ?? []).length;
  if (tickCount % 2 === 1) {
    const lastIdx = cleaned.lastIndexOf("`");
    cleaned = `${cleaned.slice(0, lastIdx)}${cleaned.slice(lastIdx + 1)}`;
  }
  return cleaned;
}

function renderInlineMarkdown(text: string): ReactNode[] {
  const safeText = sanitizeIncompleteInlineTokens(text);
  const parts = safeText.split(INLINE_TOKEN_RE);
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
        const isIndented = /^\s{2,}/.test(rawLine);
        const line = rawLine.trim();
        if (!line) return <div key={idx} className="h-1" />;
        if (STRAY_SECTION_TAG_RE.test(line)) return null;

        const headingMatch = HEADING_LINE_RE.exec(line);
        if (headingMatch) {
          return (
            <p key={idx} className="pt-1 font-semibold text-foreground">
              {renderInlineMarkdown(headingMatch[1])}
            </p>
          );
        }

        const numberedMatch = NUMBERED_LINE_RE.exec(line);
        if (numberedMatch) {
          return (
            <div key={idx} className="flex gap-2 pl-0.5">
              <span className="shrink-0 font-semibold text-accent">{numberedMatch[1]}.</span>
              <span className="flex-1">{renderInlineMarkdown(numberedMatch[2])}</span>
            </div>
          );
        }

        // Distinguish `*italic note*` from `* bullet item`
        const isItalicLine =
          line.startsWith("*") && !line.startsWith("**") && line.endsWith("*") && line.length > 2;
        if (!isItalicLine) {
          const bulletMatch = BULLET_LINE_RE.exec(line);
          if (bulletMatch) {
            return (
              <div key={idx} className={`flex gap-2 ${isIndented ? "pl-4" : "pl-1"}`}>
                <span className="shrink-0 text-accent">{isIndented ? "◦" : "•"}</span>
                <span className="flex-1">{renderInlineMarkdown(bulletMatch[2])}</span>
              </div>
            );
          }
        }

        return <p key={idx}>{renderInlineMarkdown(line)}</p>;
      })}
    </div>
  );
}

export function ChatMessage({
  message,
  precedingUserContent,
  onFeedback,
  onOrderDraft,
  onNavigate,
}: ChatMessageProps) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-sm bg-primary px-3.5 py-2.5 text-sm text-primary-foreground">
          {message.content}
        </div>
      </div>
    );
  }

  const preferredSize = inferPreferredSize(precedingUserContent);

  return (
    <div className="space-y-2.5">
      {/* Product Cards emitted before / alongside text */}
      {message.products && message.products.length > 0 && (
        <div className="space-y-2">
          {message.products.slice(0, 4).map((prod) => (
            <ProductRecommendationCard
              key={prod.id}
              product={prod}
              preferredSize={preferredSize}
              onOrderDraft={onOrderDraft}
              onNavigate={onNavigate}
            />
          ))}
        </div>
      )}

      {(message.content || message.isStreaming) && (
        <div className="rounded-sm border border-border/80 bg-card px-3.5 py-3 text-card-foreground">
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
