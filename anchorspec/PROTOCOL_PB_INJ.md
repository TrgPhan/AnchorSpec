# PB-INJ: cấy lỗi vật lý cho bài toán vòng trong và vòng ngoài trên Paderborn

Ghi ngày 12/11/2026 lúc khoảng 00:55, **trước khi đọc bất kỳ kết quả cấy lỗi nào trên Paderborn**. Khi ghi, PB-M và BW-LIB (có nhánh `inj_only`) đang chạy, nhưng chưa xem kết quả của chúng.

## Lý do

Quy tắc khóa của M-Dev dùng macro 3 lớp, nên bị lớp vòng cách chi phối. Paderborn chỉ có vòng trong và vòng ngoài. Vì vậy áp **đúng quy tắc khóa của M-Dev** cho chỉ số macro 2 lớp (vòng trong, vòng ngoài) trên 6 bộ phát triển: chênh trung bình ≥ +2,0 điểm và không bộ nào thấp hơn −2,0 điểm.

Kết quả tính trên dữ liệu phát triển (`results/m_dev/summary.json`):

| Nhánh | Chênh TB | Thấp nhất | Đủ điều kiện |
|---|---:|---:|---|
| `et500+inj_mix_0.25` | +15,73 | +6,1 | Có, **lớn nhất** |
| `et500+inj_mix_0.5` | +14,91 | +6,1 | Có |
| `lr` | +10,13 | +1,6 | Có (đã kiểm chứng ở PB-M) |
| `et500` | +7,48 | +0,7 | Có |
| `flow_mix_0.25_30` | +2,34 | +0,2 | Có |
| `inj_mix_0.5`, `inj_mix_0.25` | +17,20, +14,83 | −2,8, −2,2 | Không |

**Khóa:** `et500+inj_mix_0.25` (ExtraTrees 500 cây, 150 mẫu cấy A0 mỗi lớp vòng trong và ngoài, chiếm 25% trọng số lớp), cùng `et500` để tách phần đóng góp của mẫu cấy.

## Thiết kế

Giống PB-M: 11 ổ hỏng thật, nền khỏe chọn như PB-Flow, 1, 2, 4 sự cố mỗi loại, 3 seed. Mốc `real` là RF 500 cây. Mẫu cấy đi vào cửa sổ khỏe của nền máy K00h.

## Tiêu chí

Cấy lỗi có giá trị khi đạt cả ba:
1. `et500+inj_mix_0.25 − real` ≥ +3 điểm với CI không chứa 0 ở ít nhất một mức.
2. Không mức nào thấp hơn −1 điểm.
3. `et500+inj_mix_0.25 − et500` > 0 ở mọi mức đạt tiêu chí 1. Nếu không, phần tăng đến từ bộ phân loại chứ không phải từ mẫu cấy.

## Lưu ý

- A0 đã được xem trên Paderborn ở TN2, khi dùng RF 200 cây và cách chấm khác.
- Đây là lần nhìn thứ hai vào Paderborn trong đêm nay, sau PB-Flow và PB-M.
