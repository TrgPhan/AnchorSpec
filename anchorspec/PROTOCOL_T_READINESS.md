# T: kiểm tra chẩn đoán khi đầu vào không hoàn hảo

Chốt thiết kế ngày 05/11/2026, trước khi chạy T. Đây là nghiên cứu tiếp nối
trên XJTU-SY đã được xem trong U, không phải tập xác nhận độc lập mới.
Không sửa source hoặc kết quả đóng băng của U, V, W, Y.

## Câu hỏi và đối chứng

Khi module nhận cảnh báo, dữ liệu sinh có cải thiện chẩn đoán mà không tăng
chẩn đoán lỗi sai trên tín hiệu được giả định khỏe? Khi chưa từng học lỗi
vòng cách, module có biết từ chối hay vẫn gán sang lỗi khác?

- 13 ổ bi đơn lỗi XJTU-SY, leave-one-bearing-out, seeds 11, 29, 47.
- Giữ nguyên giả định cảm biến U: một trục, 4 kHz, băng thông 1 kHz, 8 g.
- Target snapshots 1–5 dùng tham chiếu khỏe và huấn luyện lớp khỏe;
  6–10 chỉ đánh giá. Không dùng 6–10 để sinh, chuẩn hóa hay chọn ngưỡng.
- Hai giai đoạn lỗi giữ nguyên U: 10 snapshots trước đoạn cuối và 10 cuối.
  Nhãn cuối đời gán theo teardown; không coi là nhãn từng phút đã xác minh.
- Healthy đầu đời chỉ là giả định. Healthy test khác thời điểm nhưng cùng ổ,
  không phải ca vận hành độc lập; không quy đổi thành số báo nhầm mỗi tháng.
- Đối chứng real, exact duplicate, surrogate cũ, severity và transport.
  Cùng feature, classifier, tập donor và tổng trọng số; phần tổng hợp 0.25.
- RF và SVM1 được chạy đầy đủ. Hướng theo dõi chính là RF severity so với
  RF real và RF surrogate, chọn do kết quả U nên vẫn là thăm dò hậu nghiệm.
- Hai thư viện: closed gồm mọi donor khác target; missing_cage loại toàn bộ
  donor cage. Cấm mọi dữ liệu lỗi target vào huấn luyện và tạo mẫu.

## Quyết định và thước đo

Mọi snapshot đánh giá được coi đã nhận cảnh báo upstream: đây là stress test
module chẩn đoán, không phải đo detector hay hiệu năng hệ thống nhà máy.
Làm mượt nhân quả 5 snapshots, reset giữa từng đoạn. Khoảng cách đo một phút,
không báo độ trễ 5 giây. Tất cả score đều chưa hiệu chỉnh xác suất.

1. Conditional: luôn chọn lớp lỗi có score lớn nhất, như benchmark cũ.
2. Selective: chọn argmax gồm cả lớp khỏe; nếu max score dưới ngưỡng thì
   trả chưa đủ căn cứ. Các ngưỡng cố định 0, 0.5, 0.7, 0.9; không chọn tốt nhất.
   Lớp khỏe chỉ có nghĩa model không ủng hộ một lớp lỗi đã học, không chứng
   nhận máy an toàn. Từ chối không được tính là chẩn đoán đúng lỗi.

Lưu từng score và prediction để tính lại: recall theo lớp, macro recall,
tỷ lệ đưa ra tên lỗi, độ đúng trong các tên lỗi đã đưa ra, tỷ lệ từ chối,
tỷ lệ gán lỗi trên healthy giả định, tỷ lệ gán lỗi đã biết cho cage chưa học.
Trung bình seed trong từng bearing trước khi tổng hợp. Bootstrap ghép cặp
theo bearing và lớp chỉ là CI thăm dò do các tập huấn luyện chồng lấn.
Không lấy số cửa sổ hoặc seed làm số thí nghiệm độc lập.

## Cổng nghiên cứu đặt trước, không phải chuẩn nhà máy

RF severity, closed, ngưỡng 0.5: terminal macro recall ít nhất 0.80;
recall từng lớp ít nhất 0.70; gán lỗi trên healthy giả định không quá 0.05;
gain ít nhất 0.05 so với real, CI thăm dò gain có cận dưới dương;
không kém surrogate; preterminal không giảm quá 0.02 so với real;
missing_cage không gán lớp lỗi đã biết quá 0.10. Phải qua tất cả.
Ngay cả qua cổng này cũng không đủ production: thiếu dữ liệu DENSO, thiếu
xác minh nhãn khỏe và hai lớp thiếu bôi trơn, dị vật; thiếu kiểm tra thiết bị.

## Tái lập

Chạy `python t_readiness.py`, sau đó `python t_report.py` trong anchorspec.
Lưu SHA256 source, protocol và toàn bộ prepared cache dùng trong lần chạy;
kiểm tra lại trước ghi kết quả. Exact duplicate phải cho score giống hệt.
Không có chọn ngưỡng bằng nhãn test hoặc điều chỉnh phương pháp sau khi xem T.
