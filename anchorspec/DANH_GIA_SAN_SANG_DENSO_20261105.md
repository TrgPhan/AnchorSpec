# AnchorSpec: bằng chứng và mức sẵn sàng, 05/11/2026

**Đủ làm MVP nghiên cứu và trình bày kết quả có giới hạn. Chưa đủ chứng minh vượt trội toàn diện hoặc chẩn đoán tự động trong nhà máy.**

Hướng cải thiện rõ nhất ở lượt mới là căn chỉnh feature theo nền khỏe từng ổ: real RF 68.33% thành 77.73%, vòng cách 11.67% thành 45.00%. +9.40 điểm; CI thăm dò [-6.11; +23.70]. Đây là ablation thăm dò và lợi ích xử lý feature, không phải lợi ích dữ liệu sinh. Gán lỗi trên healthy giả định tăng từ 0.00% lên 3.08%.

## Kết quả mới có thể trình bày

Bộ chọn phương pháp sinh bằng các ổ nguồn đạt 67.96% macro recall đoạn cuối, so với 68.33% khi chỉ dùng mẫu thật. Chênh lệch: -0.37 điểm; CI thăm dò [-7.78; +6.67]. Không dùng nhãn lỗi ổ đích để chọn phương pháp.

T là phép thử khó hơn cách chấm conditional trước đây: phải xử lý cả cảnh báo đưa tới tín hiệu giả định khỏe, và lỗi chưa có trong thư viện. Các phép thử mới không xác nhận được việc chỉ tăng ngưỡng score sẽ tạo ra chẩn đoán đáng tin cậy.

## Đã bổ sung gì

1. Tách năm bản ghi khỏe đầu để tham chiếu và năm bản ghi tiếp để đánh giá; không dùng healthy test để sinh mẫu.
2. Giữ nguyên đối chứng thật, sao chép, surrogate cũ, trộn nền và chuyển nền phổ; cùng bộ phân loại và trọng số.
3. Đánh giá từ chối chẩn đoán, bỏ sót khi từ chối và gán nhầm trên healthy giả định.
4. Loại hoàn toàn vòng cách khỏi thư viện để kiểm tra lỗi chưa từng học.
5. Thêm vòng đánh giá bên trong chỉ dùng ổ nguồn để chọn augmentation; nếu lợi ích nhỏ thì giữ mẫu thật.
6. Kiểm tra điều kiện thử nghiệm của nguồn thiếu bôi trơn trước khi xây benchmark.

## Dữ liệu và cách chấm

XJTU-SY: 13 ổ đơn lỗi, gồm ba vòng trong, tám vòng ngoài và hai vòng cách. Mỗi lượt giữ kín lỗi của một ổ; ba seed không phải ba thí nghiệm độc lập. Native 25,6 kHz, một trục; cảm biến giả lập 4 kHz, băng thông 1 kHz, 8g. Các giả định này chưa đại diện cho cảm biến DENSO đã xác minh.

Bản ghi đầu đời chỉ được giả định khỏe. Các nhãn lỗi lấy từ tháo kiểm tra cuối đời, không phải xác minh tại từng phút. Mười bản ghi trước đoạn cuối không được gọi là thời điểm bắt đầu lỗi. Làm mượt năm snapshot tương ứng khoảng năm phút.

Trong T, mọi đoạn test đều được ép nhận cảnh báo đầu vào để thử module chẩn đoán. Tỷ lệ gán lỗi trên healthy dưới đây không phải tỷ lệ báo nhầm của hệ thống DENSO. Có 65 snapshot healthy riêng biệt, lặp lại giữa cấu hình và seed; không phải hàng nghìn ca khỏe độc lập.

T và nested tiếp tục dùng dữ liệu đã xem. Nested giảm việc chọn cấu hình bằng lỗi outer target nhưng không xóa được tính hậu nghiệm của quá trình phát triển. CI bootstrap theo ổ chỉ mang tính thăm dò, do ít ổ và các tập train chồng lấn.

## Phương pháp mới: chọn augmentation bằng ổ nguồn

