import { EventStreamContentType, fetchEventSource } from "@microsoft/fetch-event-source";
import { useCallback, useRef, useState } from "react";
import type {
  ChatCitation,
  ChatMessageItem,
  ChatSessionInfo,
  ChatStage,
} from "@/features/chat/types";
import { API_BASE_URL, type ProductSummary } from "@/lib/api-client";

interface UseChatStreamArgs {
  ensureSession: () => Promise<ChatSessionInfo>;
  createNewSession: () => Promise<ChatSessionInfo>;
  updateAiMode: (mode: "online" | "fast_lookup_only") => void;
}

class FatalChatError extends Error {}

export function useChatStream({
  ensureSession,
  createNewSession,
  updateAiMode,
}: UseChatStreamArgs) {
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [stage, setStage] = useState<ChatStage>("idle");
  const [isStreaming, setIsStreaming] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const stopGeneration = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
    setStage("idle");
    setMessages((prev) =>
      prev.map((m) => (m.isStreaming ? { ...m, isStreaming: false } : m))
    );
  }, []);

  const resetMessages = useCallback(() => {
    stopGeneration();
    setMessages([]);
    setErrorMsg(null);
  }, [stopGeneration]);

  const sendMessage = useCallback(
    async (rawContent: string) => {
      const content = rawContent.trim();
      if (!content || isStreaming) return;

      setErrorMsg(null);
      const userId = crypto.randomUUID();
      const assistantLocalId = crypto.randomUUID();
      const clientMessageId = crypto.randomUUID();

      setMessages((prev) => [
        ...prev,
        { id: userId, role: "user", content },
        { id: assistantLocalId, role: "assistant", content: "", isStreaming: true },
      ]);
      setIsStreaming(true);
      setStage("retrieving");

      const controller = new AbortController();
      abortRef.current = controller;

      const executeStream = async (activeSession: ChatSessionInfo, retried = false) => {
        await fetchEventSource(`${API_BASE_URL}/chat/sessions/${activeSession.session_id}/messages`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
            "X-Session-Token": activeSession.session_token,
          },
          body: JSON.stringify({
            content,
            client_message_id: clientMessageId,
          }),
          signal: controller.signal,
          openWhenHidden: true,
          async onopen(response) {
            if (response.status === 401 && !retried) {
              throw new Error("RETRY_SESSION");
            }
            if (!response.ok) {
              let detail = `HTTP ${response.status}`;
              try {
                const errJson = (await response.json()) as { detail?: string };
                if (errJson.detail) detail = errJson.detail;
              } catch {
                // ignore JSON parse failure
              }
              throw new FatalChatError(detail);
            }
            const contentType = response.headers.get("content-type") ?? "";
            if (!contentType.includes(EventStreamContentType)) {
              throw new FatalChatError("Phản hồi từ server không phải SSE stream.");
            }
          },
          onmessage(ev) {
            if (!ev.data) return;
            const parsed = JSON.parse(ev.data) as Record<string, unknown>;

            if (ev.event === "status") {
              const st = parsed.stage as ChatStage | undefined;
              if (st) setStage(st);
            } else if (ev.event === "products") {
              const prods = parsed as unknown as ProductSummary[];
              setMessages((prev) =>
                prev.map((m) => (m.id === assistantLocalId ? { ...m, products: prods } : m))
              );
            } else if (ev.event === "token") {
              const delta = String(parsed.delta ?? "");
              if (delta) {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantLocalId ? { ...m, content: `${m.content}${delta}` } : m
                  )
                );
              }
            } else if (ev.event === "sources") {
              const citations = parsed as unknown as ChatCitation[];
              setMessages((prev) =>
                prev.map((m) => (m.id === assistantLocalId ? { ...m, citations } : m))
              );
            } else if (ev.event === "done") {
              const degraded = Boolean(parsed.degraded);
              if (degraded) {
                updateAiMode("fast_lookup_only");
              } else if (parsed.model && parsed.model !== "lexical-sql-fallback") {
                updateAiMode("online");
              }
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantLocalId
                    ? {
                        ...m,
                        serverMessageId: String(parsed.message_id ?? ""),
                        intent: parsed.intent ? String(parsed.intent) : undefined,
                        model: parsed.model ? String(parsed.model) : null,
                        cached: Boolean(parsed.cached),
                        degraded,
                        isStreaming: false,
                      }
                    : m
                )
              );
            }
          },
          onerror(err) {
            throw err;
          },
        });
      };

      try {
        const activeSession = await ensureSession();
        try {
          await executeStream(activeSession, false);
        } catch (err) {
          if (err instanceof Error && err.message === "RETRY_SESSION") {
            const fresh = await createNewSession();
            await executeStream(fresh, true);
          } else {
            throw err;
          }
        }
      } catch (err) {
        if ((err as Error)?.name === "AbortError") {
          return;
        }
        const message =
          err instanceof FatalChatError || err instanceof Error
            ? err.message
            : "Không thể kết nối tới Bean AI.";
        setErrorMsg(message);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantLocalId && !m.content
              ? {
                  ...m,
                  content: `Xin lỗi, đã có sự cố kết nối: ${message}`,
                  degraded: true,
                  isStreaming: false,
                }
              : m.id === assistantLocalId
                ? { ...m, isStreaming: false }
                : m
          )
        );
      } finally {
        abortRef.current = null;
        setIsStreaming(false);
        setStage("idle");
      }
    },
    [createNewSession, ensureSession, isStreaming, updateAiMode]
  );

  const submitFeedback = useCallback(
    async (localMessageId: string, serverMessageId: string, rating: 1 | -1) => {
      try {
        const activeSession = await ensureSession();
        const resp = await fetch(`${API_BASE_URL}/chat/messages/${serverMessageId}/feedback`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Session-Token": activeSession.session_token,
          },
          body: JSON.stringify({ rating }),
        });
        if (!resp.ok) return;
        setMessages((prev) =>
          prev.map((m) => (m.id === localMessageId ? { ...m, rating } : m))
        );
      } catch {
        // Non-blocking feedback
      }
    },
    [ensureSession]
  );

  return {
    messages,
    stage,
    isStreaming,
    errorMsg,
    sendMessage,
    stopGeneration,
    resetMessages,
    submitFeedback,
  };
}
