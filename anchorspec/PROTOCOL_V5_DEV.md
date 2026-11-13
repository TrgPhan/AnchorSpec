# V5-DEV: nửa vật lý, nửa Flow-gain, chỉnh trọng số trên UORED

Ghi ngày 12/11/2026, **trước khi chạy**. Đã xem kết quả V4-DEV (`bal_flowgain`: bi 55,9 so với `hier` 66,0) và V4-VAL. Đã kiểm tra code bằng một lượt ổ 12, seed 11, m = 2 (tái tạo đúng `bal_phys`, `bal_flowgain`, `hier` của V4).

## Phân công (mỗi lỗi một bộ sinh)
- **Vòng trong, vòng ngoài:** chỉ vật lý (bể A0 150 mẫu mỗi loại, trên nền khỏe máy đích). Tầng 2 giữ nguyên 25%. Ở tầng 1, nhóm vòng nhận mẫu vật lý với phần r.
- **Bi, vòng cách:** chỉ Flow-gain. Flow (mạng S3 của Trường) học "lỗi trừ khỏe" từ sự cố thật ở máy khác, co giãn theo tần số đặc trưng, áp lên nền khỏe máy đích. Vào tầng 1 với phần s.

## Lưới (8 cấu hình)
- r ∈ {10%, 25%}
- s ∈ {25%, 50%}
- Số mẫu Flow-gain ∈ {20 × số sự cố, 150 mỗi lớp}

**Đối chứng:** `hier`; `phys_r10`, `phys_r25` (cùng r, không có Flow; tương đương photocopy, vì photocopy chiếm phần bị gộp vào mẫu thật).

## Thiết lập
UORED, 20 ổ đích, 8 seed, m = 1, 2. Chỉ chọn loại lỗi, cửa sổ lỗi nặng.

## Quy tắc khóa (trung bình hai mức m)
1. **Bảo vệ từng lớp:** recall vòng trong, vòng ngoài, bi, vòng cách **mỗi lớp** ≥ `hier` − 2 điểm.
2. **Macro 4 lớp ≥ `hier`.**
3. Trong các cấu hình đạt 1 và 2, chọn cấu hình có macro cao nhất. Không cấu hình nào đạt thì khóa `hier`, tức Flow không vào pipeline.
4. Đối chứng cho kiểm chứng: `phys_r` có cùng r với cấu hình khóa.
