import { Loader2 } from "lucide-react";
import type { ChatStage } from "@/features/chat/types";

interface TypingAndStageIndicatorProps {
  stage: ChatStage;
}

export function TypingAndStageIndicator({ stage }: TypingAndStageIndicatorProps) {
  if (stage === "idle") return null;

  const label =
    stage === "retrieving"
      ? "Đang tìm trong menu & cẩm nang..."
      : "Bean AI đang pha câu trả lời...";

  return (
    <div className="flex items-center gap-2 px-1 py-1 text-xs text-muted-foreground">
      <Loader2 className="h-3.5 w-3.5 animate-spin text-accent" />
      <span>{label}</span>
    </div>
  );
}
