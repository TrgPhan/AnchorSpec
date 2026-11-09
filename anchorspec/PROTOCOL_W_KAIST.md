# KAIST: nguồn mới, đổi tải và giữ lại mức khuyết tật, 04/11/2026

Protocol viết trước khi đọc waveform KAIST. SourceSelector được khóa như W;
không đổi phương pháp từ kết quả UORED W hoặc KAIST. Tất cả nguồn dùng cùng
classifier search, cùng target healthy. Báo mọi split, không chỉ split thắng.

Nguồn: https://data.mendeley.com/datasets/ztmf3m7h5x/6, CC BY 4.0.
Paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC10036499/.
Chọn 21 MAT rung: ba healthy, 18 fault inner/outer, ba severity 03/10/30,
ba tải 0/2/4 Nm. Không dùng acoustic/current/temp. Download range ZIP kiểm
CRC từng member, SHA256 local; không xác nhận SHA256 toàn ZIP chưa tải đủ.

Một trục x housing A (cột thứ hai theo paper), g, fs25600, NSK6205DDU:
n=9,d=7.90,D=38.5,phi=0,fr=3010/60. Giả lập CheapSensor mặc định, bỏ giây
đầu, lấy tối đa 60 giây tiếp theo mỗi tệp, cửa sổ 1 giây không chồng lấn.
Nếu MAT dạng export Siemens, đọc đúng Time và Signal, kiểm dt/cột theo metadata;
không suy đoán mảng đầu tiên là waveform. Healthy dùng giây1 đến31 để lấy nền.

18 outer splits: source_load khác target_load (6 cặp), giữ lại một severity
(3 lựa chọn). Huấn luyện bốn sự kiện: hai severity còn lại cho mỗi loại tại
source_load. Test hai loại tại target_load, severity giữ lại. Bản ghi cùng
severity bị loại khỏi tất cả tải huấn luyện. Không xem cửa sổ là thí nghiệm
độc lập; không khẳng định các mã severity là các ổ vật lý độc lập khi chưa có ID.
Inner CV giữ nguyên sự kiện donor, hai fold. Dữ liệu healthy của target_load
được sử dụng để điều chỉnh nền, tức không phải hoàn toàn zero-shot.

Sinh surrogate chỉ từ bốn sự kiện training (cache mọi tệp được nhưng chỉ truy
cập derivatives train). Physics chỉ từ nền khỏe target. Seeds11,29,47.
Score chính: conditional macro recall inner/outer, trung bình seed rồi đều
theo18split; báo perload/perseverity. Không bootstrap cửa sổ hoặc giả 18 split
độc lập vì dùng chung tệp. Báo min/max split và chênh từng split.

Đây là kiểm tra nguồn mới cho chuyển tải và mức khuyết tật trên cùng giàn;
không xác nhận cage, bôi trơn, dị vật, lỗi lạ, tuổi thọ hoặc DENSO. Không so
trực tiếp phần trăm hai lớp này với macro bốn lớp UORED.

## Bổ sung sau kiểm tra schema, trước trích đặc trưng và kết quả KAIST

MAT thực tế là struct Signal, bốn cột tín hiệu và time start/increment riêng,
khác mô tả năm cột trong bài. Chọn Signal.y_values.values cột0 cho x housing A.
Metadata nói "Data saved by Test.Lab in MKS", nhãn g và unit_transformation
factor=0.101971621297793. Theo metadata, chuyển giá trị MKS bằng nhân factor
để ra g; lưu nguyên factor/offset và tỷ lệ vượt range. Đây là cách diễn giải
metadata, cần đối chiếu tác giả trước triển khai; không tự xem số thô là g.

Thêm đối chứng phụ diagnostic_real Y (mô hình thực tốt nhất trước W), dùng
nguyên code và inner validation như cũ. Quyết định này sau khi xem UORED W,
trước khi tính bất kỳ điểm KAIST nào. Không thay SourceSelector để sửa kết quả W.
