import { Coffee } from "lucide-react";
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";

export function Navbar() {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link to="/" className="flex items-center gap-2.5 font-serif text-xl font-bold text-primary">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Coffee className="h-5 w-5" />
          </span>
          <span>BREW &amp; BEAN</span>
        </Link>

        <nav className="hidden items-center gap-6 text-sm font-medium text-muted-foreground md:flex">
          <Link to="/" className="text-foreground transition-colors hover:text-primary">
            Trang chủ
          </Link>
          <span className="cursor-not-allowed opacity-60" title="Sắp ra mắt ở Giai đoạn P2">
            Menu
          </span>
          <span className="cursor-not-allowed opacity-60" title="Sắp ra mắt ở Giai đoạn P2">
            Câu chuyện
          </span>
          <span className="cursor-not-allowed opacity-60" title="Sắp ra mắt ở Giai đoạn P2">
            Ưu đãi
          </span>
          <span className="cursor-not-allowed opacity-60" title="Sắp ra mắt ở Giai đoạn P2">
            Chi nhánh
          </span>
        </nav>

        <Badge variant="secondary">P0 Walking Skeleton</Badge>
      </div>
    </header>
  );
}
