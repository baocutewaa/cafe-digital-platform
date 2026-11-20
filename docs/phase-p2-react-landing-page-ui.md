# Giai đoạn P2 — Giao diện React Brand Landing Page trên Local

> **Mục tiêu P2:** Hoàn thiện Design System thương hiệu **BREW & BEAN**, tạo bộ tài nguyên ảnh `.webp` tối ưu và xây dựng trọn vẹn 6 trang Public React kết nối trực tiếp với Storefront API trên `localhost:8000` (hoạt động mượt mà trên Desktop & Mobile kể cả khi tắt Ollama Local).

---

## 1. Design System, Tài nguyên `.webp` & Tiện ích dùng chung

### 1.1. Design System & SEO
- **Bảng màu & Typography (`apps/landing-page/src/index.css`, `tailwind.config.ts`):**
  - Tông chủ đạo Espresso (`--primary: 24 55% 24%`), Warm Cream (`--background: 36 33% 97%`), Caramel Gold (`--accent: 30 65% 44%`).
- **SEO Metadata:**
  - `apps/landing-page/index.html`: Thẻ `meta[name="description"]`, Open Graph (`og:title`, `og:description`, `og:type`).
  - `src/components/shared/SeoHead.tsx`: Tự động cập nhật `document.title` và `meta[name="description"]` cho từng trang.

### 1.2. Bộ 40 ảnh `.webp` tối ưu (`apps/landing-page/public/images/`)
- `products/` (**30 ảnh `.webp`** kích thước `800×600`, khớp 100% đường dẫn `image_url` trong `data/seed/products.json`).
- `stores/` (**3 ảnh `.webp`** kích thước `1200×675`: `nguyen-hue.webp`, `thao-dien.webp`, `vo-van-tan.webp`).
- `promotions/` (**3 ảnh `.webp`** kích thước `1200×675`: `morning-combo.webp`, `cold-brew-10k.webp`, `afternoon-bundle.webp`).
- `hero/` (**4 ảnh `.webp`** kích thước `1200×675`: `brand-hero.webp`, `cau-dat-beans.webp`, `roasting-craft.webp`, `brewing-methods.webp`).
- Component `src/components/shared/LazyImage.tsx`: Hỗ trợ `loading="eager"` / `"lazy"`, `decoding="sync"` / `"async"`, khai báo `width`/`height` cố định chống CLS và fallback khi ảnh lỗi.

### 1.3. API Client, Context & Shared Components
- `src/lib/api-client.ts`: Đầy đủ kiểu dữ liệu TypeScript và các hàm gọi `getHealth`, `getReady`, `getStorefront`, `getStores`, `getStoreBySlug`, `getCategories`, `getProducts(filters)`, `getProductBySlug`, `getActivePromotions`.
- `src/lib/format.ts`: Định dạng tiền tệ `formatVnd`, nhãn size (`S/M/L`), nhiệt độ (`Nóng/Đá`), mức caffeine, giải thích mã dị ứng (`DAIRY`, `NUTS`, `SOY`, `GLUTEN`), nhãn tiện ích chi nhánh, lời chào theo khung giờ (`getTimeOfDayGreeting`), và `getOrderingAppUrl` (ADR-09).
- `src/components/ui/`: `badge.tsx`, `button.tsx`, `card.tsx`, `input.tsx`, `skeleton.tsx`.
- `src/features/chat/context/ChatWidgetContext.tsx` & `src/features/chat/components/ChatWidgetProvider.tsx`:
  - Cung cấp `openChat()` và `openChatWithPrompt(prompt)` cho mọi nút *"Hỏi Bean AI"* trên toàn website.
  - Ở P2, khi bấm vào bất kỳ nút Bean AI nào, panel xem trước sẽ mở với câu hỏi ngữ cảnh được tạo sẵn kèm gợi ý link lọc trực tiếp sang `/menu?...` (sẵn sàng cắm SSE stream khi triển khai P5).
- `src/components/shared/OrderQuickModal.tsx`: Modal đặt nhanh hiển thị SKU, size, nhiệt độ, đơn giá VND, hotline và link sang `/visit` khi biến `VITE_ORDERING_APP_URL` chưa cấu hình (ADR-09).

---

## 2. Cấu trúc Layout & 6 Trang Public (`apps/landing-page/src/`)

- **Layout & Routing:**
  - `src/components/layout/Navbar.tsx`: Sticky header với liên kết active (`NavLink`) tới 5 mục chính, nút *"Hỏi Bean AI"* và menu hamburger responsive trên mobile.
  - `src/components/layout/Footer.tsx`: Footer 3 cột thông tin thương hiệu, đường dẫn nhanh và hotline.
  - `src/app/router.tsx` & `src/app/providers.tsx`: Cấu hình `QueryClientProvider`, `ChatWidgetProvider` và 6 route public:

