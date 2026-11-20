import { Coffee } from "lucide-react";
import { Link } from "react-router-dom";

export function Footer() {
  return (
    <footer className="border-t bg-secondary/45 py-12 text-sm text-muted-foreground">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 sm:grid-cols-3 sm:px-6">
        <div className="space-y-3">
          <div className="flex items-center gap-2 font-serif text-lg font-bold text-primary">
            <Coffee className="h-5 w-5" />
            <span>BREW &amp; BEAN</span>
          </div>
          <p className="leading-relaxed">
            Cà phê đặc sản từ nông trại Arabica Cầu Đất 1.650m và Robusta Buôn Ma Thuột rang vừa,
            kết hợp trợ lý Barista Bean AI tư vấn khẩu vị chuẩn xác.
          </p>
        </div>

        <div className="space-y-2.5">
          <p className="font-semibold text-foreground">Khám phá</p>
          <ul className="space-y-1.5">
            <li>
              <Link to="/menu" className="hover:text-primary hover:underline">
                Thực đơn đồ uống &amp; bánh
              </Link>
            </li>
            <li>
              <Link to="/about" className="hover:text-primary hover:underline">
                Câu chuyện hạt cà phê
              </Link>
            </li>
            <li>
              <Link to="/promotions" className="hover:text-primary hover:underline">
                Ưu đãi đang áp dụng
              </Link>
            </li>
            <li>
              <Link to="/visit" className="hover:text-primary hover:underline">
                Chi nhánh &amp; Giờ mở cửa
              </Link>
            </li>
          </ul>
        </div>

        <div className="space-y-2.5">
          <p className="font-semibold text-foreground">Liên hệ &amp; Giờ phục vụ</p>
          <p>Hằng ngày: 07:00 – 22:30 (Flagship Nguyễn Huệ)</p>
          <p>
            Hotline:{" "}
            <a href="tel:02838228899" className="font-medium text-foreground hover:underline">
              028 3822 8899
            </a>
          </p>
          <p className="text-xs">Hệ sinh thái cafe-digital-platform · Local-First (No-Docker)</p>
        </div>
      </div>
    </footer>
  );
}
