# Benchmark theo bảy ưu tiên nhà máy

Ngày 06/11/2026. Tính từ kết quả đã lưu của AnchorSpec Spectral Residual Flow. Không đổi cấu hình, không chọn lại ngưỡng và không học thêm bộ sinh.

[Excel đầy đủ](results/priorities/AnchorSpec_7_Priorities_20261106.xlsx). [Bảng precision và recall dạng CSV](results/priorities/Class_metrics.csv).

Cấu hình: 125 mẫu thật cộng 120 mẫu sinh, alpha bằng 0,25, flow 16 bước, mức biến đổi 0,5, RF. Đánh giá 13 ổ với ba seed. Macro recall của ba loại lỗi ở đoạn cuối là 77,22%.

## Bảng theo đúng bảy ưu tiên

| Ưu tiên | Kết quả đo được | Giới hạn |
|---|---|---|
| 1. Nhận đúng từng lỗi | Recall vòng trong 90%; vòng ngoài 100%; vòng cách 41,67%. Ổ 2_3 không được chẩn đoán đúng trong cả 10 đoạn cuối ở cả ba seed. | Bỏ sót chẩn đoán theo đoạn và theo ổ, chưa phải số sự kiện nhà máy. |
| 2. Tránh chẩn đoán nhầm | Precision vòng trong 98,78%; vòng ngoài 86,02%; vòng cách 100%. Không gán lỗi trong 195 lượt đánh giá mẫu giả định khỏe. | 195 lượt tương ứng 65 đoạn riêng biệt, không có số kiểm tra sai theo ca. |
| 3. Lợi ích dữ liệu sinh | Recall tăng 8,89 điểm so real, 4,58 so bản sao, 2,96 so surrogate; các CI 95% đều chứa 0. | Bootstrap theo ổ, thăm dò trên bộ dữ liệu đã xem nhiều lần. |
| 4. Ổn định khi đổi điều kiện | Recall theo nhóm vận hành 91,67%; 56,67%; 100%. Vòng cách nhóm 2 đạt 0%. | Nhóm có thành phần lỗi khác nhau; tốc độ và tải đi cùng nhau; chưa phải holdout toàn chế độ. |
| 5. Giữ đặc trưng vật lý | Cosine PSD 0.9826; phổ bao 0.9892; sai lệch RMS tuyệt đối 5.99%. | 84,10% gần nguồn với tương quan trên 0,99; chưa xác nhận cơ chế lỗi độc lập. |
| 6. Xử lý lỗi chưa học | S3 chưa có thử nghiệm loại bỏ một lớp lỗi. Từ chối 0% trong benchmark đóng vì ngưỡng hiện tại bằng 0. | Kết quả missing-cage đợt T được giữ riêng, không gán cho S3. |
| 7. Chi phí vận hành | CPU chẩn đoán một đoạn: trung vị 9.58 ms, P95 10.63 ms; RSS tiến trình cao nhất quan sát 159.9 MiB. | Chưa đo phần cứng DENSO, công kiểm tra, downtime hay chi phí bảo trì. |

## 1. Recall, precision và bỏ sót từng lỗi

Precision tính trên mẫu khỏe cùng mẫu cuối vòng đời. Số đếm là lượt dự đoán gộp ba seed; không phải số mẫu hoặc sự kiện độc lập.

| Loại lỗi | Recall | Precision | F1 | Đúng | Không đúng loại lỗi | Tổng lượt có lỗi đó |
|---|---:|---:|---:|---:|---:|---:|
| Vòng trong | 90.00% | 98.78% | 94.19% | 81 | 9 | 90 |
| Vòng ngoài | 100.00% | 86.02% | 92.49% | 240 | 0 | 240 |
| Vòng cách | 41.67% | 100.00% | 58.82% | 25 | 35 | 60 |

Có 30 đoạn vòng trong, 80 đoạn vòng ngoài và 20 đoạn vòng cách riêng biệt, mỗi đoạn được đánh giá ở ba seed. FN bao gồm nhầm sang lỗi khác hoặc chọn khỏe; không đồng nghĩa bộ báo bất thường phía trước đã bỏ sót.

**Ổ không có chẩn đoán đúng ở bất kỳ đoạn nào trong 10 đoạn cuối, tại cả ba seed: 2_3.** Đây là 1 trong 13 ổ và là 1 trong 2 ổ lỗi vòng cách. Seed 11, 29 và 47 đều bỏ sót đúng một ổ theo định nghĩa này. Không chuyển tỷ lệ này thành số sự kiện bị bỏ sót ở nhà máy.

