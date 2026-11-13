# ROUTER-VAL: kiểm chứng một lần router đã khóa (PLAN.md WP6)

Ghi ngày 12/11/2026, **trước khi chạy kiểm chứng**, sau khi lượt phát triển UORED đã khóa cấu hình vào `results/router_dev/lock.json`. Script chỉ đọc file khóa, không chọn lại gì. Hash của file khóa được ghi trong `results/router_val/prerun.sha256`.

## Dữ liệu và nhánh
- HUST S1: 14 ổ đích, m = 1, 2, 3 sự cố mỗi lớp (trong, ngoài, bi), 8 seed.
- HUST S2: không có sự cố bi nào; m = 2 cho trong và ngoài, 8 seed.
- Paderborn S1: 11 ổ đích, m = 1, 2, 4 (trong, ngoài), 8 seed.
- Các nhánh:
  - `real` (RF 500).
  - `hier` (kiến trúc chốt).
  - `router`: cấu hình khóa (F-neo, nhánh C, luật bi; cổng "chưa biết" chỉ chấm ở S2 nếu không khóa luật bi).
  - `router_noflow`: như `router` nhưng tắt F-neo. Nếu nhánh C khóa một bộ có Flow, thay bằng bộ không Flow tốt nhất theo cùng quy tắc trên dữ liệu phát triển.

## Tiêu chí
1. **Không làm hại:** ở mọi mức của cả hai bộ, recall trung bình trong + ngoài của `router − hier` ≥ −1 điểm, và cận dưới CI 95% > −3.
2. **Lớp bi, HUST S1:** recall bi của `router − hier` ≥ +5 với CI > 0, hoặc macro 3 lớp ≥ +2 với CI > 0, ở ít nhất một mức.
3. **HUST S2:**
   - Nếu khóa luật bi: recall bi của `router` ≥ 30% với CI > 0.
   - Nếu không: cổng "chưa biết" bắt ≥ 50% cửa sổ bi, và ≤ 10% cửa sổ trong / ngoài bị báo nhầm "chưa biết".
4. **Flow có đóng góp:** `router − router_noflow` ≥ +2 với CI > 0 ở ít nhất một mức, và không mức nào < −1.

Báo đủ mọi nhánh và mọi tiêu chí, kể cả không đạt.
