# Kế hoạch AnchorSpec v1.5 — 01/11/2026

## Cập nhật sau E1–E8 và X1–X9 (ưu tiên hơn các phần dưới nếu mâu thuẫn)

Xem [kết quả đầy đủ](../results/KET_QUA_E1_E8_20261101.md). E8 trên 20 ổ độc lập: **phát hiện đạt rất tốt, tự nhận loại lỗi trượt**.

**Câu chốt thay thế:**
> Chỉ với cảm biến rẻ sẵn có và dữ liệu bình thường, hệ thống học nền riêng cho từng máy và cảnh báo khi máy lệch nền, không cần chờ hỏng. Loại lỗi là gợi ý cho kỹ sư, và tốt dần khi kỹ sư xác nhận vài lỗi thật của chính máy đó.

| Hạng mục | Quyết định đề xuất | Căn cứ |
|---|---|---|
| Sản phẩm chính | **Phát hiện theo máy + 4 mức trạng thái làm nền; trọng tâm trả lời Bài 2 là cấy + vài sự kiện xác nhận. Cần đội chốt** | E8: HI bắt 100% vòng trong và ngoài, nhưng phần còn thiếu theo trao đổi với DENSO là Bài 2, Bài 3 |
| Loại lỗi | **Hạ từ KPI xuống gợi ý.** Bỏ chỉ tiêu "≥ 80% không cần lỗi thật" | E8: 0,41 khi đã biết là lỗi, không hơn đoán ngẫu nhiên |
| Nhận loại lỗi về sau | Cấy + vài sự kiện lỗi thật đã xác nhận. **Khám phá, chưa xác nhận** | X1, ổ khác cùng giàn, 1 sự kiện mỗi loại: vòng trong và ngoài 0,820 lên 0,916 (XJTU), 0,418 lên 0,718 (UORED). Nhánh cùng ổ không dùng làm bằng chứng |
| Nền | Làm mới có xác nhận, không tự động; kỹ sư xác nhận nền ban đầu | X2: báo nhầm giảm còn 0,098 nhưng phát hiện giảm còn 0,379; tự động báo nhầm 0,63. E8: 3 ổ nền cao không bị phát hiện |
| Học lại | **Mọi lô cần hai người xác nhận** | E6: cổng tự động trượt |
| Phần cứng | **Giữ 1 kHz; 6 kHz là nhánh thử trên phần cứng** | X8 không đạt chỉ tiêu báo nhầm; X9 có tín hiệu tốt ở HUST nhưng UORED kém vòng trong |
| Mô hình | Giữ RF, chưa cần GPU; không dùng micro | X6, X4 |
| Thư viện lỗi công khai | Không dùng làm dữ liệu chính | E3 |

**E9, E10 đã chạy (X1, X2), xem [kết quả Modal](../results/KET_QUA_MODAL_X1_X9_20261101.md).** Thí nghiệm tiếp theo xếp theo giá trị cho quyết định ở [báo cáo tiến độ 03/11](../results/BAO_CAO_TIEN_DO_20261103.md): trước hết là đường cong học theo sự kiện và xác nhận độc lập lần 3; các câu hỏi về báo nhầm dài hạn và lớp lỗi của DENSO cần **dữ liệu thật từ nhà máy**. Điểm yếu chưa giải quyết: nhận lỗi lạ (AUROC 0,55–0,56).

**Chỉ tiêu cần cả đội chốt lại:** bảng chỉ tiêu dưới đây viết trước E8. Đề xuất chuyển KPI chính sang tỉ lệ sự kiện được phát hiện, thời gian báo trước và số cảnh báo sai/máy/tháng; độ đúng loại lỗi chỉ đo sau khi đã có lỗi xác nhận của máy.

Thay phần phương pháp của v1.4 dựa trên các thử nghiệm đã chạy từ 31/10 đến 01/11 và [tra cứu thực tiễn công nghiệp](../research/THUC_TIEN_CONG_NGHIEP_BAO_TRI_DU_DOAN_20261101.md). PDF v1.4 không có trong repo nên tôi đối chiếu qua `ANCHORSPEC_HANDOFF.md`. **Đây là đề xuất; các chỉ tiêu cần Minh và cả đội chốt.**

