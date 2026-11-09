# AnchorSpec: kết quả phát triển tiếp ngày 02/11/2026

Báo cáo tự sinh từ các kết quả lưu trong `results/y`. UORED đã được dùng ở các lần nghiên cứu trước; đây là phát triển khám phá, chưa phải xác nhận trên bộ dữ liệu mới.

**Kết luận:** chưa chứng minh cách ghép dữ liệu vật lý mới vượt đối chứng chỉ dùng lỗi thật trên cả bốn lớp. Không nên chọn một biến thể chỉ vì nó thắng mô hình ghép cũ nhưng thua đối chứng mạnh hơn. Xem thêm [đối chứng SVM và chẩn đoán sau cờ bất thường](RESULTS_Y_DIAGNOSIS.md) và [pipeline demo cùng phép thử tiếp theo](DEMO_AND_NEXT_VALIDATION.md).

## Thiết kế đánh giá

20 ổ bi, bốn loại lỗi, ba seed. Mỗi ổ đích chỉ cung cấp nền khỏe để học; toàn bộ sự kiện lỗi của ổ đó bị loại khỏi donor. Mỗi sự kiện là một bản ghi hỏng nặng của một ổ khác. Các phương pháp dùng cùng sự kiện. Tính recall trung bình theo ổ rồi theo lớp; không tính 60 seed như 60 ổ độc lập. Đầu ra khỏe vẫn được phép, không có bộ từ chối để nâng điểm.

Bảng cân bằng dùng một, hai hoặc bốn sự kiện **mỗi loại**, tương ứng tổng cộng bốn, tám hoặc mười sáu sự kiện donor. Luồng đến dần không ép đủ lớp; thứ tự được mô phỏng, không phải thời gian nhà máy.

## Phương pháp đã triển khai

AnchorSpec-E chọn giữa đặc trưng chuẩn hóa cũ, độ lệch so với nền khỏe và đặc trưng trực tiếp; đồng thời chọn mức đóng góp lỗi tổng hợp bằng 0, 0,1 hoặc 0,5. Việc chọn dùng các vòng kiểm tra giữ lại nguyên ổ donor; sau đó học lại bằng các donor đã có. Nhãn lỗi và đoạn khỏe kiểm tra của ổ đích không được đưa vào bước chọn.

Đối chứng chỉ dùng lỗi thật cũng được chọn biểu diễn bằng đúng cách đó. Mô hình phân tầng là một hướng đã thử và không đạt tiêu chí giữ hiệu quả vòng trong và vòng ngoài; kết quả được giữ lại để kiểm tra.

## Kết quả cân bằng theo lớp

| Sự kiện mỗi loại | Chỉ cấy lỗi | Chỉ lỗi thật, z | Ghép cố định, z | Phân tầng, z | Chỉ lỗi thật, có chọn biểu diễn | AnchorSpec-E thích nghi |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 20.9% | 31.8% | 33.0% | 34.6% | 31.8% | 35.2% |
| 2 | 20.9% | 42.3% | 34.9% | 41.7% | 52.1% | 44.1% |
| 4 | 20.9% | 59.9% | 42.4% | 59.2% | 57.6% | 49.1% |

Chỉ số trong bảng là macro recall bốn lớp ở giai đoạn hỏng nặng.

- 1 sự kiện: AnchorSpec-E so với ghép cố định: +2.2 điểm phần trăm; khoảng 95% từ -6.6 đến +10.1. So với chỉ lỗi thật có chọn biểu diễn: +3.3 điểm phần trăm; khoảng 95% từ -8.2 đến +14.5.
- 2 sự kiện: AnchorSpec-E so với ghép cố định: +9.2 điểm phần trăm; khoảng 95% từ -2.1 đến +21.4. So với chỉ lỗi thật có chọn biểu diễn: -8.0 điểm phần trăm; khoảng 95% từ -13.8 đến -2.2.
- 4 sự kiện: AnchorSpec-E so với ghép cố định: +6.8 điểm phần trăm; khoảng 95% từ -3.9 đến +16.8. So với chỉ lỗi thật có chọn biểu diễn: -8.5 điểm phần trăm; khoảng 95% từ -18.2 đến +0.7.

