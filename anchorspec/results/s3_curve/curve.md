# S3 data-efficiency curve (XJTU-SY, 13 bearings LOBO, 3 seeds, healthy+terminal, 4 classes)

| Cửa sổ lỗi thật / ổ | Tổng cửa sổ lỗi thật | Chỉ mẫu thật P / R / Acc | + AnchorSpec Flow P / R / Acc |
|---:|---:|---|---|
| 2 | 24 | 67.0 / 67.4 / 85.0 | 85.2 / 70.4 / 86.2 |
| 3 | 36 | 67.2 / 66.9 / 84.4 | 81.0 / 68.1 / 84.1 |
| 5 | 60 | 93.7 / 75.7 / 89.4 | 94.0 / 75.8 / 89.4 |
| 10 | 120 | 86.9 / 76.2 / 89.9 | 95.7 / 81.9 / 92.0 |

## Dữ liệu lỗi thật cần để đạt mức của "chỉ mẫu thật, đủ 10 cửa sổ/ổ"

- avg_precision = 86.9%: chỉ mẫu thật cần 4.5 cửa sổ/ổ; AnchorSpec Flow cần 3.9 cửa sổ/ổ → ít hơn 1.1 lần.
- avg_recall = 76.2%: chỉ mẫu thật cần 10.0 cửa sổ/ổ; AnchorSpec Flow cần 5.3 cửa sổ/ổ → ít hơn 1.9 lần.
- accuracy = 89.9%: chỉ mẫu thật cần 10.0 cửa sổ/ổ; AnchorSpec Flow cần 6.0 cửa sổ/ổ → ít hơn 1.7 lần.

Cửa sổ của cùng một ổ không phải sự kiện độc lập; 13 ổ bi là đơn vị độc lập. Kết quả thăm dò, không phải xác nhận.