## Tóm tắt

**Không có quy trình nào hoàn hảo, và không nguồn đáng tin nào đã đọc chứng minh được điều đó.** Cái làm được là một hệ thống biết khi nào nó chắc, biết nói "chưa rõ", và kỹ sư kiểm tra được bằng chứng.

**Thay đổi lớn nhất:** bỏ một bộ phân loại tự quyết trên từng cửa sổ. Thay bằng phễu 5 tầng, giống cách Augury, Bosch ODiN và Ronds mô tả hệ thống của họ.

**Câu chốt viết trước E8, đã được thay ở phần cập nhật:**
> Chỉ với cảm biến rẻ sẵn có và dữ liệu bình thường, hệ thống học nền riêng cho từng máy, cảnh báo khi máy lệch nền, rồi đưa cho kỹ sư loại lỗi khả dĩ kèm bằng chứng phổ. Khi không đủ chắc, hệ thống nói chưa rõ. Mỗi lỗi kỹ sư xác nhận lại giúp máy đó chẩn đoán tốt hơn.

## Đổi gì so với v1.4

| Hạng mục | v1.4 | v1.5 | Vì sao |
|---|---|---|---|
| Quyết định | Theo từng cửa sổ | **Gộp theo giờ hoặc ca** | Augury khoảng 1,3 điểm/máy/giờ; hỏng ổ bi diễn tiến chậm |
| Nền | Vài chục cửa sổ | **Nhiều ngày, nhiều trạng thái máy** | ODiN học vài ngày đến vài tháng; TN1: đa dạng tải tăng 1 HP từ 0,50 lên 1,00 |
| Phát hiện và phân loại | Chung một mô hình | **Tách riêng; phân loại chỉ chạy sau cảnh báo** | 46% nửa đầu đời bị gọi là lỗi khi chạy liên tục |
| Đầu ra loại lỗi | Luôn chọn một lớp | **Đa nhãn, có "chưa rõ", kèm bằng chứng** | Lớp chưa biết 0,55–0,80; đa nhãn của Vieira et al. |
| Hiệu chỉnh tham số cấy | ABC riêng từng lớp | **Bỏ; dùng tiên nghiệm rộng** | TN2: A 0,463, A0 0,824; Hemmer et al. |
| Vòng cách | Kỳ vọng "Tốt" | **Rút lại. Báo bất thường chưa rõ, học từ lỗi thật xác nhận** | 0,009; Masteel không cảnh báo được trước 24 giờ |
| Bài 3 | Thời gian còn lại | **4 mức trạng thái và đường HI; thời gian chỉ là thử nghiệm** | Dưới 12% trong sai số ±20% |
| Vị trí ổ hỏng | Ngầm định theo ổ | **Theo cụm máy, trừ khi có nhiều cảm biến** | IMS không phân biệt được ổ cùng trục |
| Báo nhầm | Chỉ ghi lại | **Chỉ số chính thứ hai: số cảnh báo sai/máy/tháng và phút kỹ sư** | Mô hình nhẹ nhưng báo sai nhiều vẫn không dùng được |
| Học lại | Một cổng trên lỗi cấy | **Hai vòng học riêng, cổng có lỗi thật và kiểm tra vật lý** | Cổng hiện nhận 79/90 lô nhãn sai |

**Giữ nguyên:** mỗi máy một mô hình, cấy lỗi vào nền thật, RF, HI tham chiếu đóng băng, chỉ đọc không ghi PLC, chia theo ổ bi, freeze trước khi mở test.

## Kiến trúc phễu