Trong mỗi lượt outer, giữ kín lỗi ổ đích. Lần lượt dùng từng trong 12 ổ nguồn làm validation và 11 ổ còn lại để train. Chọn ứng viên có macro recall tốt nhất trong những ứng viên có tỷ lệ gán lỗi trên healthy không quá 5%. Nếu mẫu thật cũng đạt điều kiện, chỉ dùng augmentation khi gain validation ít nhất hai điểm phần trăm. Nếu không ứng viên nào đạt, giữ mẫu thật và ghi rõ selection chưa đạt điều kiện healthy.

Có 1.872 lần fit inner, nhưng vẫn chỉ 13 ổ đánh giá. Quy tắc này là cải tiến quy trình chọn phương pháp, không phải bằng chứng rằng mẫu tổng hợp tạo ra ổ hỏng mới hoặc lỗi cơ học mới.

| Phương pháp RF | Trước đoạn cuối | Đoạn cuối | Vòng trong | Vòng ngoài | Vòng cách | Gán lỗi trên healthy giả định |
|---|---:|---:|---:|---:|---:|---:|
| Chỉ mẫu thật | 58.75% | 68.33% | 93.33% | 100.00% | 11.67% | 0.00% |
| Surrogate cũ | 56.71% | 63.33% | 90.00% | 100.00% | 0.00% | 0.00% |
| Trộn nền cùng ổ | 60.56% | 66.30% | 92.22% | 100.00% | 6.67% | 1.03% |
| Chuyển nền phổ | 71.94% | 77.78% | 93.33% | 100.00% | 40.00% | 0.00% |
| Chọn bằng ổ nguồn | 61.76% | 67.96% | 92.22% | 100.00% | 11.67% | 0.00% |

Bảng dùng argmax gồm lớp khỏe, không áp thêm ngưỡng score. Lựa chọn lớp khỏe chỉ có nghĩa mô hình không ủng hộ một lớp lỗi đã học, không phải kết luận máy an toàn.

Số lựa chọn qua 39 outer fold và seed: Chuyển nền phổ: 21, Surrogate cũ: 8, Trộn nền cùng ổ: 4, Chỉ mẫu thật: 6.

## Bổ sung 15 ổ nguồn UORED để kiểm tra thiếu sự kiện

Giữ XJTU làm nơi đánh giá; thêm năm ổ vòng trong, năm vòng ngoài và năm vòng cách UORED vào thư viện nguồn. So cùng thư viện giữa real và augmentation để không gán lợi ích thêm dữ liệu thật cho bộ sinh. Một ablation trừ mean healthy riêng từng ổ kiểm tra khả năng căn chỉnh feature. Đây là thăm dò tiếp trên XJTU đã xem, không phải tập xác nhận mới.

| Thư viện | Biểu diễn | Phương pháp RF | Recall đoạn cuối | Vòng cách | Gán lỗi trên healthy |
|---|---|---|---:|---:|---:|
| XJTU | raw | Chỉ mẫu thật | 68.33% | 11.67% | 0.00% |
| XJTU | raw | Surrogate cũ | 63.33% | 0.00% | 0.00% |
| XJTU | raw | Trộn nền cùng ổ | 66.30% | 6.67% | 1.03% |
| XJTU và UORED | raw | Chỉ mẫu thật | 54.81% | 0.00% | 0.00% |
| XJTU và UORED | raw | Surrogate cũ | 53.70% | 0.00% | 0.51% |
| XJTU và UORED | raw | Trộn nền cùng ổ | 51.85% | 0.00% | 0.00% |
| XJTU | delta | Chỉ mẫu thật | 77.73% | 45.00% | 3.08% |
| XJTU | delta | Surrogate cũ | 74.03% | 45.00% | 3.08% |
| XJTU | delta | Trộn nền cùng ổ | 73.66% | 43.33% | 3.08% |
| XJTU và UORED | delta | Chỉ mẫu thật | 47.36% | 10.00% | 12.82% |
| XJTU và UORED | delta | Surrogate cũ | 41.67% | 3.33% | 14.87% |
| XJTU và UORED | delta | Trộn nền cùng ổ | 48.56% | 20.00% | 17.95% |

Primary của lượt external, RF raw với thư viện kết hợp: severity 51.85%, real cùng thư viện 54.81%; -2.96 điểm; CI thăm dò [-13.33; +3.33].

