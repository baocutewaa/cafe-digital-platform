import { Check, Copy } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";

interface PromoCodeCopyProps {
  code: string;
}

export function PromoCodeCopy({ code }: PromoCodeCopyProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="inline-flex items-center gap-2 rounded-sm border border-dashed border-foreground/35 bg-secondary/60 px-3 py-1.5">
      <span className="font-mono text-sm font-semibold tracking-wider text-foreground">{code}</span>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="h-7 gap-1 px-2 text-xs"
        onClick={() => void handleCopy()}
        aria-label={`Sao chép mã ${code}`}
      >
        {copied ? (
          <>
            <Check className="h-3.5 w-3.5 text-emerald-700" />
            <span className="text-emerald-700">Đã chép</span>
          </>
        ) : (
          <>
            <Copy className="h-3.5 w-3.5" />
            <span>Sao chép</span>
          </>
        )}
      </Button>
    </div>
  );
}
