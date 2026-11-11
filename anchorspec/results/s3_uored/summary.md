# S3-UORED: số sự cố lỗi thật mỗi loại, có và không có Flow (Flow trung bình 5 hạt giống)

| Sự cố/loại | Nhánh | Nặng, macro 4 lớp | Trong / Ngoài / Bi / Cách | Đang phát triển | Gán lỗi trên khỏe | Khoảng theo hạt giống (nặng) |
|---:|---|---:|---|---:|---:|---|
| 1 | real_raw | 35.6 | 37 / 66 / 26 / 14 | 39.0 | 0.0 | 35.6–35.6 |
| 1 | flow_raw | 26.0 | 45 / 23 / 29 / 6 | 37.0 | 0.0 | 24.1–28.9 |
| 1 | real_delta | 31.4 | 20 / 27 / 40 / 39 | 42.2 | 0.0 | 31.4–31.4 |
| 1 | flow_delta | 34.5 | 46 / 18 / 36 / 37 | 38.3 | 0.0 | 33.2–35.9 |
| 2 | real_raw | 47.9 | 75 / 46 / 38 / 33 | 45.7 | 0.0 | 47.9–47.9 |
| 2 | flow_raw | 51.5 | 80 / 50 / 40 / 36 | 50.7 | 0.0 | 49.9–53.0 |
| 2 | real_delta | 37.8 | 71 / 5 / 40 / 35 | 49.3 | 0.0 | 37.8–37.8 |
| 2 | flow_delta | 40.5 | 74 / 16 / 48 / 24 | 49.1 | 0.0 | 38.5–43.0 |
| 4 | real_raw | 63.0 | 98 / 67 / 71 / 15 | 60.3 | 0.0 | 63.0–63.0 |
| 4 | flow_raw | 66.2 | 100 / 68 / 69 / 28 | 61.6 | 0.0 | 64.6–69.7 |
| 4 | real_delta | 57.5 | 74 / 55 / 63 / 38 | 58.1 | 0.0 | 57.5–57.5 |
| 4 | flow_delta | 50.0 | 66 / 45 / 52 / 36 | 56.8 | 0.0 | 47.5–54.1 |

| Sự cố/loại | So sánh (nặng) | Chênh | CI 95% |
|---:|---|---:|---|
| 1 | flow_raw − real_raw | -9.6 | [-18.9; -0.8] |
| 1 | flow_delta − real_delta | +3.1 | [-5.6; +11.5] |
| 1 | real_delta − real_raw | -4.2 | [-17.1; +8.9] |
| 1 | flow_delta − real_raw | -1.2 | [-15.6; +13.1] |
| 2 | flow_raw − real_raw | +3.6 | [-2.6; +10.2] |
| 2 | flow_delta − real_delta | +2.6 | [-1.3; +7.0] |
| 2 | real_delta − real_raw | -10.1 | [-23.0; +3.2] |
| 2 | flow_delta − real_raw | -7.4 | [-20.0; +6.0] |
| 4 | flow_raw − real_raw | +3.2 | [-0.5; +8.2] |
| 4 | flow_delta − real_delta | -7.5 | [-13.5; -1.4] |
| 4 | real_delta − real_raw | -5.5 | [-26.1; +15.8] |
| 4 | flow_delta − real_raw | -13.0 | [-32.7; +9.2] |

Tiêu chí khai báo trước (m = 1 hoặc 2, raw): KHÔNG ĐẠT {1: False, 2: False}