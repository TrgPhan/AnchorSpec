# W: đối chứng nguồn dữ liệu và AnchorSpec Select, 04/11/2026

Viết trước khi chạy kết quả W. UORED đã được xem nhiều lần: toàn bộ W là nghiên
cứu phát triển, không phải xác nhận độc lập hay chứng minh vượt SOTA.

## Câu hỏi và phương pháp

So real-only, real cộng constrained surrogate, real cộng cấy lỗi vật lý trong
cùng nhiệm vụ chẩn đoán bốn loại lỗi, giả định đầu vào thực sự bất thường. Không
được gọi điểm này là độ chính xác toàn pipeline. So surrogate chỉ hai lớp vòng
trong/ngoài (ngân sách nhãn giống physics) và surrogate cả bốn lớp (khả năng mở
rộng thực tế). Mỗi nguồn tổng hợp tối đa 150 cửa sổ mỗi lớp. Trộn tổng hợp 50%
trọng số lớp được bổ sung, sự kiện thật 50%; lớp khác hoàn toàn dùng dữ liệu thật.

AnchorSpec Select chọn nguồn và mô hình bằng validation trên nguyên ổ donor.
Không bắt buộc chọn dữ liệu sinh. Cấu hình nguồn cố định cũng được chọn mô hình
với cùng không gian: RF50, RBF SVM C=1 hoặc 10, hồi quy ridge alpha=1; đặc trưng
raw hoặc độ lệch so nền khỏe (delta). Đây là các thành phần có sẵn, không tuyên
bố phát minh bộ phân loại mới. z theo std riêng rất nhỏ được giữ trong đối chứng
RF lịch sử, không dùng trong nhánh mới. Mô hình mới chỉ học các lớp lỗi vì
nhiệm vụ là chẩn đoán sau cờ bất thường. Không dùng dữ liệu test để chọn cấu hình.

## Chia dữ liệu và tính công bằng

- 20 ổ UORED; bỏ toàn bộ lỗi ổ đích khỏi huấn luyện. Nền khỏe ổ đích được dùng.
- Seeds 11,29,47; mỗi lớp 1,2,4 sự kiện donor; cùng donor với thí nghiệm Y.
- Chỉ state 2 donor được học/sinh surrogate. state 1 và state 2 ổ đích đều test.
- Các derivatives của donor validation phải bị loại khỏi training của fold đó.
- Nếu mỗi lớp chỉ một donor, không thể validation vẫn đủ lớp. Khi đó dùng raw
  SVM C=1 cho mọi nguồn, Select dùng real-only; không giả vờ đã chọn bằng CV.
- Hai sự kiện dùng hai fold, bốn dùng bốn fold; mọi lớp có mặt ở train mỗi fold.
- RF cùng 50 cây. SVM trọng số tổng bằng số cửa sổ THẬT, không tăng C hiệu dụng
  chỉ vì có thêm dữ liệu sinh. Tổng trọng số lớp bằng nhau, donor bằng nhau.
- Tie chọn real, surrogate_ring, physics, surrogate_all; rồi RF, SVM1, SVM10,
  ridge; rồi raw trước delta. Log toàn bộ lựa chọn và danh tính fold.
- Surrogate dùng đúng hàm constrained_surrogate cũ, 30 vòng, phase_bound .65.
  Không thêm quality filter riêng vì đang so lợi ích nguồn sinh, không so bộ lọc.
- Physics dùng cache cùng generator Y (150 mẫu mỗi lớp inner/outer); không
  gọi công thức cage/lube/foreign chưa được xác nhận.

## Tiêu chí và giới hạn

Chỉ số chính: macro recall late, trung bình seed trước rồi trung bình theo ổ
và lớp. Báo early, từng lớp, độ đúng bỏ phiếu sự kiện, chi phí fit, bytes model.
So Select với từng đối chứng bằng paired bootstrap theo ổ, 5000 lần; các
khoảng này chưa hiệu chỉnh nhiều so sánh. Không chọn chỉ vài ổ đẹp để báo cáo.
"Vượt trội" chưa đạt trừ khi hơn real và surrogate ít nhất 5 điểm phần trăm,
CI dưới dương, không lớp nào giảm quá 5 điểm và được xác nhận trên nguồn mới
phù hợp với claim. W riêng lẻ không thỏa điều kiện xác nhận nguồn mới.

Không đo báo nhầm nhà máy, RUL, lỗi chưa biết hoặc hardware Pi bằng W. Code,
cache, thư viện cũ, protocol được hash; log từng task để phục hồi, không thay
cấu hình sau khi nhìn thấy kết quả rồi ghi đè kết quả cũ.
