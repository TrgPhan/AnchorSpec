# V4-VAL: kiểm chứng một lần (PROTOCOL_V4_VAL.md)

Khóa: `{"arm": "flow_truong", "status": "neutral", "copy_equivalent": "copy_add"}`. 440 lượt, 8 seed, chỉ chọn loại lỗi.

## HUST (tiêu chí)

| m | Nhánh | trong | ngoài | bi | Macro | Trong − hier | Ngoài − hier | bi − hier | Macro − hier | flow_truong − copy_add |
|---:|---|---:|---:|---:|---:|---|---|---|---|---|
| 1 | hier | 42.1 | 62.4 | 82.0 | 62.2 | | | | | |
| 1 | flow_truong | 39.4 | 60.5 | 82.2 | 60.7 | -2.7 [-5.8; -0.3] | -1.9 [-4.5; +0.6] | +0.2 [+0.0; +0.6] | -1.5 [-2.8; -0.2] | -1.6 [-2.6; -0.6] |
| 1 | copy_add | 42.7 | 63.1 | 81.1 | 62.3 | | | | | |
| 2 | hier | 44.4 | 60.2 | 89.2 | 64.6 | | | | | |
| 2 | flow_truong | 41.8 | 60.2 | 88.9 | 63.6 | -2.6 [-6.2; -0.3] | -0.0 [-0.4; +0.3] | -0.3 [-0.9; +0.0] | -1.0 [-2.2; -0.2] | -0.6 [-1.0; -0.2] |
| 2 | copy_add | 43.1 | 60.7 | 89.0 | 64.2 | | | | | |
| 3 | hier | 44.6 | 64.0 | 89.2 | 65.9 | | | | | |
| 3 | flow_truong | 40.8 | 61.8 | 89.2 | 63.9 | -3.8 [-9.0; +1.0] | -2.2 [-4.7; -0.6] | +0.0 [+0.0; +0.0] | -2.0 [-4.0; -0.3] | -1.9 [-3.7; -0.2] |
| 3 | copy_add | 44.2 | 64.2 | 89.1 | 65.8 | | | | | |

## XJTU (tham khảo, 2 ổ vòng cách)

| m | Nhánh | trong | ngoài | cách | Macro | Trong − hier | Ngoài − hier | cách − hier | Macro − hier | flow_truong − copy_add |
|---:|---|---:|---:|---:|---:|---|---|---|---|---|
| 0 | hier | 98.3 | 96.9 | 49.4 | 81.5 | | | | | |
| 0 | flow_truong | 93.3 | 97.0 | 49.4 | 79.9 | -5.0 [-15.0; +0.0] | +0.2 [+0.0; +0.5] | +0.0 [+0.0; +0.0] | -1.6 [-4.9; +0.1] | -0.6 [-2.0; +0.1] |
| 0 | copy_add | 95.4 | 96.9 | 49.4 | 80.6 | | | | | |

## Tiêu chí (HUST)

- c1_no_harm: KHÔNG ĐẠT
- c2_ball_gain: KHÔNG ĐẠT
- c3_flow_own: KHÔNG ĐẠT