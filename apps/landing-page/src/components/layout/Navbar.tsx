import { Coffee, Menu, Sparkles, X } from "lucide-react";
import { useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useChatWidget } from "@/features/chat/context/ChatWidgetContext";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { to: "/", label: "Trang chủ", end: true },
  { to: "/menu", label: "Menu", end: false },
  { to: "/about", label: "Câu chuyện", end: true },
  { to: "/promotions", label: "Ưu đãi", end: true },
  { to: "/visit", label: "Chi nhánh", end: true },
];

export function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { openChat } = useChatWidget();

  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link
          to="/"
          className="flex items-center gap-2.5 font-serif text-xl font-bold text-primary"
          onClick={() => setMobileOpen(false)}
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Coffee className="h-5 w-5" />
          </span>
          <span>BREW &amp; BEAN</span>
        </Link>

        <nav
          aria-label="Điều hướng chính"
          className="hidden items-center gap-6 text-sm font-medium md:flex"
        >
          {NAV_LINKS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "transition-colors hover:text-primary",
                  isActive ? "font-semibold text-primary" : "text-muted-foreground"
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <Button
            type="button"
            size="sm"
            variant="secondary"
            className="hidden gap-1.5 sm:inline-flex"
            onClick={openChat}
          >
            <Sparkles className="h-3.5 w-3.5 text-accent" />
            Hỏi Bean AI
          </Button>

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
        <div className="border-t bg-card px-4 py-4 md:hidden">
          <nav aria-label="Điều hướng di động" className="flex flex-col gap-2">
            {NAV_LINKS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  cn(
                    "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-secondary font-semibold text-primary"
                      : "text-muted-foreground hover:bg-secondary/50"
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
            <Button
              type="button"
              size="sm"
              className="mt-2 gap-1.5"
              onClick={() => {
                setMobileOpen(false);
                openChat();
              }}
            >
              <Sparkles className="h-4 w-4" />
              Hỏi Bean AI Barista
            </Button>
          </nav>
        </div>
      )}
    </header>
  );
}
