# Phương pháp thời gian thực và kết quả TN2b, TN3b — 01/11/2026

**Dữ liệu công khai, CPU, chưa có dữ liệu DENSO; Minh chưa rà soát.** Tiếp nối [báo cáo 31/10](KET_QUA_SO_BO_TN1_TN2_TN3_20261031.md).

## Kết luận

| Câu hỏi | Kết quả | Mức bằng chứng |
|---|---|---|
| Cấy lỗi có thắng dữ liệu máy khác? | **Có, G1b đạt.** A0 0,519 so với C 0,298; riêng vòng trong và ngoài 0,775 so với 0,448 | Kiểm chứng một lần, có giao thức; cùng giàn thử |
| Có gần dùng lỗi thật không? | Khá gần: 0,775 so với D 0,836, CI của hiệu vẫn chạm 0 | Như trên |
| Vòng cách thì sao? | **Thất bại: 0,009.** Trái với kỳ vọng "Tốt" trong kế hoạch v1.4 | Chỉ 2 ổ |
| Có đủ nhẹ để chạy thời gian thực? | RF 50 cây: 0,44 MB, khoảng 19 ms/cửa sổ trên laptop, độ đúng không kém rõ | Chưa đo trên Pi 5 |
| Dự báo thời gian còn lại đã dùng được chưa? | **Chưa.** Các phương pháp thử đều thấp, khoảng dự báo Wiener sai | Khám phá |

**Lưu ý lớn nhất:** kết quả phân loại chỉ tính ở 10% cuối đời, khi ổ thường đã hỏng nặng. Nó **không** chứng minh phát hiện được loại lỗi ở giai đoạn sớm.

## Các phương pháp đã xem xét

Tiêu chí: chỉ dùng quá khứ, chạy được trên thiết bị biên, kỹ sư giải thích được, khởi tạo máy mới không cần chờ hỏng.

