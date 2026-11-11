# S3-Delta: kết quả (XJTU 13 ổ, 3 seed; Flow trung bình 5 hạt giống lấy mẫu)

| Nhánh | Macro recall cuối đời | Khoảng theo hạt giống | Vòng cách | Gán lỗi trên khỏe | P / R / Acc 4 lớp |
|---|---:|---|---:|---:|---|
| Chỉ mẫu thật, raw | 68.33 | 68.33–68.33 | 11.67 | 0.00 | 86.9 / 76.2 / 89.9 |
| Flow, raw | 74.06 | 67.64–78.38 | 34.33 | 0.00 | 93.9 / 80.5 / 91.4 |
| Chỉ mẫu thật, delta | 77.73 | 77.73–77.73 | 45.00 | 3.08 | 83.4 / 82.5 / 89.1 |
| Flow + delta | 75.86 | 68.70–78.47 | 42.67 | 3.90 | 80.8 / 80.9 / 87.1 |

| So sánh (macro recall cuối đời) | Chênh | CI 95% |
|---|---:|---|
| flow_delta - real_raw | +7.53 | [-8.28; +22.22] |
| flow_delta - real_delta | -1.87 | [-4.12; +0.00] |
| real_delta - real_raw | +9.40 | [-6.25; +23.70] |
| flow_raw - real_raw | +5.72 | [-2.80; +14.24] |
| flow_delta - flow_raw | +1.81 | [-8.12; +9.89] |