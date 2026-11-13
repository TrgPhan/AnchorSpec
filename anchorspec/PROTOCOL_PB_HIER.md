# PB-HIER: kiểm chứng kiến trúc hai tầng (đã khóa) trên Paderborn hỏng thật

Ghi ngày 12/11/2026 lúc khoảng 09:15, **trước khi chạy**.

## Mục đích

Chốt một phương pháp duy nhất. Cấy phẳng (`et500+inj_mix_0.25`) đã qua Paderborn, nhưng làm sập lớp không có mẫu cấy (vòng cách, bi). Kiến trúc hai tầng (`hier`, `PROTOCOL_HIER.md`) đã qua HUST và bộ phát triển, nhưng chưa chạy trên Paderborn. Nếu `hier` qua cả Paderborn thì đó là phương pháp chốt.

## Đã biết trước khi chạy (không độc lập hoàn toàn)

- Đã xem PB-Flow, PB-M, PB-INJ (3 và 5 seed), HUST HIER, và hai kiểm tra Flow của Trường sáng 12/11.
- Paderborn chỉ có vòng trong và vòng ngoài. Khi chỉ chọn loại lỗi, `hier` tương đương tầng 2 (ExtraTrees trên sự cố thật + 25% mẫu cấy, không có lớp khỏe), nên dự kiến gần với cấy phẳng. Đây là phép kiểm tra **nhất quán** của kiến trúc đã khóa, không phải phát hiện mới.

## Thiết kế (không sửa gì so với HIER và PB-INJ)

- Hàm `two_stage` và `scores_for` của `m_hier.py`, không đổi.
- Dữ liệu, cảm biến 1 kHz, chọn ổ khỏe, chọn sự cố, mẫu cấy A0 (150 mỗi lớp): như `pb_m.py`.
- 11 ổ đích hỏng thật; m = 1, 2, 4 sự cố mỗi loại; **8 seed**: 11, 29, 47, 101, 202, 303, 404, 505.
- Nhánh: `real` (RF 500), `et500`, `et500+inj_mix_0.25` (cấy phẳng), `hier`, `hier_real`.
- Chỉ số: macro 2 lớp, chỉ chọn loại lỗi. Mỗi ổ lấy trung bình trên 8 seed; bootstrap theo ổ, phân tầng theo lớp.

## Tiêu chí đạt (`hier` so với `real`)

1. Ít nhất một mức có chênh ≥ +3 điểm với CI 95% không chứa 0.
2. Không mức nào thấp hơn −1 điểm.

Phụ (báo, không quyết định đạt): `hier` so với cấy phẳng; `hier` so với `hier_real`; tách riêng seed 11/29/47 và 5 seed mới.

## Quyết định

- Đạt: chốt `hier` là phương pháp cuối cùng (một kiến trúc, qua Paderborn và HUST).
- Không đạt: báo đúng như vậy; phương pháp chốt sẽ ghi rõ điều kiện dùng cấy phẳng hay hai tầng.
