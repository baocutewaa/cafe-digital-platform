import { Bot } from "lucide-react";
import { useEffect, useRef } from "react";
import type { OrderDraft } from "@/components/shared/OrderQuickModal";
import { ChatMessage } from "@/features/chat/components/ChatMessage";
import { SuggestedQuestions } from "@/features/chat/components/SuggestedQuestions";
import { TypingAndStageIndicator } from "@/features/chat/components/TypingAndStageIndicator";
import type { ChatMessageItem, ChatStage } from "@/features/chat/types";

interface ChatMessageListProps {
  messages: ChatMessageItem[];
  stage: ChatStage;
  isStreaming: boolean;
  onSelectSuggestion: (question: string) => void;
  onFeedback: (localId: string, serverMessageId: string, rating: 1 | -1) => void;
  onOrderDraft: (draft: OrderDraft) => void;
  onNavigate?: () => void;
}

export function ChatMessageList({
  messages,
  stage,
  isStreaming,
  onSelectSuggestion,
  onFeedback,
  onOrderDraft,
  onNavigate,
}: ChatMessageListProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, stage]);

  return (
    <div className="flex-1 space-y-4 overflow-y-auto bg-background/60 p-4">
      {messages.length === 0 ? (
        <div className="space-y-5 py-4">
          <div className="rounded-2xl border bg-card p-4 shadow-sm">
            <div className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary">
                <Bot className="h-4 w-4" />
              </span>
              <p className="text-sm font-semibold">Xin chào! Mình là Bean AI Barista</p>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
              Mình có thể gợi ý đồ uống theo khẩu vị, kiểm tra giá từng size S/M/L, lọc món an
              toàn dị ứng (sữa bò, hạt, đậu nành, gluten), tra cứu giờ mở cửa chi nhánh và mã
              khuyến mãi.
            </p>
          </div>

          <SuggestedQuestions onSelect={onSelectSuggestion} disabled={isStreaming} />
        </div>
      ) : (
        <>
          {messages.map((msg) => (
            <ChatMessage
              key={msg.id}
              message={msg}
              onFeedback={onFeedback}
              onOrderDraft={onOrderDraft}
              onNavigate={onNavigate}
            />
          ))}
          <TypingAndStageIndicator stage={stage} />
        </>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
