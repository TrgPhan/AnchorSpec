# ROUTER-DEV: một lượt phát triển trên UORED (PLAN.md WP5)

Ghi ngày 12/11/2026, **trước khi chạy** (chỉ đã chạy thử 1 lượt S1 và 1 lượt S2 trên ổ 12, seed 11, để kiểm tra code).

## Dữ liệu
- UORED, 20 ổ hỏng: trong 1–5, ngoài 6–10, bi 11–15, vòng cách 16–20. Nền khỏe là đoạn khỏe của chính ổ đích. Kiểm tra trên cửa sổ lỗi nặng.
- 8 seed: 11, 29, 47, 101, 202, 303, 404, 505.
- Thư viện: với mỗi lớp, m ổ khác ổ đích, chọn theo `rng([seed, lớp, 20261112])`.

## Kịch bản S1 (nhánh C)
- Thư viện có đủ 4 lớp, m = 1 và 2. Bi và vòng cách coi là "không có luật vật lý".
- Nhánh: `real` (RF 500), `hier` (= không sinh), `c_copy` (photocopy), `c_surr`, `c_trans`, `c_trans_flow`, `c_flowgain`. Mỗi bộ sinh 20 dòng mỗi sự cố, vào tầng 1, 25% khối lượng lớp.
- **Quy tắc khóa nhánh C:**
  1. Ứng viên phải có recall "không-luật" (trung bình bi và vòng cách, trung bình hai mức m) **cao hơn `c_copy`**, và macro 4 lớp ≥ `hier` − 1 điểm.
  2. Chọn ứng viên có recall "không-luật" cao nhất.
  3. Nếu có ứng viên dùng Flow (`c_trans_flow`, `c_flowgain`) kém ứng viên tốt nhất không quá 1 điểm, chọn ứng viên Flow cao nhất.
  4. Không có ứng viên nào thì nhánh C = `c_none`.

## Kịch bản S2 (nhánh A cho bi; nhánh D)
- Không có sự cố bi nào; thư viện m = 2 cho trong, ngoài, vòng cách.
- Nhánh: `hier_noball`; `ball_B1` đến `ball_B4` (150 mẫu cấy bi trên nền khỏe ổ đích, vào tầng 1, khối lượng một lớp).
- **Quy tắc khóa luật bi:** recall bi ≥ 30%, cận dưới CI 95% của recall bi > 0, và recall trung bình trong + ngoài giảm không quá 3 điểm so với `hier_noball`. Nhiều cấu hình đạt thì chọn recall bi cao nhất. Không cấu hình nào đạt thì luật bi = null.
- **Cổng "chưa biết"** (trên `hier_noball`): κ ∈ {1,0; 1,25; 1,5; 2,0; 3,0}. Chọn κ nhỏ nhất có tỉ lệ cửa sổ của lớp đã biết (trong, ngoài, vòng cách) bị báo "chưa biết" ≤ 10%.

## Đầu ra
`results/router_dev/summary.md` và `lock.json` (`branch_c`, `ball_rule`, `kappa`, `fneo = true`). Sau bước này không chọn lại gì; kiểm chứng theo `PROTOCOL_ROUTER_VAL.md`.
