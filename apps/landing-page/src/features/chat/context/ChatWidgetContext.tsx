import { createContext, useContext } from "react";

export interface ChatWidgetContextValue {
  isOpen: boolean;
  pendingPrompt: string;
  openChat: () => void;
  openChatWithPrompt: (prompt: string) => void;
  closeChat: () => void;
}

export const ChatWidgetContext = createContext<ChatWidgetContextValue | null>(null);

export function useChatWidget(): ChatWidgetContextValue {
  const ctx = useContext(ChatWidgetContext);
  if (!ctx) {
    throw new Error("useChatWidget must be used within ChatWidgetProvider");
  }
  return ctx;
}