Riêng việc thêm mẫu thật UORED: 68.33% thành 54.81%; -13.52 điểm; CI thăm dò [-29.44; -1.48].

Delta là phép trừ mean healthy trong không gian feature, không phải chứng minh chuyển được waveform hoặc tạo thêm kiểu hỏng cơ học. Các giả định đơn vị và healthy của UORED vẫn còn. Kết quả âm được giữ lại, không chọn representation thắng sau khi xem điểm để thay primary.

Tái lập lượt này: `python t_external.py`; protocol: [T external](PROTOCOL_T_EXTERNAL.md).

## Ngưỡng tự tin chưa giải quyết được lỗi chưa biết

| RF | Chính sách | Recall đoạn cuối | Recall vòng cách | Gán lỗi trên healthy | Gán lỗi đã biết cho vòng cách chưa học |
|---|---|---:|---:|---:|---:|
| Chỉ mẫu thật | conditional | 76.11% | 35.00% | 100.00% | 100.00% |
| Chỉ mẫu thật | selective_0 | 68.33% | 11.67% | 0.00% | 100.00% |
| Chỉ mẫu thật | selective_0.5 | 58.84% | 0.00% | 0.00% | 75.00% |
| Chỉ mẫu thật | selective_0.7 | 32.04% | 0.00% | 0.00% | 48.33% |
| Chỉ mẫu thật | selective_0.9 | 9.58% | 0.00% | 0.00% | 31.67% |
| Surrogate cũ | conditional | 74.44% | 33.33% | 99.49% | 100.00% |
| Surrogate cũ | selective_0 | 63.33% | 0.00% | 0.00% | 75.00% |
| Surrogate cũ | selective_0.5 | 59.58% | 0.00% | 0.00% | 50.00% |
| Surrogate cũ | selective_0.7 | 34.21% | 0.00% | 0.00% | 50.00% |
| Surrogate cũ | selective_0.9 | 9.03% | 0.00% | 0.00% | 18.33% |
| Trộn nền cùng ổ | conditional | 77.96% | 41.67% | 100.00% | 100.00% |
| Trộn nền cùng ổ | selective_0 | 66.30% | 6.67% | 1.03% | 76.67% |
| Trộn nền cùng ổ | selective_0.5 | 55.14% | 0.00% | 0.00% | 51.67% |
| Trộn nền cùng ổ | selective_0.7 | 33.15% | 0.00% | 0.00% | 48.33% |
| Trộn nền cùng ổ | selective_0.9 | 10.97% | 0.00% | 0.00% | 31.67% |
| Chuyển nền phổ | conditional | 78.89% | 43.33% | 100.00% | 100.00% |
| Chuyển nền phổ | selective_0 | 77.78% | 40.00% | 0.00% | 85.00% |
| Chuyển nền phổ | selective_0.5 | 58.89% | 0.00% | 0.00% | 56.67% |
| Chuyển nền phổ | selective_0.7 | 32.82% | 0.00% | 0.00% | 50.00% |
| Chuyển nền phổ | selective_0.9 | 9.68% | 0.00% | 0.00% | 36.67% |

Conditional chọn trong các lớp lỗi và không phù hợp để tự xử lý một cảnh báo giả. Selective xét cả lớp khỏe và trả chưa đủ căn cứ khi score thấp; từ chối được tính là không chẩn đoán đúng lỗi. Score RF và SVM chưa được hiệu chỉnh xác suất. Tăng threshold tới mức từ chối gần hết không phải là giải quyết bài toán.

Cổng nghiên cứu đặt trước cho RF severity, ngưỡng 0,5: **không đạt**. Kết quả các điều kiện:

- terminal_macro80: không đạt.
- each_class70: không đạt.
- healthy_false_fault5: đạt.
- gain5pp: không đạt.
- positive_exploratory_ci: không đạt.
- no_loss_to_surrogate: không đạt.
- preterminal_noninferiority: đạt.
- unknown_fault_claim10: không đạt.

## Tại sao chưa có benchmark thiếu bôi trơn đáng tin cậy

