# Benchmark đầy đủ và ưu tiên khi thử trong nhà máy

Ngày 06/11/2026. Đây là bộ kết quả công khai và kế hoạch kiểm chứng; chưa phải benchmark thực địa DENSO.

[Mở Excel đầy đủ](results/factory_benchmark/AnchorSpec_Full_Benchmark_20261106.xlsx). [CSV mọi cấu hình](results/factory_benchmark/all_configurations.csv).

## Ưu tiên của phương án đưa vào nhà máy

Đề xuất sinh dữ liệu và kiểm chứng offline; đưa bộ chẩn đoán đã xác nhận vào thử nghiệm song song với kỹ thuật viên. Bộ sinh không cần chạy theo từng cảnh báo nếu chỉ phục vụ huấn luyện. Ngưỡng nghiệm thu phải chốt với đơn vị vận hành theo chi phí bỏ sót, chẩn đoán nhầm và kiểm tra thêm.

| Ưu tiên | Tiêu chí | Đo bằng gì | Bằng chứng hiện có |
|---|---|---|---|
| 1 | Đúng loại lỗi cần xử lý | Recall từng lỗi; bỏ sót sự kiện; mức nhầm lẫn giữa nguyên nhân | Có XJTU inner, outer, cage; thiếu bôi trơn và dị vật chưa xác nhận. |
| 2 | Không tăng chẩn đoán sai sau cảnh báo | Gán lỗi trên cảnh báo giả; precision theo tần suất thực; số lượt kiểm tra sai mỗi ca | Có healthy stress giả định; chưa có cảnh báo upstream DENSO. |
| 3 | Giá trị tăng thêm do mẫu sinh | Gain và CI so real, bản sao và surrogate cùng budget | Đã có matched controls và paired CI thăm dò. |
| 4 | Giữ hiệu quả khi đổi máy và chế độ | Worst-regime recall; chênh lệch theo tải, RPM, ngày đo, sensor mounting | Có các thử nghiệm cũ khác tải và nguồn; S/S2 chỉ XJTU. |
| 5 | Tín hiệu và nhãn sinh có căn cứ | PSD, phổ bao, RMS, kurtosis, clipping, gần bản sao, đa dạng trong cùng fault | Có reconstruction, clipping và một kiểm tra tương quan zero-lag; chưa có xác nhận cơ khí mẫu sinh. |
| 6 | Biết giới hạn khi gặp lỗi chưa học | Gán nhầm lỗi lạ thành lớp đã biết; coverage; recall tính cả từ chối | T có missing-cage stress; chưa chạy unknown cho S/S2. |
| 7 | Tài nguyên và khả năng truy vết | Fit time, sampling time, model size; latency p95 chẩn đoán; hash, lineage, rollback | Có fit và profile lấy mẫu trên máy phát triển; chưa đo Raspberry Pi hoặc máy nhà máy. |
| 8 | Lợi ích vận hành | Giờ dừng máy tránh được, công kiểm tra, chi phí bảo trì, thời gian xử lý cảnh báo | Chưa có pilot đối chiếu vận hành DENSO. |

Các ưu tiên trên là đề xuất cho AnchorSpec. NIST nhấn mạnh xác minh, xác nhận và phép đo phục vụ độ tin cậy, giảm downtime; ISO17359 đưa khung chung cho chương trình theo dõi tình trạng máy. Không coi bảng này là tiêu chuẩn nghiệm thu do DENSO ban hành.

