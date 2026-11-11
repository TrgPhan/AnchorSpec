# BW-LIB: băng thông cảm biến và thư viện hỏng nhân tạo

Ghi ngày 12/11/2026, **trước khi chạy**. Không phụ thuộc kết quả của M-Dev.

**Chung:**
- RF 500 cây, tham số như `InvariantClassifier`.
- Cách chấm chính: chỉ chọn loại lỗi sau `causal_average`. Macro recall theo ổ (trung bình seed), rồi theo lớp.
- CI 95% bootstrap theo ổ, phân tầng theo lớp, 5.000 lần.
- Seed 11, 29, 47.

## Câu 1: băng thông cảm biến (chỉ sự cố thật)

Ba cảm biến giả lập:
- `1k`: lấy mẫu 4 kHz, băng thông 1 kHz.
- `2k`: lấy mẫu 8 kHz, băng thông 2 kHz.
- `6k`: lấy mẫu 16 kHz, băng thông 6 kHz.

Cả ba đều ±8 g, 20 bit, nhiễu 25 µg/√Hz. Đặc trưng tính đến đúng băng thông của từng cảm biến.

**Hai bộ dữ liệu:**
- **Paderborn hỏng thật** (2 lớp): cùng thiết kế PB-Flow, 1, 2, 4 sự cố mỗi loại.
- **UORED** (3 lớp: vòng trong, ngoài, cách): ổ đích, ổ nguồn và seed như S3-Dose, bộ sự cố 1-1-1, 2-2-2, 4-4-4. Nền 11 cửa sổ khỏe; kiểm tra trên trạng thái lỗi nặng.

**Kết luận "băng thông rộng có lợi"** khi chênh `6k − 1k` ≥ +5 điểm với CI không chứa 0 ở ít nhất 2 trong 6 bộ (Paderborn 3 mức, UORED 3 bộ). Báo cả `2k − 1k`.

## Câu 2: thư viện hỏng nhân tạo (Paderborn)

**Thư viện nhân tạo:** 5 ổ vòng trong (KI01, KI03, KI05, KI07, KI08) và 7 ổ vòng ngoài (KA01, KA03, KA05–KA09). Đây là hư hỏng do người tạo (EDM, khoan, khắc), tương ứng kịch bản DENSO chủ động lắp linh kiện hỏng. Kiểm tra trên cả 11 ổ hỏng thật. Nền khỏe chọn như PB-Flow.

| Nhánh | Dữ liệu học |
|---|---|
| `art_only` | Chỉ thư viện nhân tạo |
| `art+real_m`, m = 1, 2 | Thư viện nhân tạo + m sự cố thật mỗi loại (ổ đích bị loại) |
| `real_m`, m = 1, 2, 4 | Chỉ sự cố thật (dùng lại từ Câu 1) |
| `inj_only` | Cấy A0 vào nền khỏe của máy, không có sự cố nào |

Chạy với cảm biến `1k` (chính) và `6k` (phụ). Với `inj_only`, mẫu cấy đi qua đúng cảm biến tương ứng.

**Kết luận "thư viện nhân tạo dùng được"** khi đủ cả hai:
1. `art_only` ≥ `real_1` (theo giá trị điểm).
2. `art+real_1 − real_1` ≥ +3 điểm với CI không chứa 0.

Ghi chú: cấy A0 trên Paderborn đã được xem ở TN2 (khi đó dùng RF 200 cây và cách chấm khác).
