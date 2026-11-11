# HIER: cấy lỗi cho vòng trong và ngoài mà không làm sập lớp không có mẫu cấy

Ghi ngày 12/11/2026 lúc khoảng 01:10, **trước khi chạy**. Đã xem M-Dev, PB-INJ, PB-INJ 5 seed. Chưa xem HUST trong đêm nay.

## Vấn đề

PB-INJ đạt: cấy A0 cộng ExtraTrees tăng mạnh vòng trong và vòng ngoài. Nhưng trên bộ phát triển, cách cấy phẳng làm recall vòng cách giảm từ 16–50% xuống 0–14%. Nguyên nhân: chỉ có mẫu cấy cho vòng trong và ngoài, nên các mẫu này "hút" luôn cửa sổ của lớp không có mẫu cấy.

## Thiết kế hai tầng (`hier`)

1. **Tầng 1** (ExtraTrees 500 cây, chỉ sự cố thật): phân biệt khỏe, nhóm vòng (trong + ngoài), và từng lớp còn lại (vòng cách; với HUST là bi). Trọng số nhóm vòng giảm còn một nửa, để mỗi nhóm có cùng khối lượng với lớp khỏe.
2. **Tầng 2** (ExtraTrees 500 cây): chỉ phân biệt vòng trong và vòng ngoài. Học từ sự cố thật cộng 150 mẫu cấy A0 mỗi lớp, chiếm 25% trọng số lớp (như `et500+inj_mix_0.25`).
3. **Gộp:** P(trong) = P1(nhóm vòng) × P2(trong); P(ngoài) = P1(nhóm vòng) × P2(ngoài); các lớp khác lấy nguyên P1. Sau đó `causal_average`, rồi chỉ chọn loại lỗi.

**Đối chứng:** `real` (RF 500 cây), `et500`, `et500+inj_mix_0.25` (cấy phẳng), `hier_real` (cùng hai tầng nhưng tầng 2 không có mẫu cấy).

## Bước 1: phát triển trên XJTU và UORED

Cùng 264 lượt với M-Dev. Chỉ số chính là macro 3 lớp (trong, ngoài, cách).

**Quy tắc khóa:** `hier` đủ điều kiện khi chênh trung bình so với `real` ≥ +2,0 điểm, không bộ nào thấp hơn −2,0 điểm, **và** recall vòng cách trung bình không thấp hơn `real` quá 5 điểm. Nếu không đủ điều kiện, HUST vẫn chạy nhưng ghi rõ là thăm dò.

## Bước 2: kiểm chứng trên HUST (3 lớp: trong, ngoài, bi)

**Dữ liệu:** `data/hust_v`, `data/hust_v6204` (CC BY 4.0, có SHA của nhà cung cấp).
- 5 loại ổ (6204–6208), mỗi loại là một "máy". Mỗi máy có 1 ổ khỏe và 1 ổ hỏng cho mỗi loại lỗi vòng trong, vòng ngoài, bi; mỗi ổ ghi ở 3 mức tải. Loại 6204 không có lớp bi.
- Đơn vị coi là g như X7. Tốc độ lấy từ trường `fs` của từng tệp.
- Cảm biến giả lập 1 kHz; cửa sổ 1 s không chồng lấn.
- Bậc lỗi theo hình học của từng loại ổ (`x_core.GEO`): đường kính trung bình (d + D)/2, góc 0.

**Thiết kế:**
- 14 ổ đích: vòng trong 6204–6208, vòng ngoài 6204–6208, bi 6205–6208.
- Nền khỏe là tệp khỏe tải 0 của **cùng loại ổ**: 10 cửa sổ, dùng để học và để cấy lỗi.
- Ổ nguồn: bỏ ổ đích; m = 1, 2, 3 sự cố mỗi loại, chọn theo hoán vị cố định cho từng (seed, lớp).
- Mỗi sự cố dùng 10 cửa sổ trải đều trên 3 mức tải. Ổ đích kiểm tra trên mọi cửa sổ.
- Seed 11, 29, 47.

**Tiêu chí đạt** (`hier` so với `real`, macro 3 lớp, chỉ chọn loại lỗi):
1. Ít nhất một mức có chênh ≥ +3 điểm với CI 95% không chứa 0.
2. Không mức nào thấp hơn −1 điểm.
3. Recall bi trung bình không thấp hơn `real` quá 5 điểm.

Báo đủ mọi nhánh.

**Giới hạn:** HUST đã dùng ở X7 và V với cách làm khác. Các mức tải của cùng một ổ là cùng một mẫu hỏng, nên đơn vị độc lập là ổ, và chỉ có 4–5 ổ mỗi lớp.
