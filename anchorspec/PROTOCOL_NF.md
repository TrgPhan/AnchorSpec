# NF: đặc trưng tương đối theo máy + Flow, nhằm thắng `hier`

Ghi ngày 13/11/2026, **trước khi chạy** (đã chạy thử 4 lượt: pba KA01/KI03/KA05, UORED 12). Lần thử thứ 3 sau FF và S2R; cả hai không qua bước phát triển, nên **chưa có lần nhìn nào vào Paderborn thật hay HUST**.

## Phương pháp
- **Đặc trưng tương đối theo máy:** mọi hàng (sự cố thư viện, mẫu cấy vật lý, mẫu Flow, cửa sổ kiểm tra) đều trừ trung bình đặc trưng khỏe của chính máy đó.
  - `m`: chỉ trừ trung bình.
  - `z`: trừ trung bình rồi chia độ lệch chuẩn khỏe, có sàn.
- **Flow:** mạng `ResidualGenerator` của S3, flow matching, có điều kiện theo loại lỗi. Học trên delta tương đối của mọi sự cố thư viện; sinh 150 mẫu mỗi loại; đưa vào **tầng 1** với 25% khối lượng mỗi lớp lỗi. Tầng 2 = thật + vật lý 25% (đã chuẩn hóa).
- **Đối chứng:**
  - `normm`, `normz`: chỉ chuẩn hóa, không có Flow.
  - `*_boot_t1`: delta thật lấy ngẫu nhiên thay cho Flow.

## Phát triển
`pba` (12 ổ Paderborn nhân tạo, m = 1, 2), UORED (m = 1, 2), XJTU (tự nhiên), 8 seed.

**Quy tắc khóa** (chỉ các nhánh có Flow: `normm_flow_t1`, `normz_flow_t1`):
1. Loại nhánh nếu có lớp nào, ở bộ nào, recall thấp hơn `hier` quá 3 điểm.
2. Chọn nhánh có trung bình Δ Avg Recall (so với `hier`) trên ba bộ cao nhất, với điều kiện > 0.
3. Không nhánh nào đạt thì không kiểm chứng.

## Kiểm chứng (một lần)
Paderborn hỏng thật (m = 1, 2, 4) + HUST (m = 1, 2, 3), 8 seed. Nhánh: `hier`, nhánh khóa, nhánh chỉ chuẩn hóa tương ứng, nhánh bootstrap tương ứng.

**THẮNG** nếu cả ba điều sau đúng (giống PROTOCOL_S2R.md):
- (a) trung bình Δ > 0 trên cả hai bộ;
- (b) ít nhất một mức có CI 95% > 0;
- (c) không mức nào có Δ < −2.

Báo riêng phần do chuẩn hóa và phần do Flow.