Audit metadata của tám lần chạy DLR cho thấy chỉ nhóm biên độ 10 độ, tải 9 kN và tần số 10 Hz có cả dầu và không dầu. Nhóm này gồm ba lần chạy với dầu khác nhau và chỉ một lần không dầu. Giữ lần không dầu đó làm test sẽ khiến train không còn lần không dầu cùng chế độ. Những lần không dầu còn lại đổi tải, biên độ hoặc tần số.

Hai cảm biến nằm ở hai ổ trong cùng lần chạy, không được chia qua train và test như hai thí nghiệm độc lập. Tình trạng cấp dầu là treatment của thí nghiệm, không cung cấp thời điểm bắt đầu hỏng. Đây là ổ kim dao động, không đồng nhất với ổ bi quay liên tục. Vì vậy chưa dùng nguồn này để công bố điểm chẩn đoán thiếu bôi trơn; chưa tải thêm các waveform lớn chỉ để chia ngẫu nhiên.

## Điều kiện để chuyển từ nghiên cứu sang thử nghiệm nhà máy

| Phần cần chứng minh | Bằng chứng hiện có | Việc còn thiếu |
|---|---|---|
| Tác dụng dữ liệu sinh | Có đối chứng cùng cấu hình, có cả kết quả tăng và giảm | Xác nhận phương pháp đã khóa trên tập mới |
| Vòng cách | Hai ổ tự nhiên; recall còn thấp | Nhiều sự kiện độc lập, nhãn kiểm tra cơ khí |
| Thiếu bôi trơn và dị vật | Audit nguồn; chưa có benchmark đủ điều kiện | Cohort có đối chứng và nhiều lần chạy độc lập |
| Cảnh báo giả và lỗi lạ | Có stress test; phát hiện điểm yếu | Cảnh báo upstream thật và nền khỏe được xác nhận |
| Cảm biến và tốc độ | Có mô phỏng và đo trên máy phát triển | Mã cảm biến, băng thông, dải đo; đo trên Pi mục tiêu |
| Giá trị bảo trì | Chưa đo | Chạy song song với kỹ thuật viên; log đối chiếu sự kiện |

Phạm vi hợp lý hiện nay là demo offline, hỗ trợ xem tín hiệu và gợi ý các giả thuyết kiểm tra. Chưa tự đóng cảnh báo, ra lệnh PLC, quyết định thay linh kiện hoặc báo số giờ còn lại tới hỏng. Pilot nhà máy cần dữ liệu và tiêu chí nghiệm thu thống nhất với nhóm vận hành.

## Câu trình bày đề xuất

“Nhóm xây dựng AnchorSpec để bổ sung mẫu lỗi từ tín hiệu thật và chọn phép biến đổi bằng đánh giá trên các ổ nguồn. Benchmark tách theo ổ bi, giữ nguyên đối chứng và đo cả tình huống cảnh báo sai. Kết quả cho thấy lợi ích có phạm vi, đồng thời xác định rõ vòng cách và lỗi chưa có trong thư viện là giới hạn cần giải quyết trước triển khai.”

## Tái lập và tài liệu

Trong thư mục anchorspec, sau khi có cache U:

```powershell
python t_readiness.py
python t_lubrication_design.py
python t_nested.py
python t_report.py
python -m pytest -q
```

Hai protocol chốt riêng trước mỗi lượt. Nested đọc prediction outer sau khi đã ghi lựa chọn. Source, input cache và evidence có SHA256; kiểm tra tái dựng prediction và score trong pytest. Raw data vẫn nằm ngoài Git.

- [Nguồn XJTU-SY](https://github.com/WangBiaoXJTU/xjtu-sy-bearing-datasets).
- [Bài báo XJTU-SY](https://doi.org/10.1109/TR.2018.2882682).
- [Dữ liệu ổ kim DLR](https://zenodo.org/records/20742913).
- [Repository AnchorSpec](https://github.com/TrgPhan/AnchorSpec).
- [Protocol stress test](PROTOCOL_T_READINESS.md).
- [Protocol chọn augmentation](PROTOCOL_T_NESTED.md).
- [Kết quả natural-fault U](KET_QUA_O_BI_TU_NHIEN_20261105.md).
