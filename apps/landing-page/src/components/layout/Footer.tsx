import { Link } from "react-router-dom";

export function Footer() {
  return (
    <footer className="border-t border-border/80 bg-secondary/35 py-14 text-sm text-muted-foreground">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 sm:grid-cols-3 sm:px-6">
        <div className="space-y-3">
          <div>
            <p className="font-serif text-base font-medium uppercase tracking-[0.14em] text-foreground">
              BREW &amp; BEAN
            </p>
            <p className="mt-1 text-[10px] font-medium uppercase tracking-[0.2em] text-muted-foreground">
              Specialty Coffee &amp; Bean AI
            </p>
          </div>
          <p className="max-w-xs leading-relaxed">
            Hệ thống quán cà phê đặc sản bên vành đai Hồ Tây (Tây Hồ, Hà Nội), tuyển chọn Arabica
            Cầu Đất 1.650m &amp; Robusta Buôn Ma Thuột rang vừa cùng trợ lý Bean AI.
          </p>
        </div>

        <div className="space-y-3">
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-foreground">
            Khám phá
          </p>
          <ul className="space-y-2">
            <li>
              <Link to="/menu" className="transition-colors hover:text-foreground">
                Thực đơn đồ uống &amp; bánh
              </Link>
            </li>
            <li>
              <Link to="/about" className="transition-colors hover:text-foreground">
                Câu chuyện hạt cà phê
              </Link>
            </li>
            <li>
              <Link to="/promotions" className="transition-colors hover:text-foreground">
                Ưu đãi đang áp dụng
              </Link>
            </li>
            <li>
              <Link to="/visit" className="transition-colors hover:text-foreground">
                Chi nhánh &amp; Giờ mở cửa
              </Link>
            </li>
          </ul>
        </div>

        <div className="space-y-3">
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-foreground">
            Liên hệ &amp; Giờ phục vụ
          </p>
          <p>Vành đai Hồ Tây · Quận Tây Hồ, Hà Nội</p>
          <p>Hằng ngày: 07:00 – 22:30 (Flagship Nguyễn Đình Thi)</p>
          <p>
            Hotline:{" "}
            <a href="tel:02437288899" className="font-medium text-foreground hover:underline">
              024 3728 8899
            </a>
          </p>
          <p className="pt-1 text-[11px] uppercase tracking-[0.14em] text-muted-foreground/80">
            Cầu Đất · Buôn Ma Thuột · Hồ Tây Hà Nội
          </p>
        </div>
      </div>
    </footer>
  );
}
