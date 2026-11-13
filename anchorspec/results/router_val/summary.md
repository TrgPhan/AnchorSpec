# ROUTER-VAL: kiểm chứng một lần (PROTOCOL_ROUTER_VAL.md)

Cấu hình khóa: `{"fneo": true, "branch_c": "c_none", "ball_rule": null, "kappa": 1.25}`. 712 lượt, 8 seed, chỉ chọn loại lỗi.

## HUST, S1

| m | Nhánh | trong | ngoài | bi | Macro | Trong+ngoài − hier (CI) | Macro − hier (CI) | router − router_noflow (CI) |
|---:|---|---:|---:|---:|---:|---|---|---|
| 1 | real | 24.1 | 59.5 | 84.0 | 55.9 | | | |
| 1 | hier | 42.1 | 62.4 | 82.0 | 62.2 | | | |
| 1 | router | 41.7 | 62.7 | 81.7 | 62.0 | -0.1 [-0.7; +0.5] | -0.2 [-0.5; +0.2] | -0.2 [-0.5; +0.2] |
| 1 | router_noflow | 42.1 | 62.4 | 82.0 | 62.2 | | | |
| 2 | real | 31.8 | 55.8 | 85.1 | 57.5 | | | |
| 2 | hier | 44.4 | 60.2 | 89.2 | 64.6 | | | |
| 2 | router | 45.1 | 60.1 | 89.2 | 64.8 | +0.3 [-0.6; +1.1] | +0.2 [-0.4; +0.7] | +0.2 [-0.4; +0.7] |
| 2 | router_noflow | 44.4 | 60.2 | 89.2 | 64.6 | | | |
| 3 | real | 28.5 | 52.8 | 86.6 | 56.0 | | | |
| 3 | hier | 44.6 | 64.0 | 89.2 | 65.9 | | | |
| 3 | router | 45.2 | 62.5 | 89.2 | 65.6 | -0.5 [-1.0; +0.2] | -0.3 [-0.7; +0.1] | -0.3 [-0.7; +0.1] |
| 3 | router_noflow | 44.6 | 64.0 | 89.2 | 65.9 | | | |

## Paderborn, S1

| m | Nhánh | trong | ngoài | Macro | Trong+ngoài − hier (CI) | Macro − hier (CI) | router − router_noflow (CI) |
|---:|---|---:|---:|---:|---|---|---|
| 1 | real | 56.5 | 33.0 | 44.8 | | | |
| 1 | hier | 75.5 | 56.0 | 65.8 | | | |
| 1 | router | 74.2 | 55.3 | 64.7 | -1.1 [-2.7; +0.4] | -1.1 [-2.7; +0.4] | -1.1 [-2.8; +0.4] |
| 1 | router_noflow | 75.5 | 56.0 | 65.8 | | | |
| 2 | real | 43.0 | 48.3 | 45.7 | | | |
| 2 | hier | 60.6 | 62.2 | 61.4 | | | |
| 2 | router | 61.6 | 63.0 | 62.3 | +0.9 [+0.3; +1.6] | +0.9 [+0.3; +1.7] | +0.9 [+0.3; +1.7] |
| 2 | router_noflow | 60.6 | 62.2 | 61.4 | | | |
| 4 | real | 53.2 | 68.8 | 61.0 | | | |
| 4 | hier | 68.9 | 83.7 | 76.3 | | | |
| 4 | router | 69.6 | 83.2 | 76.4 | +0.1 [-1.0; +1.5] | +0.1 [-1.0; +1.4] | +0.1 [-1.0; +1.4] |
| 4 | router_noflow | 68.9 | 83.7 | 76.3 | | | |

## HUST, S2 (không có sự cố bi nào)

| Nhánh | trong | ngoài | bi | Bi "chưa biết" | Lớp đã biết bị báo "chưa biết" |
|---|---:|---:|---:|---:|---:|
| hier | 64.9 | 72.0 | 0.0 | | |
| router | 65.7 | 72.0 | 0.0 | | |
| hier + cổng (κ=1.25) | | | | 0.7% | 9.1% |

## Tiêu chí

- c1_no_harm: KHÔNG ĐẠT
- c2_ball_S1: KHÔNG ĐẠT
- c3_S2: KHÔNG ĐẠT
- c4_flow_contrib: KHÔNG ĐẠT