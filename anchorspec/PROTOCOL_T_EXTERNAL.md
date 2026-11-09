# T external: bổ sung ổ nguồn khác bộ dữ liệu

Chốt sau T nested ngày 05/11/2026, trước khi chạy external. Thăm dò tiếp trên
XJTU đã xem, không gọi đây là xác nhận độc lập hoặc thay primary của U/T.

Câu hỏi: thêm các ổ UORED cùng loại lỗi có giúp khắc phục thư viện vòng cách
quá ít không; nếu có, augmentation có giúp thêm so với cùng thư viện mẫu thật?

Giữ nguyên T outer: 13 ổ XJTU, ba seed, healthy target1–5 train,6–10test,
hai đoạn lỗi10snapshot, RF50depth8, synthetic mass0.25, quyết định cả lớp khỏe
không ngưỡng thêm. Thư viện gồm các ổ XJTU khác target, hoặc thêm toàn bộ15ổ
UORED inner1–5, outer6–10, cage16–20; không dùng ball do không thuộc phạm vi
ba lớp đang kiểm tra. Fault UORED dùng severe, không dùng developing test.

Hai biểu diễn chốt trước: raw45; delta45 trừ mean healthy riêng của mỗi ổ,
không chia std chỉ 5snapshot. Với XJTU dùng healthy1–5 cho mọi ổ; UORED dùng
11cửa sổ healthy đầu của Y (6giây có overlap). Delta cho mẫu sinh dùng mean
healthy của donor. Không gọi phép trừ feature là tạo waveform vật lý.

Đối chứng cả hai thư viện và hai biểu diễn: real, exactduplicate, surrogate,
severity. Không dùng transport xuyên geometry ở lượt này; không giả định
đổi tốc độ đủ chuyển kinematics hai loại ổ bi khác nhau. Surrogate XJTU64mẫu
cacheU; UORED150mẫu cacheW, lấy64đầu sau khôi phụcrawfeature từ healthy norm.
Severity UORED tạo64biếnthể từ severe và healthy của cùng ổ, aUniform(.35,1),
dịch vòng ngẫu nhiên, outputsensor8g; XJTU tái dùng severityT đúng targetseed.
Tất cả donor cân bằng theo lớp và theo ổ với cùng tổng trọng số giữa methods.

Primary mới của lượt này: RF raw, thư viện kết hợp, severity so với real cùng
thư viện. Báo cả real kết hợp so với real XJTU để tách lợi ích thêm dữ liệu.
Delta chỉ là ablation; không chọn representation sau khi xem điểm.
Tổng156groups=13*3*2library*2representation, mỗi nhóm
4models, tổng624fits. Đơn vị bằng chứng vẫn13ổ XJTU, không phải624thí nghiệm.
Lưu prediction, hash input và provenance. Các unit và healthy assumptions
UORED/XJTU giữ nguyên các protocol cũ; thêm UORED không thành dữ liệu DENSO.
