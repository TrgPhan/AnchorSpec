# Giao thức TN2b — mỗi máy một mô hình trên XJTU-SY, ghi trước khi tính dự đoán

**Câu hỏi:** chỉ với đoạn đầu đời khỏe của chính ổ đó và thông số ổ bi, lỗi cấy có phân loại đúng hỏng thật cuối đời không, trong khi vẫn đủ nhẹ để chạy thời gian thực?

**Cổng G1b:** A0 không thua C theo chỉ số chính.

## Vì sao làm thử nghiệm này

TN2 trượt G1 và không còn ổ độc lập. XJTU-SY khác giàn thử, hỏng thật, có 2 trục và có nhãn vòng cách. Mỗi ổ có đoạn đầu đời, nên tránh được việc so hai ổ khác nhau như K005.

**Công khai:** chọn A0 làm nhánh chính dựa trên kết quả TN2; vì vậy Paderborn không được dùng làm bằng chứng ở đây. Đường HI của XJTU-SY đã được xem ở TN3, nhưng chưa có dự đoán loại lỗi nào được tính trên bộ này.

## Dữ liệu

Nguồn: bài giải thích bộ dữ liệu trong thư mục chính thức của tác giả (*XJTU-SY滚动轴承加速寿命试验数据集解读*, bảng 1–3). LDK UER204, 8 bi, d=7,92 mm, D=34,55 mm, góc 0°. Điều kiện: 2100/2250/2400 rpm, dùng tốc độ danh định. Tài liệu ghi kiểm chứng 1×≈34,38 Hz và BPFO lý thuyết 107,91 Hz, khớp công thức.

| Lớp | Ổ test |
|---|---|
| Vòng ngoài (8) | 1_1, 1_2, 1_3, 2_2, 2_4, 2_5, 3_1, 3_5 |
| Vòng trong (3) | 2_1, 3_3, 3_4 |
| Vòng cách (2) | 1_4, 2_3 |

**Loại khỏi kết quả, chỉ dùng chạy thử đường ống:** 1_5 và 3_2, hỏng nhiều bộ phận.

Mọi tín hiệu qua giả lập cảm biến rẻ: 4 kHz, 1 kHz, 25 µg/√Hz, ±8 g, 20 bit, hai trục. Mỗi bản ghi 1,28 s lấy một cửa sổ 1 s. Một lần tạo nhiễu cố định, seed 11/29/47 chỉ áp dụng cho cấy và mô hình.

**Chia theo thời gian trong từng ổ, trình tự cố định, không nhìn nhãn:**
- Nền: `min(30, 40% đời)` bản ghi đầu. 40% chỉ tác động tới ổ cực ngắn như 2_4.
- Bình thường test: 5 bản ghi ngay sau nền.
- Lỗi test: 10% bản ghi cuối, tối thiểu 5. Nhãn là bộ phận hỏng khám nghiệm cuối thí nghiệm.

## Các nhánh

Chuẩn hóa z-score theo nền **của chính ổ**, cho mọi nhánh.

| Nhánh | Dữ liệu huấn luyện | Vai trò |
|---|---|---|
| **A0** | Nền ổ + 150 mẫu cấy/lớp, tiên nghiệm rộng, không chạm lỗi thật | **Chính** |
| A1 | Như A0, biên độ **chung cho mọi lớp**, hiệu chỉnh bằng W1 trên lỗi thật của các ổ khác | Kiểm giả thuyết của TN2 |
| P | Không huấn luyện: quy tắc vật lý theo SNR phổ bao hình tại BPFI/BPFO/FTF so với nền, báo bình thường nếu z < 3 | Đối chứng dễ vận hành nhất |
| C | CWRU một trục, trung bình xác suất 2 trục; **không có lớp vòng cách** | Đối chứng G1b |
| D | Lỗi thật + nền từ **các ổ XJTU khác** (bỏ ổ đang kiểm) | Đối chứng dữ liệu thật cùng giàn |

Mô hình A0, A1, C, D: RF 200 cây, cấu hình như TN2. Chỉ dùng tốc độ danh định theo điều kiện.

## Chỉ số

**Chính:** độ đúng 4 lớp theo cửa sổ của từng ổ, trung bình theo ổ trong lớp, rồi macro trên 3 lớp lỗi, trung bình 3 seed. Vì C không có vòng cách, báo thêm macro trên vòng trong và vòng ngoài. Cổng G1b được đọc **trên cả hai**.

**Phụ, mô tả:** đúng loại khi đã biết bất thường; số ổ bỏ phiếu đúng /13; độ đúng bình thường; CI 95% bootstrap theo ổ trong từng lớp. Với 2–3 ổ ở một số lớp, CI phải đọc thận trọng.

## Phân tích phụ cho vận hành thời gian thực (không đổi kết luận G1b)

1. **Lọc theo thời gian:** xác suất trung bình trượt K=5 và EMA α=0,3 trên dòng cửa sổ theo thứ tự thời gian, so với từng cửa sổ riêng lẻ.
2. **Mô hình gọn trên A0:** RF 50 cây sâu 8; hồi quy logistic. Đo cỡ tệp và độ trễ một luồng cho cửa sổ 2 trục. Mục tiêu v1.4: < 100 ms và < 5 MB. Đo trên laptop, không phải Pi 5.
3. **Đặc trưng giữa hai trục** (tỉ lệ năng lượng, tương quan, coherence, xung đồng thời) trên A0. Lỗi cấy dùng cùng dạng sóng cho 2 trục với tỉ lệ biên độ ngẫu nhiên, nên có thể lệch so với thực tế.
4. **MiniRocket** nếu cài được không phá phiên bản đã ghim.

## Quy trình

Chạy thử trên 1_5 và 3_2 → freeze hash → chạy 13 ổ một lần, từ chối chạy lại. Không đổi cấu hình theo kết quả.

## Giả định và giới hạn đã biết

- Đơn vị XJTU-SY coi là g. Cuối đời biên độ lớn, nên ±8 g sẽ cắt đỉnh tín hiệu thật.
- Thử nghiệm tăng tốc, tải rất lớn so với máy thường. Nền đầu đời có thể đã chứa chạy rà.
- 10% cuối đời có thể đã hỏng nặng, dễ hơn giai đoạn sớm. **Không suy ra độ nhạy ở lỗi sớm.**
- Vòng ngoài chiếm 8/13 ổ; vòng trong và vòng cách rất ít.
- Tất cả ổ cùng giàn thử, cùng loại ổ bi.

## Nhật ký trước freeze

- Chạy thử trên 1_5 và 3_2: đường ống chạy đủ các nhánh; cổng chất lượng loại một số mẫu do bão hòa. Không có dự đoán loại lỗi nào được tính trên 13 ổ test.
- MiniRocket không chạy: `aeon` 1.6.0 buộc hạ `numpy` 2.4.4 xuống 2.3.5 và đổi `pandas`, phá phiên bản đã ghim.
