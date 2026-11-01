# Giao thức X8 — kiểm chứng tiên nghiệm rộng ở 6 kHz, ghi trước khi chạy

**Vì sao:** X5 cho thấy tiên nghiệm rộng ở 6 kHz tăng mạnh macro, nhưng không đo báo nhầm và không có đối chứng 1 kHz trong cùng khung. Cấu hình rộng lấy nguyên từ X5, không chỉnh.

**Bốn nhánh:** `1k_cu`, `1k_rong`, `6k_cu`, `6k_rong`. RF 50 cây, 150 mẫu cấy mỗi loại (trong, ngoài), z theo nền của chính máy, 3 seed (11, 29, 47).

**Dữ liệu:** XJTU và UORED (đã dùng ở X5, dùng để so sánh, không phải xác nhận độc lập); HUST 15 "máy" (đã dùng ở X7 cho 1 kHz, chưa từng chạy 6 kHz).

**Chỉ số:** macro hai lớp (trong, ngoài) trên cửa sổ muộn; tỉ lệ cửa sổ kiểm tra bình thường bị gọi lỗi. XJTU, UORED: CI bootstrap theo ổ cho hiệu `6k_rong - 1k_cu`.

**Chỉ tiêu cho `6k_rong` so với `1k_cu`, phải đạt cả ba:**
1. XJTU và UORED: hiệu macro ≥ 0,10 và CI 95% không chứa 0 trên ít nhất một bộ, không bộ nào có hiệu âm.
2. HUST: hiệu macro ≥ 0,05 (không có CI theo ổ độc lập).
3. Báo nhầm của `6k_rong` ≤ 0,10 trên cả ba bộ.

Đạt: đưa cảm biến 6 kHz + tiên nghiệm rộng thành nhánh ưu tiên để kiểm tra trên phần cứng, chưa phải quyết định cuối. Không đạt: giữ cấu hình 1 kHz.

## X9 — khám phá thêm sau khi X8 không đạt chỉ tiêu 3

X8 đo RF thô. X9 đưa `1k_cu` và `6k_rong` qua phễu đã freeze (`decide`, ngưỡng tự động, trung bình 5 cửa sổ như X7), không chỉnh gì thêm. **Đây là phân tích khám phá trên dữ liệu đã thấy, không dùng để lật kết quả X8**; chỉ dùng để quyết định có đáng thử 6 kHz trên phần cứng không.
