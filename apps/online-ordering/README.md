# Ứng dụng 2 — Online Ordering Website (`apps/online-ordering`)

> **Hệ sinh thái:** `cafe-digital-platform`  
> **Trạng thái:** Khởi tạo cấu trúc Multi-App (Triển khai sau khi hoàn tất Ứng dụng 1 — Brand Landing Page & Bean AI RAG)

## Mục tiêu
- Đặt đồ uống trực tuyến theo `sku` và `product.slug` được liên kết từ Ứng dụng 1 (`VITE_ORDERING_APP_URL/order?product=<slug>`).
- Tùy chọn size (`small`, `regular`, `large`), nhiệt độ (`hot`, `iced`), mức đường/đá, giỏ hàng và thanh toán.
- Sử dụng chung nguồn dữ liệu chuẩn PostgreSQL 17 (`stores`, `products`, `product_variants`, `promotions`).
