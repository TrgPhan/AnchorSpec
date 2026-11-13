# V5-VAL: kiểm chứng một lần cấu hình v5 đã khóa

Ghi ngày 12/11/2026, **trước khi có kết quả V5-DEV**. Script đọc `results/v5_dev/lock.json` và không chọn lại gì. Nếu khóa là `hier`, không chạy kiểm chứng.

## Dữ liệu
- **HUST:** 14 ổ (trong, ngoài, bi), m = 1, 2, 3, 8 seed. Đây là bộ tính tiêu chí.
- **XJTU:** thư viện tự nhiên, 8 seed. Chỉ tham khảo cho vòng cách (2 ổ).

## Nhánh
- `hier`.
- Cấu hình đã khóa.
- Đối chứng `phys_rXX`: cùng phần vật lý ở tầng 1, không có Flow-gain.

## Tiêu chí (HUST)
1. **Không làm hại từng lớp:** ở mọi mức, recall vòng trong, vòng ngoài và bi của `khóa − hier` **mỗi lớp** ≥ −2 điểm.
2. **Có ích:** macro 3 lớp của `khóa − hier` ≥ +2 điểm với CI 95% > 0, ở ít nhất một mức.
3. **Flow có đóng góp riêng:** macro của `khóa − phys_rXX` ≥ +2 với CI > 0 ở ít nhất một mức, và không mức nào < −1.
