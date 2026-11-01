# Giao thức E8 — xác nhận độc lập trên UORED-VAFCLS, ghi trước khi đọc bất kỳ tín hiệu lỗi nào

**Câu hỏi:** thiết kế phễu v1.5, chốt từ E1–E6 trên dữ liệu khác, có giữ được trên 20 ổ chưa từng dùng không?

## Dữ liệu

[UORED-VAFCLS](https://data.mendeley.com/datasets/y2px5tg92h/5), CC BY 4.0. Chưa từng dùng trong dự án; hash khớp bản công bố. Theo [Sehri et al. 2023](https://doi.org/10.1016/j.dib.2023.109327):
- 20 ổ (inner 1–5, outer 6–10, ball 11–15, cage 16–20), hỏng do tẩy mỡ, chạy tới hỏng, không phải lỗi gia công. Bài báo cho biết tác giả lọc file có tín hiệu sạch và xác nhận loại lỗi bằng FFT, nên **các tín hiệu đã qua chọn lọc**.
- Mỗi ổ có 3 file 10 s, 42 kHz: khỏe (`_0`), đang phát triển (`_1`, khoảng nửa đời), hỏng (`_2`).
- NSK 6203ZZ và FAFNIR 203KD đều: 8 bi, d=6,77 mm, D=28,50 mm. Tải 400 N, riêng lỗi bi 0 N. 1750 rpm danh định.
- Kênh dùng: cột 1 (gia tốc). Đơn vị không có trong tài liệu; coi là m/s², bỏ thành phần một chiều của từng file. Xem nhật ký.

**Thiết kế chốt từ:** E2 (ngưỡng tự động từ lỗi cấy), E3 (bỏ lớp vòng cách khỏi huấn luyện; lỗi cấy vào nền của máy), E4 chưa ảnh hưởng thiết kế. Đối chứng lấy từ TN2b.

## Xử lý

Cảm biến rẻ như TN2b (4 kHz, 1 kHz, 25 µg/√Hz, ±8 g, 20 bit). Một trục. Cửa sổ 1 s, chồng 50%: 19 cửa sổ mỗi file.
- **Nền:** 11 cửa sổ trong 6 s đầu file khỏe của chính ổ đó. **Bình thường kiểm tra:** 7 cửa sổ trong 4 s cuối, không trùng với nền. Nền rất ngắn so với thiết kế (nhiều ngày); đây là giới hạn của bộ dữ liệu.
- **Tốc độ:** ước lượng từ phổ 6 s nền, tìm ±3% quanh 1750 rpm, không dùng kênh tốc độ. Kênh tốc độ chỉ để đối chiếu sai số sau khi có kết quả.

## Các nhánh (mỗi ổ một mô hình, 3 seed 11/29/47)

| Nhánh | Mô tả |
|---|---|
| **M1 (chính)** | Một-chống-phần-còn-lại, RF 50 cây sâu 8, vòng trong + vòng ngoài, 150 mẫu cấy/lớp, tiên nghiệm rộng, ngưỡng tự động từ 40 mẫu cấy giữ riêng, khoảng cách 0,1, làm mượt 5 cửa sổ. Được nói "chưa rõ". |
| M0 | RF 50 cây nhiều lớp, cùng dữ liệu, luôn trả lời |
| C | CWRU như TN2b, RF 50 cây, luôn trả lời |
| D | Lỗi nặng thật từ các ổ UORED khác cùng lớp (bỏ ổ đang kiểm), RF 50 cây, luôn trả lời |

Không dùng lỗi thật cho M1, M0. Vòng cách và lỗi bi **không có trong huấn luyện** của M1, M0: đóng vai lỗi chưa biết.

## Chỉ tiêu, xét trên trạng thái hỏng `_2`

| Mã | Chỉ tiêu | Ngưỡng đạt |
|---|---|---|
| G-a | M0 không thua C, macro trong và ngoài | Hiệu ≥ 0 |
| G-b | M1 đúng khi trả lời, macro theo ổ | ≥ 0,85 |
| G-c | M1 tỉ lệ trả lời | ≥ 0,60 |
| G-d | M1 gọi lỗi trên bình thường kiểm tra | ≤ 0,10 |
| G-e | Nhận ra chưa biết, AUROC theo ổ, ball + cage so với inner + outer, điểm 1 − điểm M1 lớn nhất | ≥ 0,85 |

Báo cáo mọi chỉ tiêu dù đạt hay trượt, kèm CI bootstrap theo ổ. **Báo cáo không đặt ngưỡng:** trạng thái đang phát triển `_1`; tỉ lệ cửa sổ có HI z ≥ 10 ở các trạng thái; bản 6 kHz của cùng phương pháp.

## Quy trình

`check` chỉ đọc 20 file khỏe (đơn vị, cắt đỉnh, tốc độ) → `smoke` chạy đường ống chỉ với file khỏe → freeze hash → `test` một lần, từ chối chạy lại. Hàm đọc chặn file lỗi trước `test`. Không đổi cấu hình theo kết quả.

## Giới hạn đã biết

Tín hiệu đã chọn lọc nên có thể dễ hơn thực tế. Nền 6 s. Cùng giàn thử, cùng cỡ ổ. Mỗi lớp 5 ổ. Lỗi do tẩy mỡ, thử tăng tốc. Không kiểm tra được báo nhầm dài hạn. Kết quả **không chứng minh được hiệu quả trên máy DENSO**.

## Nhật ký trước freeze

- `check` trên 20 file khỏe, chưa đọc file lỗi: nếu coi là g thì RMS 1,9–32 và nhiều file vượt ±8 ở gần 100% mẫu, không phù hợp vật lý. Đổi sang giả định m/s² và trừ thành phần một chiều. Các số dưới được đo sau khi sửa.
- Cột 3 chỉ có một giá trị rpm trong cả file (ví dụ 1819, 1880, 1736), còn lại bằng 0, không phải chuỗi xung. Đỉnh gia tốc 1× rõ ở 29,7 Hz (khoảng 1782 rpm) trên các file khỏe đã kiểm, khớp bộ ước lượng. Tốc độ lấy từ bộ ước lượng trên nền, như đã ghi.
- Kênh tốc độ không dùng để đối chiếu sai số được; thay bằng đỉnh 1× tìm rộng 24–36 Hz trên chính file khỏe.
- Lần chạy test đầu dừng do lỗi trước khi ghi bất kỳ kết quả nào, không có dự đoán nào được xem: một ổ có nền khỏe đã chạm ±8 g nên cổng chất lượng loại mọi mẫu cấy. Sửa `funnel.injected`: khi nền đã bão hòa quá 0,1%, không tính bão hòa là lỗi của mẫu cấy. Freeze lại.
