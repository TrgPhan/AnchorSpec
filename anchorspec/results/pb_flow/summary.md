# PB-Flow: Flow S3 trên Paderborn hỏng thật (RF 500 cây; giao thức PROTOCOL_PB_FLOW.md)

| Sự cố/loại | Nhánh | Chỉ chọn loại lỗi | Vòng trong / ngoài | Có lựa chọn khỏe | Lượt chẩn đoán đúng (trên 33) | Gán lỗi trên khỏe |
|---:|---|---:|---|---:|---:|---:|
| 1 | real | 59.5 | 99.1 / 20.0 | 29.4 | 21 | 0.5 |
| 1 | dup_add_0.25 | 56.4 | 92.5 / 20.2 | 30.5 | 19 | 0.5 |
| 1 | flow_mix_0.25_30 | 61.5 | 95.9 / 27.0 | 37.0 | 22 | 0.5 |
| 2 | real | 48.7 | 38.8 / 58.7 | 43.4 | 16 | 0.2 |
| 2 | dup_add_0.25 | 47.8 | 38.8 / 56.8 | 41.4 | 15 | 0.1 |
| 2 | flow_mix_0.25_30 | 49.1 | 38.9 / 59.4 | 43.4 | 16 | 0.6 |
| 4 | real | 62.4 | 58.5 / 66.2 | 62.1 | 20 | 0.3 |
| 4 | dup_add_0.25 | 60.6 | 55.3 / 66.0 | 60.3 | 20 | 0.5 |
| 4 | flow_mix_0.25_30 | 61.6 | 55.3 / 68.0 | 61.4 | 19 | 1.1 |

| Sự cố/loại | So sánh | Chỉ chọn loại lỗi (CI 95%) | Có lựa chọn khỏe (CI 95%) |
|---:|---|---|---|
| 1 | flow_mix_0.25_30 - real | +1.9 [-2.3; +8.7] | +7.5 [+0.1; +18.3] |
| 1 | flow_mix_0.25_30 - dup_add_0.25 | +5.1 [-1.3; +13.9] | +6.4 [+0.1; +17.4] |
| 1 | dup_add_0.25 - real | -3.2 [-9.6; +0.2] | +1.1 [-0.2; +3.5] |
| 2 | flow_mix_0.25_30 - real | +0.4 [+0.0; +0.9] | +0.0 [-1.4; +1.0] |
| 2 | flow_mix_0.25_30 - dup_add_0.25 | +1.4 [-0.2; +4.2] | +2.0 [+0.3; +4.7] |
| 2 | dup_add_0.25 - real | -1.0 [-3.4; +0.5] | -2.0 [-5.0; +0.1] |
| 4 | flow_mix_0.25_30 - real | -0.7 [-5.1; +2.4] | -0.7 [-4.7; +2.4] |
| 4 | flow_mix_0.25_30 - dup_add_0.25 | +1.0 [-0.6; +3.0] | +1.1 [-0.5; +3.1] |
| 4 | dup_add_0.25 - real | -1.7 [-4.8; -0.1] | -1.8 [-4.8; -0.0] |

Tiêu chí 1 (≥ +3, CI > 0 ở ít nhất một mức): KHÔNG ĐẠT
Tiêu chí 2 (không mức nào < −1): ĐẠT
Tiêu chí 3 (hơn bản sao ở mức đạt tiêu chí 1): KHÔNG ĐẠT
**Kết luận theo giao thức: Flow KHÔNG CÓ giá trị kiểm chứng trên Paderborn.**