## Sự kiện đến dần

Số sự kiện dưới đây là tổng số đã có, không phải số mỗi loại. Khi chưa có sự kiện cho bi hoặc vòng cách, điểm của các lớp đó vẫn được tính vào kết quả.

| Sự kiện tổng cộng | Chỉ cấy lỗi | Chỉ lỗi thật, z | Ghép cố định, z | Phân tầng, z | Chỉ lỗi thật, có chọn biểu diễn | AnchorSpec-E thích nghi |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 20.9% | 0.0% | 20.9% | 20.9% | 0.0% | 20.9% |
| 2 | 20.9% | 9.6% | 28.8% | 10.4% | 9.6% | 26.3% |
| 4 | 20.9% | 19.6% | 33.2% | 19.3% | 20.9% | 37.4% |
| 8 | 20.9% | 24.9% | 31.2% | 29.1% | 33.2% | 29.0% |
| 12 | 20.9% | 33.9% | 40.6% | 38.1% | 31.1% | 40.0% |

Chỉ số trong bảng là macro recall bốn lớp ở giai đoạn hỏng nặng.

- 0 sự kiện: AnchorSpec-E so với ghép cố định: +0.0 điểm phần trăm; khoảng 95% từ +0.0 đến +0.0. So với chỉ lỗi thật có chọn biểu diễn: +20.9 điểm phần trăm; khoảng 95% từ +11.1 đến +31.9.
- 2 sự kiện: AnchorSpec-E so với ghép cố định: -2.5 điểm phần trăm; khoảng 95% từ -11.3 đến +7.4. So với chỉ lỗi thật có chọn biểu diễn: +16.7 điểm phần trăm; khoảng 95% từ +8.1 đến +25.3.
- 4 sự kiện: AnchorSpec-E so với ghép cố định: +4.1 điểm phần trăm; khoảng 95% từ -3.3 đến +12.2. So với chỉ lỗi thật có chọn biểu diễn: +16.5 điểm phần trăm; khoảng 95% từ +3.4 đến +29.0.
- 8 sự kiện: AnchorSpec-E so với ghép cố định: -2.2 điểm phần trăm; khoảng 95% từ -11.5 đến +7.4. So với chỉ lỗi thật có chọn biểu diễn: -4.2 điểm phần trăm; khoảng 95% từ -11.7 đến +3.0.
- 12 sự kiện: AnchorSpec-E so với ghép cố định: -0.6 điểm phần trăm; khoảng 95% từ -9.8 đến +7.2. So với chỉ lỗi thật có chọn biểu diễn: +8.9 điểm phần trăm; khoảng 95% từ +1.1 đến +17.2.

## Đối chứng biểu diễn cố định

Các cấu hình dưới đây được chạy trong giai đoạn phát triển, không được chọn bằng nhãn ổ đích trong thủ tục thích nghi. Bảng giữ cả cấu hình tốt và cấu hình kém để không che kết quả tìm kiếm.

| Biểu diễn | Sự kiện mỗi loại | Chỉ lỗi thật | Ghép cố định | Phân tầng |
|---|---|---:|---:|---:|
| z | 1 | 31.8% | 33.0% | 34.6% |
| z | 2 | 42.3% | 34.9% | 41.7% |
| z | 4 | 59.9% | 42.4% | 59.2% |
| delta | 1 | 30.9% | 38.6% | 33.7% |
| delta | 2 | 40.8% | 39.0% | 38.6% |
| delta | 4 | 52.5% | 50.1% | 58.7% |
| raw | 1 | 36.6% | 42.7% | 25.5% |
| raw | 2 | 54.3% | 41.8% | 44.6% |
| raw | 4 | 64.9% | 56.7% | 63.1% |
| both | 1 | 30.4% | 38.9% | 35.7% |
| both | 2 | 55.4% | 44.7% | 39.1% |
| both | 4 | 54.5% | 57.0% | 57.5% |

