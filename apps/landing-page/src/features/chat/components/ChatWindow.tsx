import type { OrderDraft } from "@/components/shared/OrderQuickModal";
import { ChatHeader } from "@/features/chat/components/ChatHeader";
import { ChatInput } from "@/features/chat/components/ChatInput";
import { ChatMessageList } from "@/features/chat/components/ChatMessageList";
import type { ChatMessageItem, ChatStage } from "@/features/chat/types";

interface ChatWindowProps {
  aiMode: "online" | "fast_lookup_only";
  messages: ChatMessageItem[];
  stage: ChatStage;
  isStreaming: boolean;
  onSend: (text: string) => void;
  onStop: () => void;
  onReset: () => void;
  onClose: () => void;
  onFeedback: (localId: string, serverMessageId: string, rating: 1 | -1) => void;
  onOrderDraft: (draft: OrderDraft) => void;
}

export function ChatWindow({
  aiMode,
  messages,
  stage,
  isStreaming,
  onSend,
  onStop,
  onReset,
  onClose,
  onFeedback,
  onOrderDraft,
}: ChatWindowProps) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Bean AI Barista Chat"
      className="fixed inset-0 z-50 flex flex-col bg-card shadow-2xl sm:inset-auto sm:bottom-6 sm:right-6 sm:h-[620px] sm:max-h-[85vh] sm:w-[420px] sm:rounded-sm sm:border sm:border-border"
    >
      <ChatHeader aiMode={aiMode} onReset={onReset} onClose={onClose} />

      <ChatMessageList
        messages={messages}
        stage={stage}
        isStreaming={isStreaming}
        onSelectSuggestion={onSend}
        onFeedback={onFeedback}
        onOrderDraft={onOrderDraft}
        onNavigate={onClose}
      />

      <ChatInput isStreaming={isStreaming} onSend={onSend} onStop={onStop} />
    </div>
  );
}
