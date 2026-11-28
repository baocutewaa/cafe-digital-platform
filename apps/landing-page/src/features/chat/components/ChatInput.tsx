import { Send, Square } from "lucide-react";
import { useState, type KeyboardEvent } from "react";
import { Button } from "@/components/ui/button";

const MAX_LENGTH = 1000;

interface ChatInputProps {
  isStreaming: boolean;
  onSend: (text: string) => void;
  onStop: () => void;
}

export function ChatInput({ isStreaming, onSend, onStop }: ChatInputProps) {
  const [text, setText] = useState("");

  const handleSubmit = () => {
    const trimmed = text.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setText("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t bg-card p-3 sm:rounded-b-sm">
      <div className="flex items-end gap-2">
        <textarea
          rows={2}
          maxLength={MAX_LENGTH}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Hỏi Bean AI về vị, giá, dị ứng, chi nhánh..."
          aria-label="Nhập câu hỏi cho Bean AI"
          className="max-h-28 min-h-[44px] flex-1 resize-none rounded-sm border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        />

        {isStreaming ? (
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={onStop}
            className="h-10 shrink-0 gap-1.5 px-3"
            aria-label="Dừng trả lời"
          >
            <Square className="h-3.5 w-3.5 fill-current" />
            Dừng
          </Button>
        ) : (
          <Button
            type="button"
            size="sm"
            disabled={!text.trim()}
            onClick={handleSubmit}
            className="h-10 shrink-0 gap-1.5 px-3"
            aria-label="Gửi tin nhắn"
          >
            <Send className="h-4 w-4" />
          </Button>
        )}
      </div>

      <div className="mt-1 flex items-center justify-between px-1 text-[11px] text-muted-foreground">
        <span>Enter để gửi · Shift+Enter xuống dòng</span>
        <span>
          {text.length}/{MAX_LENGTH}
        </span>
      </div>
    </div>
  );
}
