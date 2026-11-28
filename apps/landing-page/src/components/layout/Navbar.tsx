import { Menu, Sparkles, X } from "lucide-react";
import { useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useChatWidget } from "@/features/chat/context/ChatWidgetContext";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { to: "/", label: "Trang chủ", end: true },
  { to: "/menu", label: "Thực đơn", end: false },
  { to: "/about", label: "Câu chuyện", end: true },
  { to: "/promotions", label: "Ưu đãi", end: true },
  { to: "/visit", label: "Chi nhánh", end: true },
];

function BrandLeafMark() {
  return (
    <svg
      viewBox="0 0 28 28"
      fill="none"
      aria-hidden="true"
      className="h-7 w-7 shrink-0 text-foreground"
    >
      <path
        d="M14 23C14 14 19 8.5 24 6C23.5 13 20 19.5 14 23Z"
        fill="currentColor"
        fillOpacity="0.9"
      />
      <path
        d="M14 23C14 14 9 8.5 4 6C4.5 13 8 19.5 14 23Z"
        fill="currentColor"
        fillOpacity="0.72"
      />
      <path
        d="M14 23C11.8 16.5 11.8 10.5 14 4.5C16.2 10.5 16.2 16.5 14 23Z"
        fill="currentColor"
      />
    </svg>
  );
}

export function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { openChat } = useChatWidget();

  return (
    <header className="sticky top-0 z-40 border-b border-border/70 bg-background/95 backdrop-blur">
      <div className="mx-auto flex h-20 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link
          to="/"
          className="flex shrink-0 items-center gap-2.5 text-foreground transition-opacity hover:opacity-85"
          onClick={() => setMobileOpen(false)}
        >
          <BrandLeafMark />
          <div className="leading-tight">
            <span className="block whitespace-nowrap font-serif text-base font-medium uppercase tracking-[0.14em] text-foreground">
              BREW &amp; BEAN
            </span>
            <span className="hidden whitespace-nowrap text-[9px] font-medium uppercase tracking-[0.18em] text-muted-foreground sm:block">
              Vành đai Hồ Tây · Hà Nội
            </span>
          </div>
        </Link>

        <nav
          aria-label="Điều hướng chính"
          className="hidden items-center gap-5 lg:gap-7 md:flex"
        >
          {NAV_LINKS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "whitespace-nowrap border-b py-1 text-[11px] font-medium uppercase tracking-[0.15em] transition-colors",
                  isActive
                    ? "border-foreground text-foreground"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={openChat}
            className="hidden whitespace-nowrap items-center gap-2 rounded-sm border border-foreground/25 bg-transparent px-4 py-2 text-[11px] font-medium uppercase tracking-[0.15em] text-foreground transition-colors hover:border-foreground hover:bg-primary hover:text-primary-foreground sm:inline-flex"
          >
            <Sparkles className="h-3.5 w-3.5 text-accent" />
            Hỏi Bean AI
          </button>

          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="md:hidden"
            onClick={() => setMobileOpen((prev) => !prev)}
            aria-label={mobileOpen ? "Đóng menu" : "Mở menu"}
            aria-expanded={mobileOpen}
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>
      </div>

      {mobileOpen && (
        <div className="border-t border-border/80 bg-background px-4 py-4 md:hidden">
          <nav aria-label="Điều hướng di động" className="flex flex-col gap-1">
            {NAV_LINKS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  cn(
                    "rounded-sm px-3 py-2.5 text-xs font-medium uppercase tracking-[0.16em] transition-colors",
                    isActive
                      ? "bg-secondary text-foreground"
                      : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
            <Button
              type="button"
              size="sm"
              className="mt-3 gap-2 text-[11px] uppercase tracking-[0.15em]"
              onClick={() => {
                setMobileOpen(false);
                openChat();
              }}
            >
              <Sparkles className="h-3.5 w-3.5" />
              Hỏi Bean AI Barista
            </Button>
          </nav>
        </div>
      )}
    </header>
  );
}
