# PB-M: kiểm chứng trên Paderborn (xác nhận, nhánh đã khóa)

Nhánh: ['lr']. RF 500 cây làm mốc `real`. Chỉ chọn loại lỗi, macro 2 lớp.

| Sự cố/loại | Nhánh | Macro | Vòng trong | Vòng ngoài | So với real (CI 95%) | Lượt đúng (trên 33) |
|---:|---|---:|---:|---:|---|---:|
| 1 | real | 59.5 | 99.1 | 20.0 |  | 21 |
| 1 | lr | 50.9 | 58.2 | 43.7 | -8.6 [-22.9; +7.0] | 16 |
| 2 | real | 48.7 | 38.8 | 58.7 |  | 16 |
| 2 | lr | 52.1 | 40.4 | 63.8 | +3.4 [-7.4; +14.7] | 17 |
| 4 | real | 62.4 | 58.5 | 66.2 |  | 20 |
| 4 | lr | 76.3 | 69.8 | 82.8 | +13.9 [-2.4; +35.5] | 26 |

**lr:** tiêu chí 1 KHÔNG ĐẠT; tiêu chí 2 KHÔNG ĐẠT -> KHÔNG ĐẠT
