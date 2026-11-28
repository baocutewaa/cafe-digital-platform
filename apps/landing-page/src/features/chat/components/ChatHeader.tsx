import { Bot, RotateCcw, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface ChatHeaderProps {
  aiMode: "online" | "fast_lookup_only";
  onReset: () => void;
  onClose: () => void;
}

export function ChatHeader({ aiMode, onReset, onClose }: ChatHeaderProps) {
  const isOnline = aiMode === "online";

  return (
    <div className="flex items-center justify-between border-b bg-primary px-4 py-3.5 text-primary-foreground sm:rounded-t-sm">
      <div className="flex items-center gap-2.5">
        <span className="flex h-9 w-9 items-center justify-center rounded-sm bg-accent text-accent-foreground">
          <Bot className="h-5 w-5" />
        </span>
        <div>
          <div className="flex items-center gap-2">
            <h2 className="font-serif text-sm font-medium tracking-wide">Bean AI Barista</h2>
            <Badge
              variant={isOnline ? "success" : "warning"}
              className="px-2 py-0 text-[10px]"
            >
              {isOnline ? "Trực tuyến" : "Tra cứu nhanh"}
            </Badge>
          </div>
          <p className="text-[11px] text-primary-foreground/80">
            Tư vấn Menu · Dị ứng · Pha chế BREW &amp; BEAN
          </p>
        </div>
      </div>

      <div className="flex items-center gap-1">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onReset}
          title="Làm mới cuộc trò chuyện"
          aria-label="Làm mới phiên chat"
          className="h-8 w-8 p-0 text-primary-foreground hover:bg-white/15 hover:text-primary-foreground"
        >
          <RotateCcw className="h-4 w-4" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onClose}
          aria-label="Đóng khung Bean AI"
          className="h-8 w-8 p-0 text-primary-foreground hover:bg-white/15 hover:text-primary-foreground"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