| Phương pháp | Vì sao xét | Kết quả | Quyết định |
|---|---|---|---|
| Mô hình riêng từng máy, nền của chính ổ, cấy lỗi | Đúng yêu cầu DENSO | G1b đạt | **Giữ** |
| RF 50 cây, sâu 8 | Nhỏ, nhanh | Không kém rõ so với 200 cây | **Giữ cho triển khai** |
| Hồi quy logistic | Nhỏ nhất | Thấp hơn 0,123 ở vòng trong và ngoài, CI loại trừ 0; dao động seed lớn | Bỏ |
| Trung bình trượt xác suất, K=5 | Lọc theo thời gian, rất đơn giản | Tăng 1,8 điểm % ở A0, không có CI | Giữ vì gần như không tốn gì, không kỳ vọng nhiều |
| HI đóng băng + ngưỡng z + 5 bản liên tiếp | Dễ giải thích | Ổn định nhất; xem TN3b | **Giữ để gác cổng** |
| EWMA, CUSUM | Biểu đồ kiểm soát công nghiệp ([Li et al. 2024](https://researchonline.jcu.edu.au/93851/) dùng hướng SPC) | Cảnh báo sớm hơn nhưng dao động nhiều hơn ở nhiều cấu hình | Chưa dùng |
| Wiener hai giai đoạn ([tham khảo](https://ein.org.pl/Two-stage-Remaining-Useful-Life-Prediction-Based-on-the-Wiener-Process-With-Multi,189803,0,2.html)) | Có khoảng tin cậy | Không tốt hơn log-tuyến tính, khoảng 80% chỉ phủ 0–46% | Bỏ ở dạng hiện tại |
| Quy tắc vật lý trên phổ bao hình ([hướng tương tự](https://mdpi-res.com/d_attachment/applsci/applsci-15-02240/article_deploy/applsci-15-02240-v2.pdf)) | Không cần huấn luyện | 0,182 ở băng 1 kHz; bỏ sót nhiều | Bỏ ở dạng hiện tại |
| Đặc trưng giữa hai trục | Dùng được 3 trục của DENSO | Không cải thiện; chưa mô phỏng đúng truyền giữa các trục | Chưa kết luận |
| [MiniRocket](https://alphaxiv.org/abs/2012.08791) | Chuỗi thời gian nhanh trên CPU | **Chưa chạy:** `aeon` buộc hạ `numpy` đã ghim | Cần môi trường riêng nếu muốn thử |

Các lượt tìm nhanh của tôi không ra nghiên cứu nào so trực tiếp các phương án này trên cảm biến rẻ, nên các số dưới đây là số tự đo. Khi đọc tài liệu cần kiểm tra việc chia tập: một bài arXiv 2023 của Abburi et al. (tôi chỉ đọc đoạn trích từ kết quả tìm kiếm) cảnh báo nhiều kết quả cao đến từ việc để cùng một ổ ở cả huấn luyện và kiểm tra.

## TN2b — Mỗi máy một mô hình trên XJTU-SY

**Thiết lập:** [giao thức](../../anchorspec/PROTOCOL_TN2B.md) ghi trước; 13 ổ một lỗi; nền là đoạn đầu đời của chính ổ; kiểm tra trên 10% cuối đời; 3 seed; chạy test một lần sau freeze. Thông số và nhãn lấy từ bài giải thích bộ dữ liệu của tác giả.

| Nhánh | Macro 3 lớp | Macro trong và ngoài | Trong | Ngoài | Cách | Bình thường | Ổ bỏ phiếu đúng /13 |
|---|---:|---:|---:|---:|---:|---:|---|
| **A0, cấy, không dùng lỗi thật (chính)** | **0,519** | **0,775** | 0,674 | 0,875 | 0,009 | 0,785 | 11 / 10 / 10 |
| A1, biên độ chung, hiệu chỉnh trên ổ khác | 0,485 | 0,715 | 0,610 | 0,820 | 0,026 | 0,795 | 11 / 10 / 11 |
| D, lỗi thật từ ổ khác | 0,557 | 0,836 | 0,850 | 0,822 | 0,000 | 0,938 | 10 / 10 / 10 |
| C, CWRU | 0,298 | 0,448 | 0,291 | 0,604 | không có lớp | 0,949 | 6 / 5 / 5 |
| P, quy tắc vật lý | 0,121 | 0,182 | 0,025 | 0,339 | 0,000 | 0,985 | 2 / 2 / 2 |

| Hiệu, CI 95% bootstrap theo ổ | Macro 3 lớp | Macro trong và ngoài |
|---|---|---|
| **A0 − C (G1b)** | **+0,221 (+0,144 … +0,308)** | **+0,327 (+0,214 … +0,456)** |
| A0 − D | −0,038 (−0,076 … +0,005) | −0,061 (−0,117 … +0,002) |
| A0 − P | +0,398 (+0,294 … +0,512) | +0,593 (+0,436 … +0,761) |
| A1 − A0 | −0,034 (−0,107 … +0,042) | −0,060 (−0,167 … +0,054) |

**Quan sát.**
- Cả 2 ổ vòng cách đều sai ở A0: 1_4 chủ yếu bị gán vòng trong, 2_3 chủ yếu bị gán vòng ngoài; A1 cũng chỉ đạt 0,026. Vì vậy 10–11/13 ổ đúng thực chất là 10–11/11 ổ vòng trong và ngoài.
- Yếu nhất là 3_5 (0,24), rồi 3_3 (0,53) và 2_1 (0,56). Các ổ vòng ngoài còn lại từ 0,80 trở lên.
- Đoạn "bình thường" ngay sau nền đúng 78,5%, và rất thấp ở 1_2 (0,13) và 2_4 (0,20). Đây là các ổ đời ngắn, có thể đã bắt đầu suy giảm, nhưng không xác nhận được.
- A1 không tốt hơn A0, nên hiệu chỉnh chưa có lợi. Nó cũng không sụp như nhánh A của TN2, điều này phù hợp với giả thuyết "hiệu chỉnh riêng lớp tạo tín hiệu giả", nhưng chưa phải kiểm chứng trực tiếp.

**Vì sao vòng cách thất bại (giả thuyết):** công thức hiện tại phát xung với tần số BPFO, nên giống lỗi vòng ngoài hơn là cơ chế vỡ vòng cách thật. Dữ liệu chỉ có 2 ổ nên chưa kết luận được. **Trước mắt không nên hứa khả năng này với DENSO**, trong khi máy thử ổ bi của DENSO lại có lớp vỡ vòng cách.

**Giới hạn.** Cùng giàn thử và cùng loại ổ; thử tăng tốc tải rất lớn; vòng trong 3 ổ, vòng cách 2 ổ nên CI chỉ nên đọc thận trọng; chọn A0 làm chính dựa trên TN2. Tốc độ danh định có thể lệch thật: bài giải thích ghi 1× là 34,38 Hz ở tốc độ danh định 35 Hz, thấp hơn khoảng 1,8%, vẫn trong dung sai bậc của đặc trưng.

## TN3b — Cảnh báo và dự báo (khám phá)

Các ổ này đã xem ở TN3 nên **không phải kiểm chứng**. Dùng cảm biến rẻ; chọn tham số trên ổ dev. `Dao động` là số ổ có HI vượt mức z=5 dưới 50% thời gian sau cảnh báo. Cột cuối là tỉ lệ khoảng 80% của Wiener chứa giá trị thật.

| Bộ, nền | Cảnh báo | Ổ test (không báo) | % đời trung vị | Dưới 50% đời | Dao động | α-λ log / Wiener / hằng số | Phủ 80% |
|---|---|---|---:|---:|---:|---|---:|
| XJTU, 30 đầu | Ngưỡng z=10 | 12 (2) | 64% | 4 | 0 | 0,094 / 0,063 / 0,000 | 14% |
| XJTU, 30 đầu | EWMA 12 | 12 (1) | 80% | 4 | 0 | 0,088 / 0,091 / 0,000 | 11% |
| XJTU, 30 đầu | CUSUM 5 | 12 (0) | 19% | 10 | 2 | 0,116 / 0,109 / 0,051 | 17% |
| FEMTO, 30 đầu | Ngưỡng z=25 | 14 (13) | 70% | 0 | 0 | 0,000 / 0,000 / 0,000 | 0% |
| FEMTO, 30 đầu | EWMA 8 | 14 (0) | 51% | 7 | 4 | 0,020 / 0,000 / 0,000 | 0% |
| FEMTO, 30 đầu | CUSUM 5 | 14 (0) | 3% | 14 | 11 | 0,063 / 0,064 / 0,069 | 46% |
| IMS, 30 đầu | Ngưỡng z=5 | 3 (0) | 86% | 1 | 0 | 0,050 / 0,052 / 0,284 | 13% |

Cấu hình bỏ 10 bản đầu (chạy rà) và các cấu hình IMS còn lại nằm trong `anchorspec/results/tn3b/trend.json`; không có cấu hình nào tốt hơn rõ rệt.

**Quan sát.**
- **RUL chưa dùng được:** α-λ của Wiener và log-tuyến tính đều dưới 12%. Con số α-λ 0,284 của đối chứng hằng số ở IMS chỉ dựa trên 3 ổ.
- Khoảng 80% của Wiener chỉ phủ 0–46%, tức tin cậy quá mức; đừng trình bày nó như khoảng tin cậy. Phép tính phân vị có phát cảnh báo số học ở một số cấu hình, nên các con số phủ này có thể lệch thấp nhẹ.
- Ngưỡng lấy từ ổ dev **không chuyển được giữa các bộ dữ liệu**: FEMTO với z=25 bỏ sót 13/14 ổ. Ngưỡng cần đặt theo từng máy.
- Bỏ giai đoạn chạy rà không cải thiện rõ.

## Chuỗi thời gian thực toàn đời ổ (khám phá)

HI đóng băng → cảnh báo → phân loại RF 50 cây + K=5, chạy tuần tự như tại máy trên 13 ổ XJTU. Chuỗi này chỉ có lớp vòng trong và ngoài vì công thức vòng cách thất bại.

| Cách gác cổng | Ổ trong và ngoài có cảnh báo | Cảnh báo ở % đời (trung vị) | Đúng loại sau cảnh báo | Đúng loại ở 10% cuối | Ổ đạt ≥ 80% ở 10% cuối |
|---|---:|---:|---:|---:|---:|
| Ngưỡng z=10 | 10/11 | 57% | 0,82 | 0,90 | 8/10 |
| CUSUM 5 | 11/11 | 19% | 0,76 | 0,91 | 9/11 |

- **Phải có cổng HI:** nếu chạy bộ phân loại liên tục, trung bình 46% cửa sổ nửa đầu đời bị gọi là lỗi.
- Cảnh báo sớm kéo theo độ đúng thấp ngay sau cảnh báo (ổ 3_1: 0,12–0,17 với CUSUM, 0,41–0,42 với ngưỡng). Nên cho hiện loại lỗi sau khi kết quả đã ổn định vài chục phút, thay vì ngay tại lúc cảnh báo.
- Ổ 3_5 không cảnh báo với ngưỡng z=10, và 3_3 vẫn yếu (0,30–0,70 ở 10% cuối).

## Ước lượng tốc độ từ phổ

Không dùng tachometer. So với kênh `speed` của K001–K004 (mỗi bản ghi 4 s):

| Cách | Sai số trung vị | p90 | Lớn nhất |
|---|---:|---:|---:|
| Tìm ±10% (cũ) | 1,43% | 7,54% | 9,97% |
| **Tìm ±3% quanh tốc độ danh định** | 0,34% | 2,40% | 3,00% |
| + trung vị 5 bản ghi (20 s) | 0,20% | 1,72% | 1,99% |
| **+ trung vị 20 bản ghi (80 s)** | 0,04% | 0,49% | 0,67% |

**Dạng tốt nhất đạt cổng 1% trên Paderborn**, nhưng chỉ có 4 phép đo, ở tốc độ không đổi, và phải biết trước tốc độ danh định. Chưa kiểm tra khi máy đổi tốc độ. XJTU-SY chỉ có tốc độ danh định nên chưa đối chiếu được.

## Thiết kế đề xuất cho nhà máy

Tất cả đều mới ở mức đề xuất, vì chưa được kiểm chứng trên dữ liệu độc lập hoặc máy thật.

1. **Khởi tạo một máy:** thu nền → tính bậc lỗi từ mã ổ bi → cấy lỗi vòng trong và ngoài → huấn luyện RF 50 cây → đóng băng tham chiếu HI.
2. **Khi chạy, mỗi cửa sổ:** tính đặc trưng → HI → so ngưỡng theo máy, 5 bản liên tiếp.
3. **Sau cảnh báo:** làm mượt xác suất, chờ ổn định rồi mới hiện loại lỗi, kèm mức tin cậy. Vòng cách và lỗi lạ báo "chưa xác định".
4. **Không hiện RUL** cho tới khi có phương pháp đạt yêu cầu; chỉ hiện đường HI và giai đoạn.

## Việc tiếp theo

1. Sửa công thức vòng cách, rồi kiểm chứng trên ổ khác. Hiện chỉ có 2 ổ vòng cách XJTU đã bị mở, nên sửa xong chỉ còn là khám phá cho tới khi có dữ liệu mới.
2. Đo độ trễ trên Pi 5 thật.
3. Đánh giá theo giai đoạn đời: đúng loại lỗi ở 50–90% đời, không chỉ 10% cuối.
4. Hỏi DENSO: dữ liệu theo tháng, cảnh báo trước bao lâu là đủ. Nếu chỉ cần giai đoạn, có thể bỏ hẳn RUL.

## Tái lập

```bash
conda activate anchorspec && cd anchorspec
python test_anchorspec.py
python tn2b_xjtu.py smoke   # freeze, test: test từ chối chạy lại
python tn3b_stream.py       # cần cache đặc trưng từ tn3_trend.py
python speed_check.py
```
