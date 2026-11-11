# S3-Delta: Flow phần dư kết hợp căn chỉnh theo nền khỏe

Ghi ngày 11/11/2026, TRƯỚC khi chạy. Thăm dò trên XJTU đã xem nhiều lần; không phải xác nhận độc lập.

**Câu hỏi:** delta (T external) và Flow phần dư (S3) mỗi thứ cải thiện riêng; ghép lại có cộng dồn không?

**Giữ nguyên S3:** 13 ổ XJTU, LOBO, seed 11/29/47; 5 đoạn khỏe đầu của ổ đích để học, 6–10 để kiểm tra; 10 đoạn cuối đời mỗi ổ nguồn; codec và Flow như `s3_curve.py` ở k = 10; 10 mẫu sinh mỗi ổ nguồn, mức 0,5, alpha 0,25; RF `InvariantClassifier`; `causal_average`; `selective(p, 0)`.

**Delta** (như `t_external.py`): đặc trưng của mỗi ổ trừ trung bình 5 đoạn khỏe đầu của chính ổ đó; mẫu sinh trừ trung bình khỏe của ổ nguồn; không chia độ lệch chuẩn.

**Bốn nhánh:** `real_raw`, `flow_raw`, `real_delta`, `flow_delta`.

**Hạt giống lấy mẫu:** 5 giá trị cố định, offset 20261111, 20261106, 1, 2, 3. Nhánh Flow báo **trung bình 5 hạt giống** (chỉ số chính) và khoảng min–max. Mạng Flow chỉ huấn luyện một lần mỗi lượt.

**So sánh chính, khai báo trước:**
1. `flow_delta` so với `real_raw` (mốc S3 cũ).
2. `flow_delta` so với `real_delta` (tách phần do Flow).

**Chỉ số:**
- Macro recall 3 lớp lỗi ở đoạn cuối đời, theo ổ rồi theo lớp (như con số 77,22%).
- Recall vòng cách.
- Tỉ lệ gán lỗi trên đoạn khỏe.
- Avg precision, avg recall, accuracy 4 lớp (healthy + terminal, như `Method_metrics.csv`).
- CI 95% bootstrap theo ổ, phân tầng theo lớp, 5.000 lần.

Không chọn hạt giống hay nhánh theo điểm test. Báo đủ cả bốn nhánh, kể cả nhánh âm. Hai ổ vòng cách là giới hạn chính.