## Giai đoạn sớm và báo nhầm khỏe

| Sự kiện mỗi loại | Lỗi sớm, ghép cố định | Lỗi sớm, AnchorSpec-E | Báo nhầm khỏe, ghép cố định | Báo nhầm khỏe, AnchorSpec-E |
|---|---:|---:|---:|---:|
| 1 | 39.0% | 47.2% | 9.0% | 7.6% |
| 2 | 40.4% | 50.0% | 11.0% | 4.5% |
| 4 | 49.4% | 52.5% | 10.2% | 5.0% |

Đoạn khỏe kiểm tra nằm trong cùng bản ghi khỏe với nền ban đầu. Ngay cả 0% ở bảng này cũng không chứng minh không báo nhầm qua ngày, qua tải hay sau tháo lắp.

## Từng loại lỗi

| Sự kiện mỗi loại | Phương pháp | Vòng trong | Vòng ngoài | Bi | Vòng cách |
|---|---|---:|---:|---:|---:|
| 1 | Ghép cố định, z | 75.4% | 56.5% | 0.0% | 0.0% |
| 1 | Chỉ lỗi thật, có chọn biểu diễn | 45.6% | 8.4% | 40.0% | 33.3% |
| 1 | AnchorSpec-E thích nghi | 75.8% | 51.6% | 0.0% | 13.3% |
| 2 | Ghép cố định, z | 75.1% | 50.2% | 14.4% | 0.0% |
| 2 | Chỉ lỗi thật, có chọn biểu diễn | 91.6% | 27.4% | 60.4% | 29.1% |
| 2 | AnchorSpec-E thích nghi | 89.1% | 30.9% | 33.0% | 23.5% |
| 4 | Ghép cố định, z | 69.5% | 68.4% | 24.9% | 6.7% |
| 4 | Chỉ lỗi thật, có chọn biểu diễn | 87.4% | 38.2% | 50.5% | 54.4% |
| 4 | AnchorSpec-E thích nghi | 66.7% | 50.2% | 48.4% | 31.2% |

## Kiểm tra nhãn sai

Hoán vị nhãn của mọi sự kiện donor, giữ nguyên tín hiệu và ổ đích. Đây là phép thử nhãn sai có hệ thống; chưa đại diện cho mọi mức nhiễu nhãn trong vận hành.

| Phương pháp | Nhãn đúng | Nhãn bị hoán vị |
|---|---:|---:|
| Chỉ cấy lỗi | 20.9% | 20.9% |
| Chỉ lỗi thật, z | 31.8% | 13.3% |
| Ghép cố định, z | 33.0% | 27.3% |
| Phân tầng, z | 34.6% | 11.8% |
| Chỉ lỗi thật, có chọn biểu diễn | 31.8% | 13.3% |
| AnchorSpec-E thích nghi | 35.2% | 16.8% |

Cờ xác nhận chỉ chặn sự kiện được đánh dấu chưa xác nhận. Nó không tự phát hiện một kết luận kỹ thuật viên đã xác nhận nhưng sai.

## Cấu hình được chọn và chi phí

- 1 sự kiện mỗi loại, 60 lần fit: delta, trọng số 0.1: 8; raw, trọng số 0.1: 3; z, trọng số 0: 7; z, trọng số 0.1: 42.
- 2 sự kiện mỗi loại, 60 lần fit: delta, trọng số 0: 17; delta, trọng số 0.1: 2; delta, trọng số 0.5: 6; raw, trọng số 0: 11; raw, trọng số 0.1: 8; raw, trọng số 0.5: 4; z, trọng số 0: 6; z, trọng số 0.1: 3; z, trọng số 0.5: 3.
- 4 sự kiện mỗi loại, 60 lần fit: delta, trọng số 0: 4; delta, trọng số 0.1: 2; delta, trọng số 0.5: 2; raw, trọng số 0: 3; raw, trọng số 0.5: 4; z, trọng số 0: 19; z, trọng số 0.1: 15; z, trọng số 0.5: 11.

