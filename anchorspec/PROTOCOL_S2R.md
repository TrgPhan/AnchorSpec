# S2R: Flow matching từ mô phỏng sang thật, nhằm thắng `hier`

Ghi ngày 13/11/2026, **trước khi chạy** (chỉ đã chạy thử 2 lượt trên Paderborn nhân tạo: KA01 seed 11 m 1, KI01 seed 29 m 2). Ý tưởng FF trước đó không qua bước phát triển (`results/ff_dev/summary.md`), nên chưa có lần nhìn nào vào bộ kiểm chứng.

## Phương pháp
- Trên các máy trong thư viện:
  - Tính delta đặc trưng của **lỗi thật** (so với khỏe của chính máy đó).
  - Tính delta đặc trưng của **mẫu cấy vật lý** trên nền khỏe của chính máy đó: 30 mẫu mỗi sự cố.
- Một Flow (mạng `SmallNetwork` của S3, mục tiêu flow matching) học **phép chuyển phân bố** từ delta mô phỏng sang delta thật. Có điều kiện theo loại lỗi; chỉ áp cho vòng trong và vòng ngoài.
- Trên máy đích: lấy 150 mẫu cấy vật lý mỗi loại (như `hier`), đẩy delta của chúng qua Flow, được mẫu đã hiệu chỉnh.

## Nhánh (tầng 1 giữ như `hier`; chỉ đổi tầng 2)
| Nhánh | Tầng 2 |
|---|---|
| `hier` | thật + vật lý 25% |
| `s2r_rep` | thật + mẫu S2R 25% |
| `s2r_mix` | thật + vật lý 12,5% + S2R 12,5% |
| `ctrl_rep` | thật + ghép thẳng delta lỗi thật lên nền máy đích 25% (không Flow) |
| `ctrl_mix` | thật + vật lý 12,5% + ghép thẳng 12,5% |

## Phát triển
- **Paderborn hỏng nhân tạo (`pba`):** 12 ổ, m = 1, 2. Không trùng ổ nào với 11 ổ hỏng thật dùng kiểm chứng.
- **UORED:** m = 1, 2.
- **XJTU:** thư viện tự nhiên.
- 8 seed.

**Quy tắc khóa:**
1. Với nhánh `s2r_*`, tính Δ Avg Recall so với `hier` (UORED và `pba` lấy trung bình m; XJTU một mức).
2. Loại nhánh nếu có lớp nào, ở bộ nào, recall thấp hơn `hier` quá 3 điểm.
3. Trong các nhánh còn lại, chọn nhánh có trung bình Δ trên ba bộ cao nhất, với điều kiện trung bình đó > 0.
4. Không nhánh nào đạt thì không kiểm chứng.

## Kiểm chứng (một lần): Paderborn hỏng thật (m = 1, 2, 4) + HUST (m = 1, 2, 3), 8 seed
**THẮNG** nếu cả ba điều sau đúng:
- (a) trung bình Δ Avg Recall so với `hier` qua các mức > 0 trên **cả hai** bộ;
- (b) ít nhất một mức có CI 95% > 0;
- (c) không mức nào có Δ < −2.

Báo kèm nhánh `ctrl` tương ứng, để tách đóng góp của Flow so với ghép thẳng delta.
