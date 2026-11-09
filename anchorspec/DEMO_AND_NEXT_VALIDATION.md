# Demo nghiên cứu và phép thử tiếp theo

Cập nhật tiếp 06/11/2026: [cải tiến học sâu chạy CPU](CAI_TIEN_DL_CPU_20261106.md)
và [Excel so sánh 25 cấu hình](results/s3/AnchorSpec_CPU_Benchmark_20261106.xlsx).
Flow học phần dư phổ quanh mẫu thật đạt 77,22% recall, vòng cách 41,67%, không
ghi nhận gán lỗi trên các đoạn giả định khỏe. Kết quả cũ của flow đủ hạng là
64,81% và vòng cách 0%. Chưa chứng minh thắng chắc surrogate: CI vẫn chứa 0.
Mạng mới 9.688 tham số, 16 bước, CPU một luồng. Cache giữ chính xác đặc trưng
và score trên 78 lượt mô hình; giảm khoảng 29% tổng thời gian trong phép đo
cục bộ chạy xen kẽ. Đã qua 136 kiểm tra. Không thay runtime mặc định.
Lệnh `python s3_generate_cpu.py` xuất mẫu và nguồn gốc từ checkpoint công khai.
Đọc [handoff S3](HANDOFF_S3_CPU_20261106.md) trước khi tiếp tục nghiên cứu.

Cập nhật 06/11/2026: [mẫu thật cộng mẫu sinh, diffusion và flow matching](KET_QUA_REAL_CONG_GEN_20261106.md).
Đã giữ nguyên cả mẫu thật lẫn trọng số, thử ba mức số lượng và hai mức trọng số
mẫu sinh. Surrogate đạt 74,26%, trộn nền 77,22%, bản sao 72,64% so với real
68,33% ở liều đặt trước. Hai prototype học sâu chưa vượt surrogate, kể cả
sau ablation PCA đủ hạng. 128 kiểm tra đạt; chưa thay runtime mặc định.

Cập nhật mới nhất 05/11/2026: [đánh giá sẵn sàng DENSO](DANH_GIA_SAN_SANG_DENSO_20261105.md)
và [PowerPoint tám trang](results/t/AnchorSpec_Bang_chung_va_gioi_han_20261105.pptx).
Đã bổ sung cảnh báo giả, lỗi chưa học, lựa chọn augmentation bằng inner folds
và ghép nguồn UORED với XJTU. Căn chỉnh nền khỏe tăng điểm mẫu thật nhưng CI
còn chứa 0; dữ liệu sinh và ghép nguồn chưa thắng ổn định. 116 kiểm tra đạt.
Chưa đổi mặc định runtime hoặc xác nhận khả năng chẩn đoán trong nhà máy.

Cập nhật 04/11/2026: xem [bộ kết quả và demo mới](KET_QUA_VA_DEMO_20261104.md).
Đã đối chứng surrogate với physics trên UORED, thử biểu diễn phổ, chạy nguồn
KAIST mới và thêm cổng chất lượng tín hiệu. Có HTML tương tác và PowerPoint
mười slide. Nhánh phân tầng tăng macro recall ở lỗi đang phát triển từ70,3%
lên81,1% nhưng giảm ở lỗi nặng. Chưa đạt tiêu chí phương pháp vượt trội toàn diện; không lấy điểm
hai lớp KAIST thay cho các lớp lỗi còn thiếu của DENSO.

Cập nhật 03/11/2026: phát triển tiếp bằng dữ liệu công khai theo yêu cầu. Đã tải
nguồn về trạng thái mỡ, ổ kim không bôi trơn và ổ trượt; đã chạy hai phép thử.
Xem [dữ liệu mở và kết quả](DU_LIEU_MO_VA_KET_QUA_20261103.md). Dữ liệu nhà máy
không phải điều kiện để tiếp tục nghiên cứu; vẫn cần phân biệt nghiên cứu công
khai với xác nhận hiệu quả tại địa điểm triển khai.

## Câu chuyện nên trình bày

AnchorSpec giúp khai thác nền khỏe và ít sự kiện bảo trì đã xác nhận để xây dựng
giả thuyết về loại lỗi. Mỗi lần thêm một sự kiện phải kiểm tra xem kết quả có cải
thiện trên ổ khác hay không. Dữ liệu tổng hợp là một nguồn hỗ trợ có thể giảm hoặc
bỏ đi khi bằng chứng thật không ủng hộ, không phải nguồn chân lý mặc định.

Hiện demo phù hợp để trình bày cách tiếp cận và kết quả nghiên cứu. Chưa có bằng
chứng cho một hệ thống chẩn đoán đầy đủ đã sẵn sàng triển khai nhà máy.

## Bảy phần của pipeline dự kiến

