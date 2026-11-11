# M-Dev: tìm phương pháp có giá trị trên bộ phát triển, khóa rồi mới kiểm chứng

Ghi ngày 12/11/2026, **trước khi chạy**, sau khi PB-Flow không đạt.

**Bộ phát triển:** XJTU (bộ sự cố tự nhiên) và UORED (5 bộ sự cố 5-2-1, 1-2-5, 2-2-2, 1-1-1, 4-4-4), đúng thiết kế ổ đích, ổ nguồn và seed của S3-Dose. 264 lượt.
**Bộ kiểm chứng:** Paderborn hỏng thật, chỉ chạy sau khi đã khóa cấu hình theo quy tắc dưới đây.

## Câu hỏi

1. **Cấy lỗi vật lý vào nền khỏe của chính máy (A0)**, ghép với vài sự cố thật, có hơn chỉ dùng sự cố thật không? Đây là ý tưởng gốc của AnchorSpec, chưa từng thử với RF ổn định và cách chấm chỉ chọn loại lỗi.
2. **Bộ phân loại khác** có tổng quát giữa các ổ tốt hơn RF không?

## Chung cho mọi nhánh

- Đặc trưng 45 cột raw, cảm biến 1 kHz.
- Cách chấm chính: chỉ chọn loại lỗi (`fault_labels`) sau `causal_average`. Macro recall 3 lớp (vòng trong, ngoài, cách) ở trạng thái nặng (UORED) hoặc cuối đời (XJTU). Theo ổ, rồi theo lớp.

## Các nhánh

**Nhánh mốc và các nhánh dữ liệu sinh** (cùng RF 500 cây, tham số như `InvariantClassifier`):

| Nhánh | Nội dung |
|---|---|
| `real` | Chỉ sự cố thật. **Mốc so sánh** |
| `flow_mix_0.25_30` | Flow S3 như PB-Flow, một hạt giống lấy mẫu (20261106) |
| `inj_mix_0.25`, `inj_mix_0.5` | 150 mẫu cấy A0 mỗi lớp vòng trong và vòng ngoài, chiếm 25% hoặc 50% trọng số của lớp đó. Tổng trọng số lớp không đổi. Vòng cách không có mẫu cấy |
| `inj_only` | Nền khỏe + mẫu cấy vòng trong và ngoài, **không** dùng sự cố thật. Chỉ để tham khảo |

Mẫu cấy dùng `funnel.injected`, tiên nghiệm mặc định `Prior()`, cấy vào cửa sổ khỏe của chính ổ đích:
- XJTU: 5 bản ghi khỏe đầu.
- UORED: 11 cửa sổ nền.

**Các bộ phân loại khác, trên chỉ sự cố thật:**
- `et500`: ExtraTrees 500 cây, cùng tham số cây.
- `hgb`: HistGradientBoosting, 200 vòng, sâu 3, mỗi lá tối thiểu 5 mẫu.
- `lr`: hồi quy logistic, C = 1.
- `svm1`: SVM như `InvariantClassifier`.

Mọi bộ phân loại dùng chung bước gộp mẫu trùng và chuẩn hóa có trọng số của `invariant_classifier.canonicalize`.

**Kết hợp:** `inj_mix_{0.25, 0.5}` với `et500` và với `lr`.

## Quy tắc khóa (khai báo trước)

- Với mỗi nhánh, tính chênh so với `real` ở 6 bộ phát triển.
- **Đủ điều kiện:** chênh trung bình ≥ +2,0 điểm và không bộ nào thấp hơn −2,0 điểm.
- **Khóa** nhánh đủ điều kiện có chênh trung bình lớn nhất. Nếu nhánh tốt nhất trong các bộ phân loại khác (không dùng mẫu cấy) cũng đủ điều kiện, khóa thêm nhánh đó. Tối đa 2 nhánh.
- Nếu không nhánh nào đủ điều kiện: không khóa gì, và Paderborn chỉ chạy nhánh có chênh trung bình lớn nhất, ghi rõ là **thăm dò**.

## Kiểm chứng trên Paderborn (PB-M), cùng thiết kế với PB-Flow

- Ổ đích, nền khỏe, 1, 2, 4 sự cố/loại, 3 seed, RF 500 cây.
- Chỉ số chính: chỉ chọn loại lỗi, macro 2 lớp.
- **Đạt** khi: ở ít nhất một mức, chênh so với `real` ≥ +3 điểm với CI 95% không chứa 0; và không mức nào thấp hơn −1 điểm.
- Lưu ý: A0 (cấy không dùng sự cố thật) đã từng được xem trên Paderborn ở TN2, nên phép kiểm chứng này **không hoàn toàn độc lập** với thành phần cấy lỗi.
