# Kiểm tra cách đo của S3-Delta và S3-UORED (11/11/2026)

**Mã đúng.** Nhánh `flow_raw@20261111` và `real_raw` của S3-Delta trùng khít 39/39 lượt với `s3_curve` ở k = 10 (cùng anchor, hạt giống, trọng số). `real_delta` tái tạo 77,73% của đợt T; bản sao trên XJTU tái tạo 72,64% của đợt S.

**Lỗi thiết kế: hai giao thức S3-Delta và S3-UORED thiếu đối chứng bản sao.** Thêm mẫu sinh làm tăng tổng trọng số của lớp lỗi so với lớp khỏe. Mẫu Flow lại tương quan khoảng 0,994 với anchor, nên `flow − real` gộp cả hiệu ứng dồn trọng số lẫn giá trị mới của mẫu sinh. Đối chứng bản sao (chính cửa sổ thật của ổ nguồn, cùng số dòng và trọng số với Flow) được thêm **sau** khi đã xem kết quả, nên chỉ là phân tích bổ sung. Script: `dupcheck.py`.

| Dữ liệu | Thật | Bản sao | Flow | Bản sao − thật | Flow − bản sao |
|---|---:|---:|---:|---|---|
| XJTU, cuối đời, 3 lớp | 68,33 | 72,64 | 74,06 | +4,31 [−3,84; +12,45] | +1,42 [−0,07; +2,90] |
| UORED, 1 sự cố/loại | 35,6 | 21,7 | 26,0 | −13,9 [−29,6; +0,4] | +4,4 [−5,4; +12,9] |
| UORED, 2 sự cố/loại | 47,9 | 53,3 | 51,5 | +5,4 [−0,6; +12,5] | −1,8 [−6,7; +2,8] |
| UORED, 4 sự cố/loại | 63,0 | 62,7 | 66,2 | −0,3 [−3,8; +3,0] | +3,5 [+0,3; +6,7] |

Flow là trung bình 5 hạt giống lấy mẫu; CI 95% bootstrap theo ổ, phân tầng theo lớp.

## Đọc đúng

1. **Phần lớn "lợi ích" của Flow trên XJTU là hiệu ứng trọng số:** trong +5,7 điểm so với thật, bản sao chiếm +4,3. Phần đóng góp riêng của mẫu Flow chỉ khoảng +1,4 điểm.
2. **Flow kém ở UORED khi chỉ có 1 sự cố/loại là do cách dồn trọng số, không phải do bộ sinh.** Riêng bản sao đã giảm 13,9 điểm; so với bản sao, Flow còn nhỉnh hơn.
3. **Kết quả RF rất nhạy với tổng trọng số lớp lỗi.** Chỉ dồn thêm 25% khối lượng mà kết quả dao động từ −14 đến +5 điểm. Ngoài ra, đoạn khỏe kiểm tra nằm cùng tệp với nền nên luôn 0% gán lỗi, tức là không đo được cái giá của việc dồn khối lượng về phía lớp lỗi.
4. **Tín hiệu dương duy nhất có CI không chứa 0:** Flow so với bản sao ở UORED 4 sự cố/loại, +3,5 [+0,3; +6,7]. Đây là phân tích hậu nghiệm, nhiều phép so sánh, chưa được hiệu chỉnh.

## Các điểm yếu khác của cách đo (đã biết, không phải lỗi mã)

- Đoạn khỏe kiểm tra cùng tệp với nền: tỉ lệ gán lỗi trên khỏe gần như luôn bằng 0, không phản ánh báo nhầm thật.
- Avg precision tính lớp không có dự đoán bằng 0, làm số của nhánh "chỉ mẫu thật" ở k nhỏ thấp giả tạo (chỉ vì không dự đoán vòng cách).
- `s3_curve`: tập con k cửa sổ không lồng nhau giữa các mức k; dùng 1 hạt giống lấy mẫu trong khi biên độ dao động do hạt giống lên tới khoảng 10 điểm.
- XJTU: nhãn khỏe đầu đời là giả định; ở ±8 g trục ngang có tới 35,6% mẫu bị bão hòa ở đoạn cuối; chỉ 2 ổ vòng cách.
