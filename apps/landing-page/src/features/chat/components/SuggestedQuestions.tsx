import { useQueryClient } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { useLocation } from "react-router-dom";
import type { ProductDetail } from "@/lib/api-client";

interface SuggestedQuestionsProps {
  onSelect: (question: string) => void;
  disabled?: boolean;
}

function humanizeSlug(slug: string): string {
  return slug
    .split("-")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function getQuestionsForPath(pathname: string, activeProductName?: string): string[] {
  if (pathname.startsWith("/menu/")) {
    const label = activeProductName?.trim() || "món này";
    const subject = activeProductName ? `Món ${label}` : "Món này";
    return [
      `${subject} có chứa sữa bò hay chất gây dị ứng nào không?`,
      `Độ đắng và caffeine của ${label} phù hợp uống buổi nào?`,
      `${subject} có thể đổi sang sữa hạt hoặc giảm ngọt được không?`,
    ];
  }
  if (pathname.startsWith("/menu")) {
    return [
      "Đồ uống nào dưới 45k, ít đắng và dễ uống nhất?",
      "Mình bị dị ứng sữa bò (DAIRY) thì uống món nào được?",
      "Buổi tối muộn nên uống món gì để không bị mất ngủ?",
    ];
  }
  if (pathname.startsWith("/promotions")) {
    return [
      "Hôm nay quán có mã giảm giá nào đang áp dụng?",
      "Combo Sáng MORNING20 áp dụng khung giờ và món nào?",
    ];
  }
  if (pathname.startsWith("/visit")) {
    return [
      "Chi nhánh Nguyễn Đình Thi (Hồ Tây) mấy giờ đóng cửa?",
      "Chi nhánh nào có chỗ đậu xe và cho mang thú cưng?",
    ];
  }
  if (pathname.startsWith("/about")) {
    return [
      "Cold Brew ủ lạnh 18h khác gì Espresso pha đá?",
      "Arabica Cầu Đất và Robusta Buôn Ma Thuột khác nhau thế nào?",
    ];
  }
  return [
    "Mình muốn đồ uống ít đắng, béo nhẹ, dưới 50k uống buổi chiều",
    "Caramel Latte size L giá bao nhiêu?",
    "Mình bị dị ứng sữa bò thì uống món nào được?",
    "Cold Brew khác gì Espresso pha đá?",
  ];
}

export function SuggestedQuestions({ onSelect, disabled }: SuggestedQuestionsProps) {
  const { pathname } = useLocation();
  const queryClient = useQueryClient();

  let activeProductName: string | undefined;
  if (pathname.startsWith("/menu/")) {
    const slug = pathname.slice("/menu/".length).split("/")[0]?.trim();
    if (slug) {
      const cached = queryClient.getQueryData<ProductDetail>(["product-detail", slug]);
      activeProductName = cached?.name_vi ?? humanizeSlug(slug);
    }
  }

  const questions = getQuestionsForPath(pathname, activeProductName);

  return (
    <div className="space-y-2">
      <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <Sparkles className="h-3.5 w-3.5 text-accent" />
        Gợi ý câu hỏi nhanh
      </p>
      <div className="flex flex-wrap gap-1.5">
        {questions.map((q) => (
          <button
            key={q}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(q)}
            className="rounded-sm border border-border/80 bg-secondary/45 px-3 py-1.5 text-left text-xs text-foreground transition-colors hover:border-foreground/40 hover:bg-secondary disabled:opacity-50"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
