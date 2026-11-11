# Kiểm tra kết quả S3 curve (11/11/2026)

Chạy đủ 156/156 lượt (4 mức k × 13 ổ × 3 seed), không có lỗi. Máy: WSL, CPU, 6 worker, mỗi lượt 1 luồng. Dữ liệu tải lại bằng `u_download.py` (390 CSV, kiểm tra CRC) và `u_natural.py prepare`.

## Đối chiếu k = 10 với `results/priorities/Method_metrics.csv` (healthy_terminal)

| | Avg Precision | Avg Recall | Accuracy |
|---|---|---|---|
| real, k = 10 | 86,89% (khớp tuyệt đối) | 76,25% (khớp) | 89,91% (khớp) |
| flow, k = 10 | 95,65% (cũ 95,70%, −0,05) | 81,94% (cũ 82,92%, −0,98) | 91,97% (cũ 92,48%, −0,51) |

Flow lệch dưới 1 điểm, nằm trong mức ±2 chấp nhận được theo handoff (do cách chọn anchor và seed lấy mẫu khác).

## Chênh lệch Flow − chỉ mẫu thật, CI 95% bootstrap theo ổ (phân tầng theo lớp, 2.000 lần)

| k | Avg Precision | Avg Recall | Accuracy |
|---:|---|---|---|
| 2 | +18,2 [−0,5; +27,2] | +3,0 [−3,8; +9,8] | +1,2 [−2,2; +4,6] |
| 3 | +13,8 [−1,0; +22,7] | +1,2 [−6,3; +8,6] | −0,3 [−3,8; +3,1] |
| 5 | +0,2 [−0,2; +0,8] | +0,1 [−1,3; +1,4] | +0,0 [−0,9; +0,7] |
| 10 | +8,8 [−1,0; +12,2] | +5,7 [−2,8; +14,2] | +2,1 [−1,7; +5,8] |

Mọi CI đều chứa 0.

## Recall từng lớp (khỏe / vòng trong / vòng ngoài / vòng cách, %)

| k | Chỉ mẫu thật | + Flow |
|---:|---|---|
| 2 | 100 / 70,0 / 99,6 / 0,0 | 100 / 66,7 / 100 / 15,0 |
| 3 | 100 / 68,9 / 98,8 / 0,0 | 100 / 50,0 / 99,2 / 23,3 |
| 5 | 100 / 87,8 / 100 / 15,0 | 100 / 86,7 / 100 / 16,7 |
| 10 | 100 / 93,3 / 100 / 11,7 | 100 / 87,8 / 100 / 40,0 |

## Đọc đúng

- **Precision tăng mạnh ở k = 2, 3 chủ yếu do cách tính.** Chỉ mẫu thật không dự đoán vòng cách lần nào, nên precision vòng cách bị tính 0 và kéo trung bình xuống. Flow có đưa ra vài nhãn vòng cách nên được tính. Đây không phải chẩn đoán tốt hơn ở mọi lớp: vòng trong ở k = 3 giảm từ 68,9% xuống 50,0%.
- **"Ít hơn 1,9 lần" trong `curve.md` không đứng vững.** Số này là nội suy tuyến tính. Chỉ mẫu thật đã đạt 75,7% recall ở k = 5, chỉ kém mốc 76,2% của k = 10 là 0,5 điểm, nên chỉ mẫu thật cũng gần như không cần đủ 10 cửa sổ mỗi ổ. Ở k = 5, hai phương pháp gần như trùng nhau.
- **Theo mục 7 của handoff, đây là trường hợp 3:** đường Flow không cao hơn rõ ở mức ít dữ liệu (recall +3,0 và +1,2 với CI chứa 0, accuracy k = 3 thấp hơn). Không đưa tuyên bố tiết kiệm dữ liệu.
- Đơn vị độc lập vẫn là 13 ổ (2 ổ vòng cách). Đây là kết quả thăm dò trên dữ liệu công khai.
