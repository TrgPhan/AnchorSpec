# S3 data-efficiency curve (XJTU-SY, 13 bearings LOBO, 3 seeds, healthy+terminal, 4 classes)

| Cửa sổ lỗi thật / ổ | Tổng cửa sổ lỗi thật | Chỉ mẫu thật P / R / Acc | + AnchorSpec Flow P / R / Acc |
|---:|---:|---|---|
| 2 | 24 | 67.0 / 67.7 / 85.1 | 88.8 / 69.6 / 85.8 |
| 3 | 36 | 66.9 / 67.8 / 85.3 | 90.1 / 72.9 / 86.8 |
| 5 | 60 | 80.3 / 71.1 / 87.2 | 94.5 / 77.8 / 90.1 |
| 10 | 120 | 68.0 / 71.9 / 87.9 | 96.5 / 84.9 / 93.3 |

## Dữ liệu lỗi thật cần để đạt mức của "chỉ mẫu thật, đủ 10 cửa sổ/ổ"

- avg_precision = 68.0%: chỉ mẫu thật cần 3.2 cửa sổ/ổ; AnchorSpec Flow cần 2.0 cửa sổ/ổ → ít hơn 1.6 lần.
- avg_recall = 71.9%: chỉ mẫu thật cần 10.0 cửa sổ/ổ; AnchorSpec Flow cần 2.7 cửa sổ/ổ → ít hơn 3.7 lần.
- accuracy = 87.9%: chỉ mẫu thật cần 10.0 cửa sổ/ổ; AnchorSpec Flow cần 3.6 cửa sổ/ổ → ít hơn 2.8 lần.

Cửa sổ của cùng một ổ không phải sự kiện độc lập; 13 ổ bi là đơn vị độc lập. Kết quả thăm dò, không phải xác nhận.