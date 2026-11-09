# T nested: chọn augmentation bằng ổ bi huấn luyện

Chốt sau khi xem T readiness, trước khi chạy nested ngày 05/11/2026.
Đây là cải tiến thăm dò trên dữ liệu đã xem; không biến XJTU thành test mới.

Giữ nguyên T: RF, features45, sensor8g, target khỏe 1–5 để train và 6–10
để test, terminal10 và preterminal10; 13 outer bearings, 3seeds. Chính sách
quyết định argmax cả lớp khỏe, không ngưỡng score thêm (`selective_0`).
Không gọi score là xác suất đúng và không dùng chính sách này để chứng nhận
máy an toàn hoặc phát hiện lớp lỗi chưa biết.

Ứng viên real, surrogate, severity, transport; synthetic mass0.25. Trong mỗi
outer fold, giữ kín mọi lỗi outer target. Với từng trong 12 donor bearings,
giữ nó làm inner validation, train trên 11 donor còn lại; tham chiếu khỏe
inner lấy 1–5, kiểm tra khỏe 6–10. Sinh cho inner chỉ dùng dữ liệu inner khỏe
1–5 và dữ liệu của donor inner train. Cả outer target lẫn inner target đều
không xuất hiện trong danh sách donor inner train.

Chọn theo terminal macro recall inner, với điều kiện tỷ lệ gán lỗi trên
healthy inner trung bình theo bearing không quá 5%. Nếu real đủ điều kiện,
chỉ dùng dữ liệu sinh khi gain inner ít nhất 2 điểm phần trăm; ngược lại
giữ real. Nếu real không đủ điều kiện, chọn ứng viên đủ điều kiện tốt nhất.
Nếu không ứng viên nào đủ điều kiện, giữ real và đánh dấu selection không
đạt tiêu chí healthy. Ties giữ ứng viên đứng trước trong danh sách trên.
Đây là quy tắc heuristic đã chốt, không phải bảo đảm thống kê.

Sau lựa chọn, lấy prediction outer tương ứng từ T đã chạy cùng cấu hình.
Chỉ đọc outer prediction để chấm sau khi lựa chọn đã ghi vào selection.json.
Kiểm tra hash T và cache trước và sau. T không huấn luyện trên lỗi target.
Real, surrogate, severity, transport cố định được báo cạnh selector; không
thay baseline theo từng fold. Báo cả gain CI, recall từng lớp, preterminal,
healthy false fault và số fold đã chọn từng ứng viên. Không chọn lại theo
điểm outer. Thiếu bôi trơn và dị vật vẫn chưa được kiểm chứng.
