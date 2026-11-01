# Kết quả các việc chạy bằng CPU — 01/11/2026

**Dữ liệu công khai, chưa có dữ liệu DENSO, Minh chưa rà soát.** Kết quả mới hơn, gồm xác nhận độc lập E8: [báo cáo E1–E8](KET_QUA_E1_E8_20261101.md). Tiếp nối [báo cáo TN2b, TN3b](KET_QUA_TN2B_TN3B_REALTIME_20261101.md).

Chỉ **TN2c** có giao thức ghi trước và mở test một lần. Mọi việc còn lại là **khám phá** trên dữ liệu đã xem, không dùng làm bằng chứng xác nhận.

## Kết luận

| Việc | Kết quả | Hệ quả |
|---|---|---|
| **TN2c: giàn IMS** | A0 0,795 so với CWRU 0,093, nhưng ổ đối chứng chỉ đúng bình thường **14%** | Chưa có độ đặc hiệu trên giàn khác |
| **Theo giai đoạn đời** | Vòng ngoài 0,43 → 0,64 → 0,75 → 0,88; vòng trong 0,38 → 0,43 → 0,53 → 0,72 (lần lượt 30–50, 50–70, 70–90, 90–100% đời) | Mạnh dần về cuối đời; chưa đủ tin ở giữa đời |
| **Lớp chưa biết** | AUROC 0,55 / 0,80 / 0,80 | **Trượt** chỉ tiêu 0,85 |
| **Vòng học lại** | Vòng cách 0,07 → 0,80–0,96 sau 3–10 cửa sổ xác nhận | Lợi ích lớn nhất đo được, nhưng **cổng không chặn được nhãn sai** |
| **Vòng cách v2** | 0,009 → 0,232, đổi lại vòng trong và ngoài giảm | Chưa dùng; giữ công thức cũ |
| **MiniRocket** | Trong và ngoài 0,32 so với A0 0,775 | Không dùng ở cấu hình đã thử |
| **Khởi tạo máy** | 1,4–2,6 giây phần tính toán | Đạt mục tiêu < 1 ngày cho phần tính toán |
| **Tốc độ ở 900 rpm** | Sai số lớn nhất 0,57% với 20 bản ghi | Đạt; nhưng 1,43% nếu tốc độ danh định lệch 2% |
| **TN1 nhiều tải** | 0,50 → 1,00 ở 1 HP khi học 0 + 2 HP toàn bộ cửa sổ | Khác biệt tải quan trọng hơn cấu hình mô hình |

## TN2c — Kiểm chứng trên giàn IMS

[Giao thức](../../anchorspec/PROTOCOL_TN2C.md) ghi trước; ổ đũa hai dãy ZA-2115; 3 ổ hỏng, 8 ổ đối chứng; 3 seed. Quá ít ổ nên không có CI.

| Nhánh | Chỉ số chính, 10% cuối | t1_b3 vòng trong | t2_b1 vòng ngoài | t3_b3 vòng ngoài | Chỉ số chính, 2% cuối | Đối chứng đúng bình thường |
|---|---:|---:|---:|---:|---:|---:|
| **A0** | **0,795** | 0,805 | 0,980 | 0,590 | 0,888 | **0,140** |
| C, CWRU | 0,093 | 0,009 | 0,340 | 0,014 | 0,065 | 0,540 |
| P, quy tắc vật lý | 0,000 | 0,000 | 0,000 | 0,002 | 0,002 | 0,998 |

**Đọc kết quả.**
- Tiêu chí mô tả A0 ≥ C đạt, nhưng **A0 gọi gần như mọi thứ cuối thí nghiệm là lỗi**: ổ đối chứng bộ 1 và 2 đúng 0%. Vì vậy 0,795 chỉ cho biết phân biệt được loại lỗi khi đã giả định có lỗi, không cho biết có lỗi hay không.
- P bảo thủ ở chiều ngược lại: gần như không bao giờ báo lỗi.
- **Cổng HI cũng không cứu được ở đây.** Với z=10, ổ đối chứng t2_b3 và t2_b4 báo ở 91–93% đời, sớm hơn ổ hỏng t2_b1 ở 95%. Các ổ cùng một trục nên HI riêng từng ổ khó chỉ ra ổ nào hỏng. Máy DENSO cần được kiểm tra điều này khi có nhiều ổ gần nhau.

