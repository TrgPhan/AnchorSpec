# S3-UORED: cần bao nhiêu sự cố lỗi thật, có và không có Flow

Ghi ngày 11/11/2026, TRƯỚC khi chạy. UORED đã được dùng nhiều lần (E8, Y, W, V, U); đây là thăm dò, không phải xác nhận độc lập. Flow S3 chưa từng chạy trên UORED.

**Câu hỏi (mentor):** cách thường cần bao nhiêu sự cố lỗi để đạt mức X, cách có Flow cần bao nhiêu? Đơn vị là **số ổ hỏng (sự cố) mỗi loại**, không phải số cửa sổ.

**Dữ liệu:** UORED-VAFCLS 20 ổ (5 vòng trong, 5 ngoài, 5 bi, 5 cách), cảm biến giả lập 1 kHz như E8 (`e8_uored`).
- Ổ đích: 11 cửa sổ khỏe đầu để học; cửa sổ 12 trở đi của tệp khỏe để kiểm tra khỏe; toàn bộ cửa sổ trạng thái lỗi nặng (2) để kiểm tra chính, trạng thái đang phát triển (1) báo phụ.
- Ổ nguồn: 10 cửa sổ không chồng lấn của trạng thái lỗi nặng (cửa sổ 1 s, lấy mỗi cửa sổ thứ hai của chuỗi chồng 50%).

**Ngân sách:** m = 1, 2, 4 ổ nguồn mỗi loại lỗi (4, 8, 16 sự cố). Chọn như đợt Y: hoán vị cố định theo seed, bỏ ổ đích, lấy m ổ đầu mỗi lớp. 20 ổ đích × 3 seed × 3 mức = 180 lượt.

**Nhánh:** `real` (RF học từ khỏe đích + cửa sổ lỗi của ổ nguồn) và `flow` (thêm 10 mẫu Flow S3 mỗi ổ nguồn, mức 0,5, alpha 0,25; codec và mạng chỉ học từ cửa sổ của ổ nguồn đã chọn; điều kiện = one-hot 4 lớp, tốc độ, log RMS khỏe). Biểu diễn chính raw 45 đặc trưng; delta (trừ trung bình 11 cửa sổ khỏe của từng ổ) báo phụ. RF `InvariantClassifier`, `causal_average`, `selective(p, 0)`. Flow trung bình 5 hạt giống lấy mẫu (offset 20261111, 20261106, 1, 2, 3).

**Chỉ số chính:** macro recall 4 lớp lỗi ở trạng thái nặng, theo ổ (trung bình seed) rồi theo lớp. Kèm recall từng lớp, tỉ lệ gán lỗi trên đoạn khỏe kiểm tra, trạng thái đang phát triển.

**Tiêu chí khai báo trước để được nói "Flow giúp cần ít sự cố hơn":** ở m = 1 hoặc m = 2, `flow − real` ≥ +5 điểm với CI 95% bootstrap theo ổ (phân tầng theo lớp, 5.000 lần) không chứa 0, và gán lỗi trên khỏe không tăng quá 2 điểm. Nếu không đạt, báo là không đạt.

Giới hạn: đoạn khỏe kiểm tra cùng tệp với nền; mỗi trạng thái chỉ 10 s; 5 ổ mỗi lớp.
