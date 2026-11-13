# FUSION: giữ Flow trong pipeline, ghép với cấy lỗi vật lý

Ghi ngày 12/11/2026, **trước khi chạy**. Đã xem: mọi kết quả Flow (S3, PB-Flow, công thức Trường, đường cong + photocopy), PB-INJ, HUST HIER, PB-HIER. Chưa xem bất kỳ con số ghép nào.

## Mục đích

Flow đã được báo cáo nên cần giữ trong pipeline. Câu hỏi: có cách ghép nào mà Flow (a) không làm kém kiến trúc đã chốt (hai tầng + cấy lỗi), và (b) có đóng góp riêng đo được?

## Các nhánh (đều chấm "chỉ chọn loại lỗi", trên nền kiến trúc hai tầng đã khóa)

- `hier`: kiến trúc chốt (mốc so sánh).
- `real`: chỉ sự cố thật, RF 500 cây (mốc cũ).
- **`f_neo` (nhánh chính):** Flow học từ sự cố thật (như S3), nhưng sinh biến thể **quanh mẫu cấy lỗi trên nền khỏe của máy đích**: mỗi mẫu cấy có thêm 1 biến thể Flow (độ mạnh 0,5). Tầng 2 dùng 150 mẫu cấy + 150 biến thể, tổng vẫn 25% trọng số. Tầng 1 không đổi.
- `f_t1`: Flow theo đúng công thức Trường (mỗi cửa sổ thật 1 mẫu, trọng số 0,25 cộng thêm) cho sự cố thật ở **tầng 1**. Tầng 2 không đổi.
- `f_t1_copy`: như `f_t1` nhưng thay mẫu Flow bằng photocopy cửa sổ thật (đối chứng).
- `f_par`: chạy song song `hier` và mô hình S3 (RF 500 cây, thật + Flow theo công thức Trường), lấy trung bình xác suất.

## Dữ liệu

- Paderborn: như `PROTOCOL_PB_HIER.md` (11 ổ hỏng thật, m = 1, 2, 4, 8 seed).
- HUST: như `PROTOCOL_HIER.md` (14 ổ, m = 1, 2, 3, cùng 8 seed). Cửa sổ của sự cố nguồn dựng lại bằng cùng hàm mô phỏng cảm biến và cùng hạt giống.
- Flow: 2.000 bước, một hạt giống lấy mẫu mỗi lượt.

## Tiêu chí (cho từng nhánh ghép so với `hier`, macro theo lớp, bootstrap theo ổ)

- **Giữ được:** ở mọi mức của cả hai bộ, chênh ≥ −1,0 điểm và cận dưới CI 95% > −3,0 điểm.
- **Có đóng góp:** đạt "giữ được", và ít nhất một mức có chênh ≥ +2,0 điểm với CI 95% không chứa 0.
- Với `f_t1`: đóng góp riêng của Flow đọc từ `f_t1 − f_t1_copy`.

Nhánh chính là `f_neo`; ba nhánh còn lại là phụ, báo đủ, không chọn lại sau khi xem.