[NIST PHM4SM](https://www.nist.gov/programs-projects/prognostics-and-health-management-reliable-operations-smart-manufacturing-phm4sm). [ISO17359](https://www.iso.org/standard/71194.html).

## Thông số cần xác nhận trước khi sinh

| Nhóm | Cấu hình hiện tại | Việc phải xác nhận tại nhà máy |
|---|---|---|
| Cảm biến đầu vào | Mô phỏng lấy mẫu 4 kHz, băng thông 1 kHz, dải 8 g, độ phân giải 20 bit | Xác nhận mã cảm biến, đơn vị, chống alias, vị trí lắp và dải đo thực. |
| Loại lỗi | Vòng trong, vòng ngoài, vòng cách trên XJTU | Xác nhận nhãn thiếu bôi trơn, vòng cách, dị vật bằng hồ sơ kiểm tra hoặc bảo trì. |
| Điều kiện vận hành | Điều kiện sinh gồm tốc độ nguồn và RMS của tín hiệu khỏe | Ghi tốc độ, tải, công đoạn, nhiệt độ, hình học ổ; có mẫu khỏe đối chiếu theo chế độ. |
| Số lượng và trọng số | Thêm 60, 120 hoặc 240 mẫu; alpha bằng 0.25 hoặc 1; giữ nguyên 125 mẫu thật | Chọn bằng tập validation tách theo sự kiện. Giữ kín tập test; thêm nhiều mẫu chưa chắc tốt hơn. |
| Kiến trúc bộ sinh | MLP ba lớp ẩn, mỗi lớp 128 nút; 1.500 bước cập nhật; PCA 32 hoặc 119 thành phần và log RMS | Đánh giá đặc trưng vật lý và hiệu quả chẩn đoán; kết quả prototype không đại diện toàn bộ họ mô hình. |
| Lấy mẫu | Flow matching dùng 50 bước Euler; DDPM dùng 100 bước với lịch cosine | Tối ưu chi phí sinh sau khi đã xác nhận lợi ích. |
| Đề xuất triển khai | Chưa triển khai lên hệ thống sản xuất | Sinh và kiểm chứng offline; thử bộ chẩn đoán song song để kỹ thuật viên đối chiếu trước khi sử dụng cho quyết định vận hành. |

## Bảng cùng số lượng và trọng số mẫu sinh

Mỗi lượt có 125 mẫu thật; các nhánh tăng cường thêm 120 mẫu ở alpha bằng 0.25. Nhánh chỉ dùng mẫu thật vẫn có 125 mẫu. Alpha là trọng số mỗi mẫu thêm so với mẫu thật của cùng ổ nguồn. Điểm là recall trung bình theo ổ và loại lỗi; bộ phân loại được phép chọn lớp khỏe. Giữ thứ tự đối chứng và phương pháp, không chọn cấu hình theo điểm test cao nhất.

| Phương pháp | Recall trước cuối | Recall cuối | Inner | Outer | Cage | Gán lỗi healthy | Gain so bản sao |
|---|---:|---:|---:|---:|---:|---:|---:|
| Mẫu thật | 58.75% | 68.33% | 93.33% | 100.00% | 11.67% | 0.00% | Không áp dụng |
| Thêm bản sao | 68.06% | 72.64% | 86.67% | 99.58% | 31.67% | 0.00% | +0.00 điểm |
| Surrogate cũ | 64.17% | 74.26% | 91.11% | 100.00% | 31.67% | 0.00% | +1.62 điểm |
| Surrogate giữ đường bao | 65.46% | 74.07% | 85.56% | 100.00% | 36.67% | 0.00% | +1.44 điểm |
| Trộn nền cùng ổ | 69.91% | 77.22% | 83.33% | 100.00% | 48.33% | 1.03% | +4.58 điểm |
| PCA32 dựng lại | 58.43% | 62.96% | 88.89% | 100.00% | 0.00% | 0.00% | -9.68 điểm |
| Flow matching PCA32 | 53.70% | 61.06% | 81.11% | 98.75% | 3.33% | 0.00% | -11.57 điểm |
| Diffusion PCA32 | 53.56% | 63.15% | 91.11% | 98.33% | 0.00% | 0.00% | -9.49 điểm |
| PCA đủ hạng dựng lại | 69.91% | 75.79% | 87.78% | 99.58% | 40.00% | 0.00% | +3.15 điểm |
| Flow matching đủ hạng | 59.68% | 64.81% | 94.44% | 100.00% | 0.00% | 0.00% | -7.82 điểm |
| Diffusion đủ hạng | 59.86% | 66.30% | 98.89% | 100.00% | 0.00% | 0.00% | -6.34 điểm |

Gán lỗi trên dữ liệu khỏe được đo trên 65 đoạn tín hiệu giả định khỏe, lặp lại theo seed. Đây không phải số cảnh báo giả mỗi giờ của detector DENSO. Chỉ có hai ổ lỗi vòng cách. Khoảng tin cậy của mức cải thiện so với bản sao và surrogate có trong Excel; điểm cao nhất chưa có nghĩa là thắng chắc.

Trộn nền cùng ổ tăng 4.58 điểm phần trăm so với thêm bản sao, nhưng khoảng tin cậy 95% từ -5.79 đến +14.81 điểm vẫn chứa 0. PCA đủ hạng dựng lại tín hiệu gần như chính xác trước bước giới hạn biên độ; sau giới hạn 8 g và lượng tử hóa, tín hiệu vẫn thay đổi. Vì vậy, mức tăng của nhánh PCA không chứng minh đã học được cơ chế lỗi mới.

## File Excel gồm những gì?

| Sheet | Số dòng dữ liệu | Nội dung |
|---|---:|---|
| README | 22 | Định nghĩa, đơn vị, cách chia và giới hạn |
| Priorities | 8 | Ưu tiên và tiêu chí đề xuất |
| Settings | 7 | Thông số dữ liệu, cảm biến và bộ sinh |
| Primary | 11 | Cấu hình đặt trước, đầy đủ 11 nhánh |
| All_configs | 122 | 61 cấu hình, hai chính sách quyết định, recall từng lớp, khoảng tin cậy và F1 mô tả |
| Per_bearing | 1586 | Trung bình seed trong từng ổ |
| Per_seed | 4758 | Kết quả từng ổ và seed |
| Confusion | 4392 | Ma trận nhầm lẫn trên mẫu khỏe và mẫu cuối vòng đời |
| Quality | 6 | Codec, giới hạn biên độ, thời gian huấn luyện |
| Quality_folds | 234 | Chi tiết chất lượng từng lượt |
| Sampling_CPU | 4 | Đo lấy mẫu trên máy phát triển, chưa đo trên Pi |
| Unknown_T | 50 | Thử lỗi chưa học của T, không gán cho S và S2 |
| History | 987 | 987 dòng kết quả từ các đợt W, V, U và T |
| Sources | 133 | Nguồn và SHA256 |

Macro F1 và accuracy trên mẫu khỏe cùng mẫu cuối vòng đời là chỉ số mô tả bổ sung, tính từ ma trận nhầm lẫn gộp ba seed với 585 lượt dự đoán. Chỉ có 195 đoạn tín hiệu riêng biệt, gồm 65 đoạn giả định khỏe và 130 đoạn cuối vòng đời. Những đoạn trong cùng ổ có liên quan với nhau; đơn vị đánh giá độc lập là 13 ổ, không phải 585 lượt dự đoán. Tần suất lớp trong benchmark không đại diện tần suất lỗi nhà máy.

[Kho toàn bộ chỉ số lịch sử](results/overview/archive_metrics.csv) giữ 260.124 giá trị từ 127 file kết quả, bao gồm các lượt CWRU trước đây. [Báo cáo lịch sử](TOAN_BO_KET_QUA_VA_SO_SANH_20261105.md) giải thích từng nhóm so sánh. Các kết quả khác dataset, cách chia hoặc chỉ số không được gộp thành một bảng xếp hạng.

## Tốc độ và chi phí

Đo lại bốn checkpoint của fold 1_1, seed 11 trên CPU một luồng: mỗi lần sinh 120 tín hiệu, mỗi tín hiệu 4.000 điểm; chạy khởi động một lần và đo mười lần. Không gồm đọc file, huấn luyện hoặc suy luận bộ phân loại. P95 chỉ mô tả mười lần đo trên máy phát triển, chưa phải cam kết độ trễ tại nhà máy.

| Prototype | Đợt | Sinh và dựng lại 120 mẫu, trung vị | P95 | Tính 45 đặc trưng, trung vị | Checkpoint |
|---|---|---:|---:|---:|---:|
| flow | s | 0.0196s | 0.0217s | 0.1585s | 177.3KiB |
| diffusion | s | 0.0392s | 0.0427s | 0.1609s | 177.8KiB |
| flow | s2 | 0.0231s | 0.0253s | 0.1584s | 265.2KiB |
| diffusion | s2 | 0.0503s | 0.0538s | 0.1592s | 265.7KiB |

Sinh nhanh không bù được việc chẩn đoán sai. Kích thước trên đây là checkpoint bộ sinh, không phải tổng RAM, thư viện chạy mô hình hoặc kích thước bộ chẩn đoán triển khai.

## Chưa có benchmark nào?

- Hiệu quả trên dữ liệu DENSO với nhãn bảo trì xác nhận và đầu ra upstream thật.
- Thiếu bôi trơn, dị vật và các lỗi chưa học đối với chính các mô hình S và S2.
- False alarms theo giờ hoặc ca, latency trên thiết bị mục tiêu, độ tin cậy qua nhiều ngày và lần lắp sensor.
- Số giờ tới hỏng, downtime tránh được hoặc chi phí bảo trì tiết kiệm.

Các ô chưa có bằng chứng không được điền 0. Bộ hiện tại đủ so sánh nghiên cứu có đối chứng, chưa đủ tuyên bố áp dụng tự động trong nhà máy.

## Tái lập

```powershell
python factory_sampling_profile.py
python factory_benchmark_report.py
```

[Toàn bộ bảng lịch sử](TOAN_BO_KET_QUA_VA_SO_SANH_20261105.md). [Báo cáo S và S2](KET_QUA_REAL_CONG_GEN_20261106.md).
