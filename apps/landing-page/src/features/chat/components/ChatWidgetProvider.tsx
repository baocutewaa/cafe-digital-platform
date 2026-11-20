import { useCallback, useState, type ReactNode } from "react";
import { ChatWidget } from "@/features/chat/components/ChatWidget";
import { ChatWidgetContext } from "@/features/chat/context/ChatWidgetContext";

export function ChatWidgetProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const [pendingPrompt, setPendingPrompt] = useState("");

  const openChat = useCallback(() => setIsOpen(true), []);
  const openChatWithPrompt = useCallback((prompt: string) => {
    setPendingPrompt(prompt);
    setIsOpen(true);
  }, []);
  const closeChat = useCallback(() => setIsOpen(false), []);
  const clearPendingPrompt = useCallback(() => setPendingPrompt(""), []);

  return (
    <ChatWidgetContext.Provider
      value={{ isOpen, pendingPrompt, openChat, openChatWithPrompt, closeChat }}
    >
      {children}
      <ChatWidget
        isOpen={isOpen}
        pendingPrompt={pendingPrompt}
        onClearPendingPrompt={clearPendingPrompt}
        onOpen={openChat}
        onClose={closeChat}
      />
    </ChatWidgetContext.Provider>
  );
}
