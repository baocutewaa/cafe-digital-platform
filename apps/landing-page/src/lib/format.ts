import type { CaffeineLevel, ProductSize, ProductTemperature } from "@/lib/api-client";

export function formatVnd(amount: number): string {
  return `${new Intl.NumberFormat("vi-VN").format(amount)}đ`;
}

export function formatShortTime(rawTime: string): string {
  return rawTime.slice(0, 5);
}

export const SIZE_LABELS: Record<ProductSize, { short: string; full: string }> = {
  small: { short: "S", full: "Nhỏ (S)" },
  regular: { short: "M", full: "Vừa (M)" },
  large: { short: "L", full: "Lớn (L)" },
};

export const TEMPERATURE_LABELS: Record<ProductTemperature, string> = {
  hot: "Nóng",
  iced: "Đá",
  both: "Nóng / Đá",
};

export const CAFFEINE_LABELS: Record<CaffeineLevel, { label: string; tone: string }> = {
  none: { label: "Không caffeine", tone: "bg-emerald-50 text-emerald-800 border-emerald-200" },
  low: { label: "Caffeine nhẹ", tone: "bg-sky-50 text-sky-800 border-sky-200" },
  medium: { label: "Caffeine vừa", tone: "bg-amber-50 text-amber-800 border-amber-200" },
  high: { label: "Caffeine đậm", tone: "bg-stone-100 text-stone-800 border-stone-300" },
};

export const ALLERGEN_LABELS: Record<string, { label: string; description: string }> = {
  DAIRY: { label: "Sữa bò (Dairy)", description: "Chứa sữa tươi, sữa đặc, bơ hoặc kem phô mai." },
  NUTS: { label: "Các loại hạt (Nuts)", description: "Chứa hạnh nhân, macca hoặc hạt phỉ." },
  SOY: { label: "Đậu nành (Soy)", description: "Chứa chế phẩm từ đậu nành." },
  GLUTEN: { label: "Gluten", description: "Chứa bột mì hoặc ngũ cốc có gluten." },
};

export const TASTE_TAG_LABELS: Record<string, string> = {
  sweet: "Ngọt dịu",
  creamy: "Béo mịn",
  less_bitter: "Ít đắng",
  fruity: "Hương trái cây",
  refreshing: "Thanh mát",
  bold: "Đậm vị",
  floral: "Hương hoa",
  nutty: "Bùi béo hạt",
  chocolatey: "Vị cacao",
  caramel: "Caramel",
  salted_caramel: "Kem muối",
  tea_forward: "Đậm vị trà",
  coconut: "Cốt dừa",
  dairy_free: "Không sữa bò",
  buttery: "Thơm bơ Pháp",
  balanced: "Cân bằng",
};

export const DAY_NAMES_VI = [
  "Thứ Hai",
  "Thứ Ba",
  "Thứ Tư",
  "Thứ Năm",
  "Thứ Sáu",
  "Thứ Bảy",
  "Chủ Nhật",
];

export const AMENITY_LABELS: Record<string, string> = {
  wifi: "Wi-Fi tốc độ cao",
  parking: "Chỗ đậu xe",
  ac: "Máy lạnh",
  work_friendly: "Phù hợp làm việc",
  power_outlets: "Nhiều ổ cắm điện",
  pour_over_bar: "Quầy Pour-over",
  outdoor_garden: "Sân vườn thoáng mát",
  pet_friendly: "Thân thiện thú cưng",
  quiet_zone: "Khu vực yên tĩnh",
  meeting_table: "Bàn họp nhóm",
};

export function getOrderingAppUrl(sku: string, productSlug: string): string | null {
  const base = (import.meta.env.VITE_ORDERING_APP_URL || "").trim().replace(/\/+$/, "");
  if (!base) return null;
  const search = new URLSearchParams({ product: productSlug, sku });
  return `${base}/order?${search.toString()}`;
}

export function getTimeOfDayGreeting(): { title: string; suggestion: string } {
  const hour = new Date().getHours();
  if (hour < 11) {
    return {
      title: "Chào buổi sáng năng lượng",
      suggestion: "Bắt đầu ngày mới với Cà Phê Muối Cầu Đất hoặc Croissant Bơ Pháp.",
    };
  }
  if (hour < 17) {
    return {
      title: "Buổi chiều tỉnh táo nhẹ nhàng",
      suggestion: "Thử Cold Brew Cam Sả thanh mát hoặc Matcha Latte Uji ít caffeine.",
    };
  }
  return {
    title: "Buổi tối thư giãn êm dịu",
    suggestion: "Khám phá Trà Hibiscus Dâu Tằm hoặc Cacao Sữa Dừa không caffeine.",
  };
}