**Giới hạn.** Bậc lỗi từ nguồn thứ cấp, đã đối chiếu đỉnh phổ (231 Hz so với 236,4 Hz); đối chứng có thể đã suy giảm mà không được ghi nhận; bộ 3 không khớp readme.

## Độ đúng theo giai đoạn đời (XJTU-SY)

A0 RF 200 cây, trung bình trượt K=5. `Gọi bình thường` là tỉ lệ cửa sổ bị coi là bình thường.

| % đời | Vòng trong: đúng / gọi bình thường | Vòng ngoài: đúng / gọi bình thường | Vòng cách: đúng / gọi bình thường |
|---|---|---|---|
| 0–30 | 0,24 / 0,71 | 0,18 / 0,72 | 0,00 / 0,82 |
| 30–50 | 0,38 / 0,43 | 0,43 / 0,39 | 0,00 / 0,20 |
| 50–70 | 0,43 / 0,46 | 0,64 / 0,11 | 0,03 / 0,00 |
| 70–90 | 0,53 / 0,44 | 0,75 / 0,00 | 0,08 / 0,00 |
| 90–100 | 0,72 / 0,07 | 0,88 / 0,00 | 0,00 / 0,00 |

Nhãn chỉ biết chắc ở cuối đời; đầu đời có thể chưa có lỗi nên điểm thấp ở đó không hẳn là sai. Thử nghiệm tăng tốc nên % đời không quy đổi được sang thời gian ở nhà máy.

## Lớp chưa biết

Bỏ một lớp khỏi huấn luyện rồi đo ở mức ổ bi, với điểm lạ là 1 − xác suất lớn nhất.

| Lớp đã biết → chưa biết | AUROC | Số ổ chưa biết / đã biết |
|---|---:|---|
| Trong + ngoài → cách | 0,545 | 2 / 11 |
| Ngoài + cách → trong | 0,800 | 3 / 10 |
| Trong + cách → ngoài | 0,800 | 8 / 5 |

**Trượt chỉ tiêu 0,85**, nhất là vòng cách, loại chưa biết thực tế nhất. Khoảng cách tới tâm lớp cho kết quả không ổn định (0,14–0,88). Số ổ rất ít.

## Vòng học lại có rào chắn

`anchorspec/retrain.py` cài đủ các rào chắn của v1.4 và có kiểm thử đơn vị. Thử nghiệm: thêm k cửa sổ đầu của 10% cuối đời, đo ở nửa sau.

| Lớp | Ban đầu | k=3 | k=5 | k=10 | Độ đúng nếu nhãn sai, k=3 / 5 / 10 |
|---|---:|---:|---:|---:|---|
| Vòng trong | 0,833 | 0,803 | 0,800 | 0,815 | 0,752 / 0,706 / 0,693 |
| Vòng ngoài | 0,879 | 0,993 | 0,954 | 0,997 | 0,370 / 0,338 / 0,563 |
| Vòng cách | 0,074 | 0,799 | 0,957 | 0,926 | 0,012 / 0,000 / 0,012 |

- **Vài lỗi thật đã xác nhận cải thiện rất nhiều**, nhất là vòng cách. Đây là hướng thực tế hơn việc cố hoàn thiện công thức, nhưng đo trên cùng một ổ và các cửa sổ sát nhau trong thời gian, nên rất lạc quan.
- **Lỗ hổng nghiêm trọng: cổng gần như không chặn nhãn sai**, vì bộ kiểm tra cố định chỉ gồm lỗi cấy và đoạn khỏe, không có lỗi thật. Lô nhãn sai vẫn được nhận 32/36, 30/36 và 17/18 lần ở k=3, 5, 10, và độ đúng rơi mạnh. Lô nhãn đúng được nhận 31/36, 30/36 và 17/18, tức cổng gần như không phân biệt hai trường hợp. Cần bổ sung, ví dụ yêu cầu xác nhận lần hai khi nhãn trái với dự đoán của mô hình, và đưa lỗi thật đã duyệt vào bộ cố định.
- Bộ cố định khoảng 95 mẫu với dung sai 2% nghĩa là 2 lỗi đã đủ từ chối, nên một số lô đúng cũng bị từ chối.

