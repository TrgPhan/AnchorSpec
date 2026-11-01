# Giao thức TN2c — kiểm chứng cấy lỗi trên giàn IMS, ghi trước khi tính dự đoán

**Câu hỏi:** cách A0 của TN2b có giữ được trên giàn thử khác, loại ổ khác (ổ đũa hai dãy Rexnord ZA-2115, 2000 rpm)?

**Tiêu chí mô tả:** A0 ≥ C trên chỉ số chính. Chỉ có 3 ổ hỏng phù hợp nên **không có CI**, đây chỉ là bằng chứng yếu.

## Dữ liệu

Readme IMS: bộ 1 ổ 3 hỏng vòng trong, ổ 4 hỏng con lăn; bộ 2 ổ 1 hỏng vòng ngoài; bộ 3 ổ 3 hỏng vòng ngoài.

| Vai trò | Ổ |
|---|---|
| Vòng trong | t1_b3 |
| Vòng ngoài | t2_b1, t3_b3 |
| Không có công thức, chỉ ghi lại dự đoán | t1_b4 (con lăn) |
| Đối chứng không ghi nhận hỏng | t1_b1, t1_b2, t2_b2, t2_b3, t2_b4, t3_b1, t3_b2, t3_b4 |

**Thông số là điểm yếu:** chưa tìm được bảng hình học gốc. Bậc lỗi lấy từ nguồn thứ cấp (BPFO 236,4; BPFI 296,9; FTF 14,8 Hz ở 2000 rpm, README `hibatallahchmicha/bearing-rul-pipeline`), trước khi dùng được kiểm tra bằng đỉnh phổ bao hình trên t2_b1.

Một trục cho mọi ổ (kênh đầu của ổ). Cảm biến rẻ như TN2b. Đơn vị không ghi, coi là g. Bộ 3 có 6.324 tệp, khác readme.

## Chia và chỉ số

Nền: 30 bản ghi đầu của chính ổ. Kiểm tra: 10% bản ghi cuối (chính), 2% cuối (phụ, vì t3_b3 có HI phẳng tới rất muộn). Đối chứng lấy cùng khoảng thời gian.

**Chính:** độ đúng 3 lớp trung bình theo lớp vòng trong và vòng ngoài trên 10% cuối, 3 seed. **Phụ:** 2% cuối; độ đúng "bình thường" trên ổ đối chứng.

## Nhánh

A0: nền + 150 mẫu cấy/lớp, tiên nghiệm rộng, RF 200 cây. C: CWRU như TN2b, không có nền máy trong huấn luyện. P: quy tắc vật lý. Cả ba chuẩn hóa theo nền của chính ổ. Không đổi cấu hình theo kết quả; chạy một lần.

## Giới hạn

Chỉ 3 ổ; các ổ cùng trục nên không độc lập; đối chứng có thể đã suy giảm mà không được ghi; thí nghiệm ổ đũa, thử tăng tốc. Đường HI của IMS đã xem ở TN3 nhưng chưa có dự đoán loại lỗi nào được tính.

## Nhật ký trước khi chạy test

Kiểm tra thông số trên t2_b1: đỉnh phổ bao hình mạnh nhất ở 230–231 Hz và 461–463 Hz (hài bậc 2), SNR quanh BPFO 378 so với 4,3 quanh BPFI. Đỉnh thấp hơn 236,4 Hz khoảng 2,3%, nằm trong dung sai đặc trưng ±5,9 Hz, phù hợp trượt. Giữ nguyên thông số.
