# Mọi phương pháp chấm đúng như S3 (XJTU, 13 ổ, seed 11/29/47, khỏe + cuối đời, 4 lớp có "khỏe")

| Phương pháp | Avg Precision | Accuracy | Avg Recall | Precision khỏe / trong / ngoài / cách | Recall khỏe / trong / ngoài / cách |
|---|---:|---:|---:|---|---|
| Chỉ dữ liệu thật, RF 50 (mốc S3) | 86.9 | 89.9 | 76.2 | 90 / 100 / 87 / 70 | 100 / 93 / 100 / 12 |
| Thật + photocopy, RF 50 | 90.8 | 90.8 | 79.5 | 95 / 100 / 86 / 83 | 100 / 87 / 100 / 32 |
| Thật + Flow S3 (Trường), RF 50 | 95.7 | 92.5 | 82.9 | 98 / 99 / 86 / 100 | 100 / 90 / 100 / 42 |
| Chỉ dữ liệu thật, RF 500 | 68.0 | 87.9 | 71.9 | 87 / 100 / 85 / 0 | 100 / 88 / 100 / 0 |
| Thật + photocopy, RF 500 | 96.5 | 93.5 | 85.1 | 99 / 100 / 87 / 100 | 100 / 92 / 100 / 48 |
| Thật + Flow S3, RF 500 | 95.2 | 91.1 | 80.6 | 97 / 100 / 84 / 100 | 100 / 82 / 100 / 40 |
| Hai tầng ET, không sinh | 68.1 | 86.2 | 70.6 | 87 / 100 / 86 / 0 | 100 / 86 / 97 / 0 |
| hier (chốt): vật lý tầng 2 | 68.8 | 88.0 | 73.6 | 87 / 100 / 89 / 0 | 100 / 98 / 97 / 0 |
| hier + Flow within 0,3 (bi/cách) | 68.8 | 88.2 | 73.5 | 87 / 100 / 89 / 0 | 100 / 97 / 98 / 0 |
| hier + công thức Trường (bi/cách) | 70.5 | 87.4 | 72.8 | 87 / 100 / 89 / 6 | 100 / 93 / 96 / 2 |