| Tầng | Việc làm | Chạy ở đâu | Kỹ sư thấy gì |
|---|---|---|---|
| **0. Chất lượng và trạng thái** | Kiểm tra cảm biến, bão hòa, máy chạy hay dừng; gắn nhãn tốc độ và tải; bỏ đoạn quá độ | Biên | Cảnh báo cảm biến lỗi |
| **1. Đặc trưng** | Mỗi cửa sổ tính đặc trưng, phổ và phổ bao hình; cộng dồn theo giờ hoặc ca | Biên, mục tiêu < 100 ms | Không |
| **2. Phát hiện theo máy** | Mahalanobis đóng băng theo từng trạng thái, hoặc điểm autoencoder DENSO nếu xuất được; cần nhiều lần liên tiếp; đường riêng cho thay đổi đột ngột | Biên | 4 mức: Bình thường, Theo dõi, Cảnh báo, Nguy hiểm |
| **3. Bằng chứng loại lỗi** | Chỉ chạy sau tầng 2. Mỗi loại lỗi một bộ riêng: mô hình học từ lỗi cấy cộng thư viện lỗi thật, đối chiếu đỉnh phổ tại BPFO, BPFI, FTF | Biên hoặc máy chủ | Loại khả dĩ, mức tin cậy, hình phổ; hoặc "chưa rõ" |
| **4. Người chốt và học** | Kỹ sư xác nhận. Vòng A học cảnh báo nào đáng quan tâm. Vòng B cập nhật mô hình lỗi qua cổng | Máy chủ | Ô chọn loại lỗi, lịch sử phiên bản |

**Định nghĩa lại "thời gian thực":** tầng 0–2 chạy liên tục để không bỏ lỡ đột biến, còn kết luận loại lỗi đưa ra theo giờ hoặc ca. Cần hỏi DENSO có đồng ý cách này không.

## Thí nghiệm tiếp theo

Tất cả chạy được bằng CPU. **E1–E6 là khám phá vì dữ liệu đã xem; chỉ E8 là xác nhận.** Hiệu quả dưới đây là giả thuyết, chưa đo.

| # | Thí nghiệm | Giả thuyết | Dữ liệu | Thước đo chính | Thời lượng ước tính |
|---|---|---|---|---|---:|
| **E1** | Nền dài, nhiều trạng thái, gộp theo thời gian | Giảm mạnh báo nhầm, không mất nhiều phát hiện | XJTU, FEMTO, IMS, CWRU | Tỉ lệ ổ cảnh báo trước 50% đời; phát hiện | 1 ngày |
| **E2** | Hai tầng + đa nhãn + được phép "chưa rõ" + đối chiếu vật lý | Câu trả lời đưa ra đúng hơn hẳn | XJTU, Paderborn | Đường cong độ đúng theo tỉ lệ trả lời | 1 ngày |
| **E3** | Đặc trưng theo miền bậc, thêm thư viện lỗi thật công khai | Nhiều ổ thật giúp hơn thêm mẫu | Bỏ từng bộ dữ liệu ra để kiểm | Macro theo ổ | 1 ngày |
| **E4** | Quét băng thông 1 / 1,56 / 2 / 6 kHz | Cho biết nên đề nghị phần cứng gì | XJTU, IMS, Paderborn | Thời điểm phát hiện, độ đúng theo giai đoạn | 0,5 ngày |
| **E5** | Giám sát dài hạn 3 trục, 2 kHz | Đo được trôi theo thời gian giữa máy và đợt | Bosch CNC (khoảng 900 MB) | Báo nhầm theo máy và đợt | 1 ngày |
| **E6** | Cổng học lại v2 + mô hình cảnh báo có đáng quan tâm | Chặn được nhãn sai | XJTU, kỹ sư giả lập | Chặn lô sai; nhận lô đúng; báo nhầm giảm | 1 ngày |
| **E7** | 4 mức trạng thái + đường thay đổi đột ngột | Rõ ràng và ổn định hơn RUL | XJTU, FEMTO, IMS | Số lần đổi mức ngược; mức trước hỏng | 0,5 ngày |
| **E8** | **Xác nhận độc lập một lần** | Thiết kế đã freeze giữ được trên ổ mới | UORED-VAFCLS, chưa mở | Tất cả chỉ tiêu dưới đây | 1 ngày |