Ở ổ vòng cách 1_4, số đoạn đúng lần lượt là 10, 10 và 5 trong 10 đoạn cuối; ở ổ 2_3 là 0, 0 và 0. Precision vòng cách 100% đi cùng recall thấp vì mô hình ít đưa ra nhãn vòng cách.

## 2. Chẩn đoán nhầm

- Mẫu giả định khỏe: không có gán lỗi trong 195 lượt đánh giá, tương ứng 65 đoạn riêng biệt từ 13 ổ.
- Vòng trong: 9 lượt bị gán thành vòng ngoài.
- Vòng cách: 30 lượt bị gán thành vòng ngoài, một lượt thành vòng trong, bốn lượt chọn khỏe.
- Vòng ngoài: nhận đúng cả 240 lượt, nhưng precision chỉ 86,02% do nhận nhầm các lỗi khác vào lớp này.

Macro F1 của ba loại lỗi là 81,83%. Nếu cộng lớp khỏe, macro F1 là 86,12% và accuracy gộp là 92,48%; các con số này không thay thế macro recall lỗi 77,22%. Precision phụ thuộc tỷ lệ lớp trong benchmark, chưa đại diện tần suất lỗi tại nhà máy. Chưa có số lượt kiểm tra sai mỗi ca.

## 3. Lợi ích của dữ liệu sinh

| Đối chứng | Tăng macro recall cuối | Khoảng tin cậy 95%, điểm phần trăm |
|---|---:|---:|
| Chỉ mẫu thật | +8.89 điểm | [-2.22; +20.00] |
| Thêm bản sao | +4.58 điểm | [-0.60; +9.77] |
| Surrogate cũ | +2.96 điểm | [-4.44; +10.37] |
| Trộn nền cùng ổ | +0.00 điểm | [-8.89; +11.11] |
| Flow đủ hạng cũ | +12.41 điểm | [-5.93; +30.74] |
| Diffusion đủ hạng cũ | +10.93 điểm | [-5.93; +27.78] |
| Diffusion phần dư mới | +4.40 điểm | [-1.34; +10.14] |

Khoảng tin cậy dùng bootstrap phân tầng theo loại lỗi trên 13 ổ, trung bình seed trước, 5.000 lần lấy lại mẫu. Không coi 39 lượt mô hình là 39 ổ độc lập. Tất cả đối chiếu chính với real, bản sao và surrogate còn chứa 0; chưa xác nhận thắng chắc.

## 4. Ổn định theo điều kiện

| Tốc độ | Tải | Số ổ | Vòng trong | Vòng ngoài | Vòng cách | Macro trên lớp có mặt |
|---|---:|---:|---:|---:|---:|---:|
| 2100 vòng mỗi phút | 12 kN | 4 | Không có lớp này | 100.00% | 83.33% | 91.67% |
| 2250 vòng mỗi phút | 11 kN | 5 | 70.00% | 100.00% | 0.00% | 56.67% |
| 2400 vòng mỗi phút | 10 kN | 4 | 100.00% | 100.00% | Không có lớp này | 100.00% |

Tốc độ và tải thay đổi cùng nhau; các nhóm có thành phần lỗi khác nhau. Nhóm 2400 vòng mỗi phút không có lỗi vòng cách, nên 100% ở đó không chứng minh xử lý được vòng cách tại tốc độ này. Mỗi lượt đã giữ riêng một ổ, nhưng vẫn có ổ cùng chế độ trong train; đây chưa phải kiểm tra giữ riêng toàn bộ chế độ vận hành.

