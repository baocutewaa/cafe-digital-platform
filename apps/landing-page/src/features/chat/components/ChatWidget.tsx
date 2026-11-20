import { MessageCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { OrderQuickModal, type OrderDraft } from "@/components/shared/OrderQuickModal";
import { ChatWindow } from "@/features/chat/components/ChatWindow";
import { useChatSession } from "@/features/chat/hooks/useChatSession";
import { useChatStream } from "@/features/chat/hooks/useChatStream";

interface ChatWidgetProps {
  isOpen: boolean;
  pendingPrompt: string;
  onClearPendingPrompt: () => void;
  onOpen: () => void;
  onClose: () => void;
}

export function ChatWidget({
  isOpen,
  pendingPrompt,
  onClearPendingPrompt,
  onOpen,
  onClose,
}: ChatWidgetProps) {
  const [orderDraft, setOrderDraft] = useState<OrderDraft | null>(null);
  const { session, ensureSession, createNewSession, clearSession, updateAiMode } =
    useChatSession();

  const {
    messages,
    stage,
    isStreaming,
    sendMessage,
    stopGeneration,
    resetMessages,
    submitFeedback,
  } = useChatStream({
    ensureSession,
    createNewSession,
    updateAiMode,
  });

  useEffect(() => {
    if (isOpen && !session) {
      void ensureSession().catch(() => {
        // Session will be created lazily on send if initial ping fails
      });
    }
  }, [ensureSession, isOpen, session]);

  useEffect(() => {
    if (isOpen && pendingPrompt.trim() && !isStreaming) {
      const prompt = pendingPrompt;
      onClearPendingPrompt();
      void sendMessage(prompt);
    }
  }, [isOpen, isStreaming, onClearPendingPrompt, pendingPrompt, sendMessage]);

  const handleReset = () => {
    resetMessages();
    clearSession();
    void createNewSession().catch(() => {
      // Lazy retry on next send
    });
  };

  return (
    <>
      {!isOpen && (
        <button
          type="button"
          onClick={onOpen}
          aria-label="Mở trợ lý Bean AI Barista"
          className="fixed bottom-5 right-5 z-40 inline-flex items-center gap-2.5 rounded-full bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground shadow-lg transition-transform hover:scale-105 hover:bg-primary/95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        >
          <MessageCircle className="h-5 w-5 text-accent" />
          <span className="hidden sm:inline">Hỏi Bean AI Barista</span>
        </button>
      )}

      {isOpen && (
        <ChatWindow
          aiMode={session?.ai_mode ?? "online"}
          messages={messages}
          stage={stage}
          isStreaming={isStreaming}
          onSend={(text) => void sendMessage(text)}
          onStop={stopGeneration}
          onReset={handleReset}
          onClose={onClose}
          onFeedback={(localId, serverId, rating) =>
            void submitFeedback(localId, serverId, rating)
          }
          onOrderDraft={(draft) => setOrderDraft(draft)}
        />
      )}

      <OrderQuickModal draft={orderDraft} onClose={() => setOrderDraft(null)} />
    </>
  );
}
