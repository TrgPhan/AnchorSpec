# V4-VAL: kiểm chứng một lần (PLAN_V4.md mục 4.3)

Ghi ngày 12/11/2026, trước khi chạy kiểm chứng; nội dung không phụ thuộc kết quả phát triển. Script đọc `results/v4_dev/lock.json` và không chọn lại gì. Hash của khóa ghi trong `results/v4_val/prerun.sha256`.

## Dữ liệu
- **HUST:** 14 ổ đích (trong 5, ngoài 5, bi 4), m = 1, 2, 3 sự cố mỗi lớp ở ổ khác, 8 seed.
- **XJTU:** 13 ổ, thư viện tự nhiên (mọi ổ khác), 8 seed. Chỉ để tham khảo cho vòng cách (2 ổ), không tính tiêu chí.

## Nhánh
- `hier` (kiến trúc chốt).
- Nhánh đã khóa.
- Đối chứng photocopy tương ứng của nhánh khóa.

## Tiêu chí (HUST)
1. **Không làm hại:** ở mọi mức, recall vòng trong và vòng ngoài của `khóa − hier` mỗi lớp ≥ −2 điểm, và macro ≥ −1.
2. **Có ích cho bi:** recall bi của `khóa − hier` ≥ +5 điểm với CI 95% > 0, ở ít nhất một mức.
3. **Flow có đóng góp riêng:** `khóa − đối chứng` ≥ +2 với CI > 0 ở ít nhất một mức, và không mức nào < −1.