**Vì sao chọn [UORED-VAFCLS](https://data.mendeley.com/datasets/y2px5tg92h/5) để xác nhận:** chưa từng dùng; 20 ổ gồm 5 mỗi loại vòng trong, vòng ngoài, bi, vòng cách; mỗi ổ có 3 trạng thái bình thường, lỗi đang phát triển, lỗi nặng. Nó trả lời cùng lúc ba câu đang thiếu: **lỗi sớm, vòng cách và lỗi chưa biết**. Giới hạn: mỗi trạng thái chỉ 10 s, nên nền rất ngắn. Trước khi dùng phải đọc bài Data in Brief để xác nhận cách tạo lỗi, thông số ổ và giấy phép.

**Nếu thiếu thời gian, làm theo thứ tự:** E2 → E1 → E8 → E4 → E6 → E3 → E7 → E5.

## Chỉ tiêu đề xuất

Số "hiện tại" lấy từ các đợt chạy trước, phần lớn là khám phá và không cùng dữ liệu với E8. Số "mục tiêu" là đề xuất của tôi, không phải chuẩn ngành: tôi không tìm được chuẩn công khai nào.

| Chỉ tiêu | Hiện tại | Mục tiêu E8 | Mục tiêu trên máy DENSO |
|---|---|---|---|
| Đúng loại khi trả lời (vòng trong, ngoài) | 0,775 (trả lời mọi mẫu) | ≥ 0,85 | ≥ 0,80, kèm số sự kiện |
| Tỉ lệ được trả lời | 100%, buộc phải chọn | ≥ 60% | ≥ 60% |
| Bình thường bị báo lỗi | Đúng 0,785 ở đoạn ngay sau nền | ≤ 10% | ≤ 1 cảnh báo sai/máy/tháng, đo khi có dữ liệu |
| Phát hiện lỗi đang phát triển | Chưa đo đúng cách | Báo cáo trung thực, không đặt ngưỡng | Lead time theo sự kiện |
| Nhận ra lỗi chưa biết | AUROC 0,55–0,80 | ≥ 0,85 | ≥ 0,85 nếu có dữ liệu |
| Cổng học lại | Chặn 11/90 lô sai, nhận 78/90 lô đúng | Chặn ≥ 90%, nhận ≥ 80% | Như vậy |
| Độ trễ cửa sổ | Khoảng 19 ms trên laptop | Giữ | < 100 ms trên Pi 5 |
| Khởi tạo máy mới | 1,4–2,6 s phần tính | Giữ | < 1 ngày, gồm thu nền |

**Quy tắc khi trượt:** ghi kết quả trượt, sửa thiết kế, và chỉ xác nhận lại trên dữ liệu chưa mở. Không điều chỉnh chỉ tiêu sau khi xem kết quả.

## Lộ trình

Mốc 16/11, 27/11, 02/12 vẫn cần xác nhận với BTC.

| Giai đoạn | Việc chính | Cổng |
|---|---|---|
| **01–02/11** | Rà số liệu; chạy E2, E1; làm slide | Minh rà xong |
| **03/11, báo cáo** | Trình bày trung thực và hướng mới; xin dữ liệu | DENSO trả lời câu hỏi 1–4 bên dưới |
| **04–08/11** | E4, E6, E3; viết giao thức và freeze; **E8 một lần** | Cổng G1 mới: E8 đạt, hoặc báo trượt và nói rõ sẽ sửa gì |
| **09–15/11** | Máy 1: chạy lại offline dữ liệu DENSO theo thứ tự thời gian, đo báo nhầm | Kỹ sư DENSO rà ít nhất một loạt cảnh báo |
| **16–22/11** | Trình bày vòng 1; lỗi thật đã xác nhận; học lại; máy 2; E7, E5 | Đo thời gian khởi tạo máy 2 |
| **23–27/11** | Đánh giá cuối do Minh giám sát; Pi 5; đóng băng | 27/11 khóa mã và số liệu |
| **28/11–02/12** | Video, slide | Chung kết |

### Chia việc đề xuất

| Người | Phần việc |
|---|---|
| **Quyền** | E2, E3, E6; bộ phân loại đa nhãn và cổng học lại |
| **Trường** | Tầng 0–1, E4, E5; Pi 5 |
| **Bảo** | E1 phần HI theo trạng thái, E7 |
| **Minh** | Giao thức E8, chia tập, phủ quyết số liệu, chạy E8 |
| **Tới** | Câu hỏi DENSO, giao diện 4 mức và ô xác nhận, demo |

**Thứ tự cắt khi thiếu thời gian:** E5 → E7 → máy 2 → Pi 5 (demo laptop) → E3. **Không cắt:** E8, tách hai tầng, "chưa rõ", cổng học lại, rà soát số liệu.

## Buổi thứ Ba 03/11 nên nói gì

**Bản mới nhất, có đính chính số liệu: [báo cáo tiến độ 03/11](../results/BAO_CAO_TIEN_DO_20261103.md).** Mục dưới đây viết trước X1–X9.

1. **Kết quả thật:** phát hiện theo máy mạnh (E8: 100% cửa sổ vòng trong và ngoài, nhưng chưa đo được báo nhầm dài hạn). Nhận loại lỗi không cần lỗi thật **không qua được xác nhận độc lập** (E8: 0,41), dù XJTU-SY từng đạt 0,775. Báo nhầm dài hạn là rủi ro lớn (Bosch: 0,60 với nền cố định).
2. **Điều đã học được:** nhiều số 99% trong tài liệu do chia tập rò rỉ. Công nghiệp không dùng một bộ phân loại tự quyết, mà dùng phễu với kỹ sư chốt.
3. **Hướng mới:** phát hiện và mức trạng thái là sản phẩm chính; loại lỗi là gợi ý, tốt dần nhờ lỗi thật được kỹ sư xác nhận. Đã rút lại vòng cách, RUL theo giờ.
4. **Việc cần DENSO:** các câu dưới đây.

**Không nên nói:** "độ chính xác cao", "phát hiện sớm", "hoàn hảo", hoặc trích 0,824 và 0,795 mà không kèm giới hạn.

## Câu hỏi cho DENSO, xếp theo mức ảnh hưởng

1. **Mã cảm biến, băng thông thật, dải đo, gá thế nào; mỗi máy có mấy cảm biến, cách nhau bao xa?** Quyết định có thấy được giai đoạn sớm và có định vị được cụm không.
2. **Dữ liệu bình thường dạng sóng thô, kèm trạng thái máy (chương trình, tốc độ, tải), bao nhiêu ngày?** Quyết định tầng 0 và 2.
3. **Nhật ký hỏng thật, kể cả vỡ vòng cách ở máy thử ổ bi:** ngày, bộ phận, ảnh, ai xác nhận.
4. **Thời gian đủ để lên kế hoạch thay là bao lâu? Kết luận theo giờ hoặc ca có chấp nhận được không?** Nếu đủ bằng mức trạng thái thì có thể bỏ hẳn RUL.
5. Có xuất được điểm autoencoder theo thời gian, và giữ một bản đóng băng không?
6. Mỗi cảnh báo tốn kỹ sư bao nhiêu phút? Có thêm được ô chọn loại lỗi không?
7. Có được chạy song song không tác động lên máy thật không? Dữ liệu có cần NDA không?

## Rủi ro còn lại, kể cả làm đúng kế hoạch

| Rủi ro | Hệ quả | Cách xử lý |
|---|---|---|
| Băng thông chỉ khoảng 1 kHz | Khó cảnh báo sớm, chủ yếu thấy giai đoạn muộn | Nói rõ; dùng E4 để đề xuất nâng cảm biến cho máy quan trọng |
| Vòng cách vẫn không nhận được | Không có chẩn đoán vòng cách từ đầu | Báo "bất thường chưa rõ", học từ lỗi thật |
| Nền của máy đã có lỗi sẵn | Lỗi bị học thành bình thường | Kỹ sư xác nhận nền; so nhiều máy cùng loại nếu có |
| Không đủ lỗi thật của DENSO | Chỉ đánh giá được vài sự kiện | Báo số sự kiện, không dùng phần trăm một mình |
| E8 trượt | Không có kết quả xác nhận cho vòng 1 | Báo thật, trình bày phần còn đạt |
| Máy đổi chế độ thường xuyên | Báo nhầm nhiều | Tầng 0 phải có nhãn từ PLC hoặc tự phân cụm trạng thái |