| Phần | Mô tả ngắn | Tình trạng |
|---|---|---|
| 1. Nền khỏe của máy | Ghi lại dữ liệu khỏe và điều kiện đo để tạo mốc so sánh cho máy đó. | Đã có trên benchmark; chưa có quản lý chế độ nhà máy |
| 2. Giả thuyết vật lý | Tạo tín hiệu lỗi vòng trong và vòng ngoài qua mô hình cảm biến rồi trích đặc trưng. | Đã có; loại lỗi khác chưa được xác nhận |
| 3. Sự kiện đã xác nhận | Lưu tín hiệu và kết luận kiểm tra linh kiện theo từng sự kiện độc lập. | Có đối tượng Event và kiểm tra nguồn; chưa có ứng dụng bảo trì |
| 4. Chọn và huấn luyện | Giữ lại nguyên ổ donor để chọn biểu diễn, mô hình và mức dùng dữ liệu tổng hợp. | Đã triển khai RF, SVM và đối chứng chỉ dùng dữ liệu thật |
| 5. Tiếp nhận bất thường | Nhận cửa sổ rung cùng cờ bất thường từ hệ thống phía trước. | Có API cờ vào trong nhánh diagnostic; chưa nối hệ thống thật |
| 6. Đề xuất loại lỗi | Tính đặc trưng và xếp giả thuyết lỗi trong tập đã có bằng chứng. | Đã chạy offline; chưa có unknown detector đạt mục tiêu |
| 7. Theo dõi và phản hồi | Lưu diễn biến, kết quả kiểm tra và phiên bản mô hình để đánh giá lần cập nhật sau. | Có log thí nghiệm và script mức trạng thái; chưa tích hợp liên tục |

Các phần một đến bốn thuộc khâu xây dựng mô hình; các phần năm đến bảy thuộc
vận hành. Kết luận bảo trì ở phần bảy quay lại bổ sung phần ba. Không cần sinh lỗi
hay chạy chọn cấu hình mỗi khi có một cửa sổ mới.

## Một buổi demo ngắn

1. Mở biểu đồ học theo sự kiện trong `results/y/event_learning.png`, nói rõ đây là
   dữ liệu công khai và số sự kiện độc lập, không phải số cửa sổ.
2. So mô hình chỉ cấy, chỉ lỗi thật và ghép hai nguồn trên cùng các ổ kiểm tra.
3. Mở một kết quả lưu có danh sách donor và hash code để giải thích cách tránh
   học nhãn lỗi của chính ổ đang kiểm tra.
4. Cho xem một trường hợp không cải thiện hoặc nhãn bị hoán vị; giải thích vì sao
   cần xác nhận kết luận sửa chữa trước khi cập nhật.
5. Phân biệt điểm chẩn đoán khi đã biết có lỗi với điểm toàn pipeline; không dùng
   giả định bộ phát hiện hoàn hảo để khẳng định đã hết bỏ sót và báo nhầm.

## Những phát biểu hiện chưa có bằng chứng

Chưa chứng minh nhận được thiếu bôi trơn hay dị vật; chưa chứng minh phân loại
mọi lỗi ngoài danh sách; chưa có dự báo giờ hỏng đáng tin; chưa đo báo nhầm nhiều
ngày cùng máy; chưa đo toàn pipeline trên Pi với cảm biến thật. Xác suất RF và
điểm SVM chưa được hiệu chỉnh thành độ tin cậy có thể dùng cho quyết định vận hành.

## Thử nghiệm cần thiết để đi tiếp

Thứ tự hợp lý là chốt tín hiệu cảm biến và điểm nối hệ thống hiện hữu, lấy các
phiên khỏe độc lập theo điều kiện vận hành, thu sự kiện có xác nhận linh kiện,
chốt tập kiểm tra giữ lại rồi mới chạy phương pháp đã khóa cấu hình. So với cả
mô hình hiện hữu lẫn mô hình chỉ học lỗi thật, cùng ngân sách sự kiện và cùng
băng thông. Tính theo sự kiện, báo riêng bỏ sót, báo nhầm, độ bao phủ và từng loại
lỗi; không lấy trung bình đẹp để che một loại lỗi quan trọng bị bỏ qua.

Đối với thời gian suy giảm, cần chuỗi theo dõi tới sự kiện thay hoặc hỏng có
timestamp và tiêu chí kết thúc thống nhất. Các bản ghi ngắn chỉ có nhãn khỏe và
hỏng không đủ để suy ra số giờ còn lại. Trạng thái theo dõi chỉ nên hỗ trợ ưu tiên
kiểm tra cho đến khi có dữ liệu kiểm định tiên lượng.

XJTU-SY đã được kiểm tra trong đợt U ngày05/11. Đã sửa đối chứng sao chép,
đánh giá một trục và surrogate đồng bộ hai trục. Xem
[báo cáo ổ hỏng tự nhiên](KET_QUA_O_BI_TU_NHIEN_20261105.md) và
[handoff U](HANDOFF_U_20261105.md). Có cải thiện có phạm vi; chưa thắng ổn định.

KAIST đã được kiểm tra trong đợt W và V; không còn là tập chưa xem. Đợt V bổ sung
HUST và kiểm tra riêng loại ổ6204, nhưng chưa chứng minh dữ liệu sinh thắng ổn
định. Xem [báo cáo V](KIEM_CHUNG_DU_LIEU_SINH_20261104.md) và
[handoff V](HANDOFF_V_20261104.md). [UNSW run-to-failure](https://data.mendeley.com/datasets/h4df4mgrfb/3)
vẫn là nguồn cần đánh giá tính phù hợp trước khi thiết kế phép thử mới.