## Thử công thức vòng cách v2 và MiniRocket

**Vòng cách v2:** xung theo chu kỳ FTF kèm cụm nhiễu. Macro theo lớp: trong 0,573, ngoài 0,821, cách 0,232. So với A0 (0,674 / 0,875 / 0,009), vòng cách chỉ nhích nhờ 1_4 (0,44), còn 2_3 vẫn 0,02 và 3_5 bị gán hẳn sang vòng cách. Hai ổ vòng cách đã bị mở, nên chỉ thử một lần và không tinh chỉnh tiếp. **Không dùng**, và giữ khuyến nghị không hứa vòng cách.

**MiniRocket:** 2.000 kernel + Ridge trên cùng dữ liệu cấy. Trong 0,304, ngoài 0,337, cách 0,569, bình thường 0,923; 25 ms; 0,06 MB. Thua A0 rõ ở vòng trong và ngoài, nhưng cao hơn ở vòng cách. Chỉ một cấu hình, môi trường riêng `anchorspec-rocket`, chưa đủ kết luận chung về MiniRocket.

## Tốc độ, khởi tạo, TN1 nhiều tải

**Tốc độ ở 900 rpm**, K001–K004, tìm ±3%:

| Tốc độ danh định | 1 bản ghi: trung vị / max | 5 bản ghi | 20 bản ghi (80 s) |
|---|---|---|---|
| Đúng | 1,11% / 3,03% | 0,04% / 1,64% | 0,17% / **0,57%** |
| Lệch +2% | 0,95% / 5,01% | 0,53% / 3,90% | 0,54% / 1,43% |

Dùng được khi máy chạy ổn định và biết tốc độ danh định gần đúng. Chưa xử lý máy đổi tốc độ. Chỉ 4 phép đo ở mức 20 bản ghi.

**Khởi tạo một máy:** RF 50 cây, vòng trong và ngoài, 150 mẫu cấy/lớp, một luồng, laptop: **1,4–2,6 giây, mô hình 0,24–0,27 MB**. Chưa tính thời gian thu nền, nhập mã ổ bi, và chạy trên Pi 5.

**TN1 nhiều tải**, S4, độ đúng 4 lớp:

| Cấu hình | 1 HP | 3 HP |
|---|---:|---:|
| 0 HP, neo (gốc) | 0,496 | 0,880 |
| 0 HP, toàn bộ cửa sổ | 0,747 | 0,760 |
| 0 + 2 HP, neo | 0,842 | 0,992 |
| **0 + 2 HP, toàn bộ cửa sổ** | **0,999** | **1,000** |
| 0 HP, neo, nền từng tải | 0,654 | 0,736 |
| 0 + 2 HP, toàn bộ, nền từng tải | 0,958 | 0,864 |

Đa dạng tải giúp nhiều hơn thêm mẫu cùng tải: riêng thêm mẫu 0 HP còn làm lớp bình thường gần như mất hẳn (0–4%). Mô hình đã thấy 2 tải nên 1 HP là nội suy, 3 HP là ngoại suy gần. CWRU dễ và cả hai tải đã xem, nên **không suy ra được cho máy DENSO**. Gợi ý thực tế: thu nền ở nhiều tải khi khởi tạo.

## Ý nghĩa cho thiết kế

1. **Giữ:** cấy lỗi riêng từng máy, RF gọn, cổng HI, không hiện RUL.
2. **Thêm:** thu nền ở nhiều điều kiện tải khi khởi tạo; học lại theo lỗi thật đã xác nhận, nhất là với vòng cách.
3. **Phải sửa trước khi vận hành:** cổng học lại với nhãn sai; độ đặc hiệu khi các ổ cùng trục; điểm lớp chưa biết.
4. **Vẫn chưa đo được:** Pi 5, đủ 3 trục, dữ liệu DENSO. Công thức dị vật và hết dầu vẫn chưa đối chiếu với lỗi thật.

## Tái lập

```bash
conda activate anchorspec && cd anchorspec
python test_anchorspec.py
python tn1b_multiload.py
python speed_check2.py
python tn2c_ims.py check && python tn2c_ims.py test   # test từ chối chạy lại
python tn5_stage_unknown.py
python tn6_retrain_cage.py
conda run -n anchorspec-rocket python tn7_minirocket.py
```
