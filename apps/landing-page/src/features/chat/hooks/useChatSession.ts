import { useCallback, useState } from "react";
import { API_BASE_URL } from "@/lib/api-client";
import type { ChatSessionInfo } from "@/features/chat/types";

const STORAGE_KEY = "brew_bean_chat_session_v1";

function loadStoredSession(): ChatSessionInfo | null {
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ChatSessionInfo;
    if (!parsed.session_id || !parsed.session_token) return null;
    if (new Date(parsed.expires_at).getTime() <= Date.now()) {
      window.sessionStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function useChatSession() {
  const [session, setSession] = useState<ChatSessionInfo | null>(() => loadStoredSession());

  const createNewSession = useCallback(async (): Promise<ChatSessionInfo> => {
    const resp = await fetch(`${API_BASE_URL}/chat/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ language: "vi" }),
    });
    if (!resp.ok) {
      throw new Error(`Không thể tạo phiên chat (HTTP ${resp.status})`);
    }
    const data = (await resp.json()) as ChatSessionInfo;
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    setSession(data);
    return data;
  }, []);

  const ensureSession = useCallback(async (): Promise<ChatSessionInfo> => {
    const stored = loadStoredSession();
    if (stored) {
      setSession(stored);
      return stored;
    }
    return createNewSession();
  }, [createNewSession]);

  const clearSession = useCallback(() => {
    window.sessionStorage.removeItem(STORAGE_KEY);
    setSession(null);
  }, []);

  const updateAiMode = useCallback((aiMode: "online" | "fast_lookup_only") => {
    setSession((prev) => {
      if (!prev || prev.ai_mode === aiMode) return prev;
      const updated = { ...prev, ai_mode: aiMode };
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      return updated;
    });
  }, []);

  return {
    session,
    ensureSession,
    createNewSession,
    clearSession,
    updateAiMode,
  };
}