| Route | Component | Chức năng chính đã triển khai |
|---|---|---|
| `/` | `pages/HomePage.tsx` | • Gọi `warmupBackend()` khi mount.<br>• Hero section với lời chào theo khung giờ, ảnh `brand-hero.webp` ưu tiên tải sớm.<br>• **Interactive Taste Finder:** Chọn chip *Ít đắng / Ngọt dịu / Không caffeine / Không sữa bò / Dưới 45k* → tạo URL lọc `/menu?...` hoặc gửi prompt sang Bean AI.<br>• Signature Drinks grid (từ `/api/v1/storefront`), Brand Craft section, Active Promotions preview & Store Locator preview kèm Skeleton loading. |
| `/menu` | `pages/MenuPage.tsx` | • Kết nối `/api/v1/menu/categories` và `/api/v1/menu/products`.<br>• Bộ lọc `MenuFilters.tsx` đồng bộ 2 chiều với URL search params: danh mục, mức giá (`≤ 40k/45k/50k`), caffeine, *Chỉ Signature*, *Không sữa bò (Dairy-free)*, tag hương vị và ô tìm kiếm debounce 250ms hỗ trợ tiếng Việt không dấu.<br>• `ProductGrid.tsx` & `ProductCard.tsx` (kèm nút *"Hỏi AI"* từng món). |
| `/menu/:slug` | `pages/ProductDetailPage.tsx` | • Breadcrumb điều hướng, ảnh `.webp` & `story_vi`.<br>• `FlavorMeter.tsx`: Thanh trực quan Độ đắng (1–5), Độ ngọt (1–5), badge Caffeine.<br>• Bộ chọn Size (`S/M/L`) & Nhiệt độ (`Nóng/Đá`) cập nhật giá VND, lượng `kcal` và `SKU` theo biến thể.<br>• Danh sách nguyên liệu chi tiết + cảnh báo dị ứng nổi bật (`DAIRY`, `NUTS`, `SOY`, `GLUTEN`) hoặc xác nhận an toàn.<br>• 2 nút CTA: *"Đặt món ngay"* và *"Hỏi Bean AI cách thưởng thức"*. |
| `/about` | `pages/AboutPage.tsx` | • Câu chuyện nông trại Arabica Cầu Đất 1.650m & Robusta Buôn Ma Thuột, triết lý rang vừa theo mẻ nhỏ 12 kg và 3 phương pháp pha chế (Espresso 9 Bar, Cold Brew 18h, V60). |
| `/promotions` | `pages/PromotionPage.tsx` | • Hiển thị danh sách ưu đãi đang hiệu lực qua `PromotionBanner.tsx`, nút sao chép mã `PromoCodeCopy.tsx` (`MORNING20`, `COLDBREW10K`, `CHILLDUO`) và tag sản phẩm áp dụng dẫn tới `/menu/:slug`. |
| `/visit` | `pages/VisitPage.tsx` | • Danh sách 3 chi nhánh từ `/api/v1/stores` qua `StoreCard.tsx` & `OpeningStatusBadge.tsx`: badge *"Đang mở cửa / Đã đóng cửa"* theo giờ thực tế, bảng giờ mở cửa 7 ngày (highlight hôm nay), tiện ích và link Google Maps. |

---

## 3. Kiểm thử & Lỗi đã xử lý trong P2

- **Vấn đề đã sửa:** Khi kiểm thử trình duyệt thực tế, React 18 ghi nhận 1 cảnh báo `React does not recognize the fetchPriority prop on a DOM element` tại `LazyImage.tsx`. Đã gỡ `fetchPriority` khỏi thẻ `<img>` (giữ `loading="eager"` + `decoding="sync"` cho ảnh hero) để console hoàn toàn sạch cảnh báo.
- **Kiểm tra Build & Asset:**
  - `npm run lint`: Exit `0` (0 lỗi, 0 cảnh báo).
  - `npm run build` (`tsc -b && vite build`): Exit `0` (tổng bundle `dist/assets/index-*.js` ~91.63 kB gzip, CSS ~5.34 kB gzip).
  - Kiểm tra đối chiếu 40 file `.webp` trong `public/images/` và `dist/images/`: `Missing assets: []`.
- **Kiểm tra trình duyệt trực tiếp (`http://localhost:5173` ↔ `http://localhost:8000`):**
  - Toàn bộ 6 route tải thành công ở Desktop (`1280×800`) và Mobile (`390×844`), `0` ảnh lỗi, `0` failed network requests, `0` lỗi tràn ngang trên mobile.
  - Đã kiểm chứng Interactive Taste Finder, toggle bộ lọc *Không sữa bò* (`14` → `6` món), đổi size `S/M/L` & modal đặt món, copy mã `COLDBREW10K` và menu mobile hamburger.
- **Backend regression (`services/landing-api`):** `ruff check .` Exit `0`, `pytest -v` Exit `0` (`13 passed`).
