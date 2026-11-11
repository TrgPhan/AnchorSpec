# BW-LIB: băng thông và thư viện hỏng nhân tạo (RF 500 cây, chỉ chọn loại lỗi)

## Câu 1: băng thông, chỉ sự cố thật

| Bộ | 1 kHz | 2 kHz | 6 kHz | 2k − 1k (CI 95%) | 6k − 1k (CI 95%) |
|---|---:|---:|---:|---|---|
| Paderborn 1 sự cố/loại | 59.5 | 53.0 | 59.5 | -6.5 [-18.4; +4.9] | -0.1 [-1.2; +1.0] |
| Paderborn 2 sự cố/loại | 48.7 | 46.0 | 48.8 | -2.7 [-14.3; +8.9] | +0.0 [-11.6; +10.2] |
| Paderborn 4 sự cố/loại | 62.4 | 58.5 | 78.0 | -3.8 [-31.4; +25.6] | +15.7 [-0.9; +36.3] |
| UORED 1-1-1 | 52.6 | 47.6 | 50.4 | -5.0 [-16.5; +6.3] | -2.2 [-22.9; +16.3] |
| UORED 2-2-2 | 55.2 | 49.6 | 56.5 | -5.6 [-17.7; +7.7] | +1.3 [-14.7; +17.3] |
| UORED 4-4-4 | 67.8 | 60.7 | 63.4 | -7.1 [-28.4; +12.9] | -4.4 [-27.4; +17.1] |

Kết luận theo giao thức: băng thông rộng KHÔNG lợi (0/6 bộ đạt +5 với CI dương).

## Câu 2: thư viện hỏng nhân tạo (Paderborn, kiểm tra trên 11 ổ hỏng thật)

| Cảm biến | Nhánh | Macro 2 lớp | Vòng trong | Vòng ngoài |
|---|---|---:|---:|---:|
| 1k | real_1 | 59.5 | 99.1 | 20.0 |
| 1k | real_2 | 48.7 | 38.8 | 58.7 |
| 1k | real_4 | 62.4 | 58.5 | 66.2 |
| 1k | art_only | 46.5 | 37.4 | 55.6 |
| 1k | art+real_1 | 62.5 | 68.4 | 56.6 |
| 1k | art+real_2 | 56.5 | 51.2 | 61.7 |
| 1k | inj_only | 76.9 | 98.3 | 55.6 |

| So sánh (1k) | Chênh (CI 95%) |
|---|---|
| art_only − real_1 | -13.0 [-33.7; +9.8] |
| art+real_1 − real_1 | +2.9 [-18.9; +24.8] |
| art+real_2 − real_2 | +7.7 [-8.2; +27.3] |
| art_only − inj_only | -30.4 [-48.1; -11.0] |
| inj_only − real_1 | +17.4 [+1.8; +34.7] |

Kết luận theo giao thức (1k): thư viện nhân tạo KHÔNG ĐẠT.

| Cảm biến | Nhánh | Macro 2 lớp | Vòng trong | Vòng ngoài |
|---|---|---:|---:|---:|
| 6k | real_1 | 59.5 | 99.0 | 20.0 |
| 6k | real_2 | 48.8 | 46.8 | 50.8 |
| 6k | real_4 | 78.0 | 64.5 | 91.6 |
| 6k | art_only | 61.2 | 78.3 | 44.1 |
| 6k | art+real_1 | 63.5 | 85.0 | 42.0 |
| 6k | art+real_2 | 64.8 | 82.4 | 47.2 |
| 6k | inj_only | 73.1 | 99.4 | 46.7 |

| So sánh (6k) | Chênh (CI 95%) |
|---|---|
| art_only − real_1 | +1.7 [-17.5; +18.8] |
| art+real_1 − real_1 | +4.0 [-8.2; +16.4] |
| art+real_2 − real_2 | +16.0 [-5.4; +37.1] |
| art_only − inj_only | -11.8 [-42.3; +18.5] |
| inj_only − real_1 | +13.6 [-5.6; +33.0] |

Kết luận theo giao thức (6k): thư viện nhân tạo KHÔNG ĐẠT.
