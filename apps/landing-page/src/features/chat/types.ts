import type { ProductSummary } from "@/lib/api-client";

export interface ChatCitation {
  source_key: string;
  title: string;
  category: string;
  section: string;
  snippet: string;
}

export interface ChatSessionInfo {
  session_id: string;
  session_token: string;
  language: "vi" | "en";
  expires_at: string;
  ai_mode: "online" | "fast_lookup_only";
}

export type ChatStage = "idle" | "retrieving" | "generating";

export interface ChatMessageItem {
  id: string;
  serverMessageId?: string;
  role: "user" | "assistant";
  content: string;
  products?: ProductSummary[];
  citations?: ChatCitation[];
  intent?: string;
  model?: string | null;
  cached?: boolean;
  degraded?: boolean;
  isStreaming?: boolean;
  rating?: 1 | -1;
}
