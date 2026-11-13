# FF: Flow trong không gian đặc trưng, nhằm thắng `hier`

Ghi ngày 13/11/2026, **trước khi chạy**. Chỉ đã chạy thử 1 lượt (UORED ổ 12, seed 11, m = 2) để kiểm tra code; `hier` tái tạo đúng PB-HIER.

## Phương pháp
- Flow matching (mạng `ResidualGenerator` S3 của Trường) học, có điều kiện theo loại lỗi, phân bố của **delta đặc trưng** = đặc trưng cửa sổ lỗi thật − trung bình đặc trưng khỏe của chính máy nguồn. Học từ sự cố trong thư viện.
- Mẫu sinh = đặc trưng khỏe của máy đích + delta sinh ra, 150 mẫu mỗi loại lỗi. Mọi loại lỗi đều có mẫu, nên cân bằng nguồn gốc.
- Đối chứng `bs_*`: cùng cấu trúc, nhưng delta lấy ngẫu nhiên từ delta thật, không qua Flow.

## Nhánh
| Nhánh | Tầng 1 | Tầng 2 |
|---|---|---|
| `hier` | thật | thật + vật lý 25% |
| `ff_t1` / `bs_t1` | + sinh 25% (mọi lớp lỗi) | thật + vật lý 25% |
| `ff_t12` / `bs_t12` | + sinh 25% | thật + vật lý 12,5% + sinh 12,5% |
| `ff_t2` / `bs_t2` | thật | thật + vật lý 12,5% + sinh 12,5% |

## Phát triển (chỉ dữ liệu này được dùng để chọn)
- UORED: 20 ổ, m = 1, 2.
- XJTU: thư viện tự nhiên.
- 8 seed. Chỉ chọn loại lỗi.

**Quy tắc khóa:**
1. Với mỗi nhánh `ff_*`, tính Δ Avg Recall so với `hier` trên UORED (trung bình m) và trên XJTU.
2. Loại nhánh nếu có lớp nào, ở bộ nào, recall thấp hơn `hier` quá 3 điểm.
3. Trong các nhánh còn lại, chọn nhánh có trung bình Δ của hai bộ cao nhất, với điều kiện trung bình đó > 0.
4. Không nhánh nào đạt thì không kiểm chứng; thử ý tưởng khác (ghi giao thức mới).

## Kiểm chứng (một lần, nhánh đã khóa)
- Paderborn: m = 1, 2, 4. HUST: m = 1, 2, 3. 8 seed.
- **THẮNG** nếu cả ba điều sau đúng:
  - (a) trung bình Δ Avg Recall so với `hier` qua các mức > 0 trên **cả hai** bộ;
  - (b) ít nhất một mức, ở một bộ, có Δ với CI 95% > 0;
  - (c) không mức nào có Δ < −2 điểm.
- Báo kèm nhánh `bs_` tương ứng, để tách phần đóng góp của Flow so với delta bootstrap.

## Đếm số lần nhìn vào bộ kiểm chứng
Paderborn và HUST đã được nhìn ở các đợt trước. Mỗi ý tưởng mới được kiểm chứng sẽ được đếm và báo cáo.
