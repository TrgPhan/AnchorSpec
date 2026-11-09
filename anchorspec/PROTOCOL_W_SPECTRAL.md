# Bổ sung W-Spectral, 04/11/2026

Sau khi thấy W Select không hơn đối chứng, thử một giả thuyết mới có phạm vi rõ:
45 đặc trưng thiên về công thức vòng trong/ngoài có thể thiếu dấu hiệu phổ của
bi/vòng cách. Không thay sensor hay labels; chỉ thay biểu diễn trên chính rung
4 kHz, băng thông1kHz. Không sử dụng microphone như trục rung thứ hai.

Tạo 128 bin log phổ công suất chuẩn hóa trong0 đến1kHz và64 bin log phổ bao
hình trong0 đến500Hz; Welch nperseg1024, pooling hai bin. Bao hình Hilbert sau
lọc300 đến1000Hz. Cộng4thống kê vô hướng crest,kurtosis,skew,shape. Đặc trưng
raw và delta trừ mean nền khỏe. Cùng donor và các outer test với Y/W.

Ba ứng viên view: original45, spectral196, concatenate241. Inner CV theo ổ,
RF50,RBF SVM C1,C10,ridge1,raw/delta. Không thêm dữ liệu sinh. Chọn trên donor,
fallback raw SVM1 original45 khi mỗi lớp một sự kiện; folds đủ lớp mới chọn.
Mọi điểm vẫn exploratory trênUORED đã xem; không chọn trên test và không giấu
view nào. Báo so với DiagnosticExperts real-only Y và mọi kết quả W.

Không gọi đây là vượt SOTA; spectral features và bộ phân loại là thành phần
chuẩn. Nếu tăng chỉ trên dữ liệu đã xem, cần thêm nguồn bốn lớp phù hợp trước
khi tuyên bố ưu thế tổng quát. Lưu source/protocol hash và kết quả riêng.