Mô hình gồm cả metadata khi pickle: trung vị 0.239 MB; lớn nhất 0.503 MB. Thời gian fit gồm chọn cấu hình, đo khi có nhiều tiến trình đồng thời; không dùng để suy ra tốc độ thiết bị biên.

## Giới hạn và quyết định

Không có bằng chứng đã vượt mọi giới hạn. Chỉ ghi nhận cải thiện nào có trong bảng và kiểm tra riêng phần đánh đổi. Chưa xác nhận lỗi ngoài tập nhãn, thiếu bôi trơn, dị vật, dự báo giờ hỏng, báo nhầm dài hạn hay hiệu năng Pi. Số đo hiện tại dùng một trục rung công khai qua cảm biến giả lập.

Khoảng bootstrap lấy mẫu lại theo ổ và phân tầng theo lớp. Nó chỉ mô tả độ bất định trên bộ dữ liệu này; chưa điều chỉnh việc thử nhiều phương pháp và không xử lý hết sự phụ thuộc do dùng chung donor. Có năm ổ mỗi loại, nên cần kiểm tra độc lập trước khi tuyên bố tổng quát.

Chuẩn hóa cũ có đặc trưng sau chia lên tới khoảng 112 tỷ vì một số chiều gần như không đổi trong 11 cửa sổ khỏe chồng lấn. Đây là vấn đề độ ổn định cần xử lý, nhưng việc bỏ chuẩn hóa không tự động cải thiện mọi lớp. Vì vậy các biểu diễn được so bằng sự kiện donor thay vì mặc định chọn biểu diễn có điểm test cao nhất.

## Cách chạy lại

```powershell
python anchorspec/y_download.py
python anchorspec/y_run.py prepare
python anchorspec/y_run.py run
python anchorspec/y_run.py run --mode stream
python anchorspec/y_run.py run --representation delta
python anchorspec/y_run.py run --representation raw
python anchorspec/y_run.py run --representation both
python anchorspec/y_adaptive_run.py
python anchorspec/y_adaptive_run.py --mode stream
python anchorspec/y_report.py
python -m pytest -q anchorspec
```

Dữ liệu thô khoảng 303 MB được tải trực tiếp và kiểm tra SHA256 của nhà cung cấp. Dữ liệu, cache và mô hình ở data được Git bỏ qua. Các JSON lưu hash code, sự kiện donor, seed, cấu hình và kết quả từng ổ. Các hash ghi tại thời điểm chạy có thể khác code hiện tại nếu sửa tiếp; cần đối chiếu trước khi tái lập.

## Nguồn và phạm vi kế thừa

- [UORED phiên bản 5](https://data.mendeley.com/datasets/y2px5tg92h/5): nguồn dữ liệu công khai của các lượt chạy mới.
- [Integrating Expert Knowledge with Domain Adaptation for Unsupervised Fault Diagnosis](https://arxiv.org/abs/2107.01849): đã nghiên cứu tạo lỗi trên tín hiệu khỏe và chuyển từ tổng hợp sang thật; không được nhận đây là ý tưởng hoàn toàn mới của AnchorSpec.
- [Controlled Generation of Unseen Faults for Partial and Open-Partial Domain Adaptation](https://arxiv.org/abs/2204.14068): nghiên cứu sinh lỗi trong bài toán lệch miền và thiếu lớp; chưa được tái hiện trong lượt này.
- [Bi-directional digital twin prototype anchoring](https://arxiv.org/abs/2603.07054): hướng few-shot trên tín hiệu dòng điện động cơ; chưa có bằng chứng áp dụng trực tiếp cho cấu hình rung giá rẻ này.

Đóng góp cần đánh giá của nhánh mới là tổ chức học theo sự kiện độc lập, điều chỉnh vai trò dữ liệu vật lý bằng kiểm tra donor và lưu bằng chứng lựa chọn; chưa đưa ra tuyên bố ưu tiên học thuật.