Chưa có phép thử tách riêng theo ngày đo, lần lắp lại cảm biến, vị trí cảm biến hoặc máy DENSO. Thông số nhóm được đối chiếu với ánh xạ thư mục dữ liệu trong tn2b_xjtu.py; [nguồn dữ liệu của tác giả](https://github.com/WangBiaoXJTU/xjtu-sy-bearing-datasets).

## 5. Đặc trưng vật lý và mức gần mẫu nguồn

Đo trên mẫu sinh flow chính so với đúng tín hiệu nguồn được dùng làm nền. Trung bình từ 468 tổ hợp ổ nguồn, fold và seed; các nguồn lặp lại nên không coi là 468 sự kiện độc lập.

| Chỉ số | Giá trị | Cách đọc |
|---|---:|---|
| Cosine phổ công suất | 0.9826 | Gần 1 là hình dạng phổ gần nhau |
| RMSE log phổ chuẩn hóa | 1.114 dB | Sai lệch hình dạng phổ, tách khỏi RMS |
| Cosine phổ bao | 0.9892 | Phổ bao sau bandpass, Hilbert và Welch |
| Tỷ lệ RMS sinh so với nền | 0.9800 | Trung bình biên độ RMS còn khoảng 98.00% |
| Sai lệch RMS tuyệt đối trung bình | 5.99% | Không triệt tiêu sai lệch tăng và giảm |
| Sai lệch kurtosis tuyệt đối trung bình | 0.0675 | Dùng excess kurtosis |
| Tương quan waveform với nền | 0.9942 | Zero-lag, cùng pha nền |
| Tỷ lệ gần nguồn, tương quan lớn hơn 0,99 | 84.10% | Biến thể rất gần mẫu thật |
| Tỷ lệ sao chép số học theo kiểm tra đã nêu | 0.00% | Ngưỡng sai số tuyệt đối 1e-10 |
| Mẫu phải co biên độ để giữ giới hạn đỉnh của nguồn | 11.45% | Co toàn waveform, không cắt từng điểm |
| Tọa độ phần dư bị giới hạn | 9.36% | Tỷ lệ trong 24 tọa độ biến đổi phổ |

Các con số cho thấy tín hiệu sinh bám sát nguồn. Chúng không chứng minh sinh được lỗi cơ khí mới. Không cắt đỉnh từng điểm lần nữa không có nghĩa nguồn ban đầu không bị bão hòa; bão hòa cảm biến trong nguồn vẫn chưa được giải quyết.

## 6. Lỗi chưa học

S3 chưa được chạy trong điều kiện loại bỏ một lớp lỗi khỏi cả bộ sinh và bộ phân loại. Vì thế chưa tính được tỷ lệ gán nhầm lỗi lạ. Tỷ lệ từ chối trong tập đóng hiện tại bằng 0% do chính sách chọn nhãn với ngưỡng 0; không được hiểu là khả năng nhận lỗi lạ tốt.

Các kết quả missing-cage của đợt T nằm riêng trong sheet Unknown_T_only. Cấu hình khác, nên không dùng chúng để đánh giá bộ sinh mới.

## 7. Chi phí chẩn đoán và sinh dữ liệu

Đo chẩn đoán trong một tiến trình mới không nạp Torch hoặc bộ sinh. Đầu vào là một đoạn 4.000 điểm đã qua mô phỏng cảm biến; bộ RF khớp chính xác dự đoán đã lưu. Một lần khởi động, 100 lần đo, CPU một luồng.

| Chỉ số | Giá trị |
|---|---:|
| Tính đặc trưng, trung vị | 6.95 ms |
| RF và gộp lịch sử, trung vị | 2.47 ms |
| Chẩn đoán tổng, trung vị | 9.58 ms |
| Chẩn đoán tổng, P95 | 10.63 ms |
| Lần gọi đầu sau load, chưa làm nóng | 13.59 ms |
| RSS tiến trình sau load model | 157.96 MiB |
| RSS cao nhất quan sát trong lượt đo | 159.89 MiB |
| File bộ chẩn đoán RF | 125.56 KiB |
| Huấn luyện flow, trung bình lượt S3 | 1.89 giây |
| Số tham số mạng flow | 9688 |
| Sinh và dựng 120 mẫu với cache, trung vị lượt trước | 19.10 ms |
| Sinh và tính đặc trưng 120 mẫu, trung vị lượt trước | 319.04 ms |

RSS gồm Python, thư viện, dữ liệu và RF; không phải RAM riêng của trọng số model. Lấy mẫu RSS mỗi 5 ms có thể bỏ qua đỉnh ngắn. Các phép đo chỉ thuộc một fold và query cố định trên máy phát triển, chưa phải Raspberry Pi hay thiết bị DENSO. Thời gian sinh ở lượt trước chịu tải máy khác, không dùng để tính tỷ số tăng tốc so với lượt chẩn đoán mới.

Độ trễ tính toán không gồm thời gian thu đoạn tín hiệu, truyền mạng, tải model hay thời gian phát hiện lỗi. XJTU có các snapshot cách khoảng một phút; gộp năm snapshot là gộp theo lịch sử nhiều phút, không phải năm giây. Chưa có số giờ công, downtime tránh được hoặc tiền bảo trì tiết kiệm.

## Tái lập

```powershell
python priority_benchmark.py
python priority_report.py
python -m pytest -q test_priority_benchmark.py
```

[Báo cáo cải tiến CPU](CAI_TIEN_DL_CPU_20261106.md). [Benchmark tổng hợp trước đây](FULL_BENCHMARK_VA_UU_TIEN_NHA_MAY_20261106.md).
