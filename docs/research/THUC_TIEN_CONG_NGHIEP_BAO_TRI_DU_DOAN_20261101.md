# Công nghiệp thực sự làm chẩn đoán ổ bi như thế nào — 01/11/2026

Tra cứu để trả lời: vì sao thử nghiệm của AnchorSpec yếu, và nhà máy lớn làm khác gì. Kế hoạch rút ra từ đây nằm ở [kế hoạch v1.5](../plans/KE_HOACH_ANCHORSPEC_v1.5.md).

## Kết luận

1. **Số của ta yếu, nhưng phần lớn không phải vì ta kém hơn hẳn người khác.** Nhiều bài báo đạt 99–100% vì chia tập rò rỉ. Khi chia đúng theo ổ bi, một nghiên cứu độc lập chỉ còn 94,8% / 53,9% / 78,7% cho vòng trong, vòng ngoài, bi trên CWRU.
2. **Không nhà máy hay hãng nào trong các nguồn đã đọc dùng một bộ phân loại tự quyết định trên từng cửa sổ 1 giây.** Họ dùng một phễu nhiều tầng: học nền dài theo từng máy, lọc theo trạng thái máy, gộp bằng chứng theo thời gian, và chuyên gia chốt.
3. **Lỗi lớn nhất của ta là thiết kế, không phải thuật toán:** nền quá ngắn (30 bản ghi) và một mô hình làm cả hai việc phát hiện và phân loại. Đây là nguyên nhân hợp lý nhất của việc gọi gần như mọi thứ là lỗi, và sẽ được kiểm chứng ở E1, E2.
4. **Có những giới hạn vật lý thuật toán không vượt qua được.** Băng 1 kHz khó thấy giai đoạn sớm, và vỡ vòng cách đã có tiền lệ không cảnh báo được trên máy thật.
5. **"Hoàn hảo" không có trong bất kỳ nguồn nào.** Con số cao nhất tìm được là tự công bố và không có phương pháp đo.

## Cách đọc độ tin cậy

| Mức | Loại nguồn |
|---|---|
| **A** | Bài báo có phương pháp, đã đọc nội dung |
| **B** | Tài liệu chính thức của công ty, báo cáo thường niên, bài nói kỹ thuật của chính kỹ sư công ty |
| **C** | Tuyên bố của hãng, hoặc chỉ đọc được đoạn trích |
| **D** | Blog, bài cộng đồng, số không có nguồn |

## Nhà máy và hãng lớn

### Bosch

| Quan sát | Mức | Nguồn |
|---|---|---|
| ODiN học trạng thái bình thường riêng từng bộ phận rồi theo dõi chỉ số sức khỏe. Tại Kraiburg, giai đoạn học kéo dài **vài tháng**. | B | [Fluid Power World](https://www.fluidpowerworld.com/predictive-maintenance-radial-piston-motors-prevents-downtime-rubber-industry/) |
| ODiN **không cảnh báo khi một tín hiệu lệch thoáng qua**; cảnh báo khi nhiều cảm biến cùng làm chỉ số xấu đi, dù từng giá trị còn trong giới hạn. | B | Cùng nguồn |
| Thời gian học có thể chỉ vài ngày nếu máy lặp lại công việc trong điều kiện giống nhau, lâu hơn nếu cách dùng thay đổi. | C | [Industrial Production](https://www.industrial-production.de/hydraulics---pneumatics/predictive-maintenance-with-the-odin-service-package-from-bosch-rexroth.htm) |
| Tập dữ liệu CNC của Bosch Rexroth và TU Munich: cảm biến Bosch CISS **3 trục, 2 kHz**, 3 máy cũ trong sản xuất thật, 15 nguyên công, 6 đợt từ 10/2018 đến 8/2021, nhãn thủ công. | A | [GitHub Bosch Research](https://github.com/boschresearch/CNC_Machining), [UCI](https://archive.ics.uci.edu/dataset/752/bosch+cnc+machining+dataset) |
| CISS có chế độ đặc biệt 2 kHz cho gia tốc khi tắt cảm biến khác. Bài cộng đồng Bosch Sensortec ghi BMA280 có băng thông tối đa 1.000 Hz ở tốc độ 2.000 Hz; đây là cảm biến cùng lớp với giả định của ta. | C | [Datasheet CISS](https://www.mouser.com/datasheet/2/783/ciss_datasheet-1842703.pdf), [Diễn đàn Bosch Sensortec](https://community.bosch-sensortec.com/t5/MEMS-sensors-forum/Looking-for-Higher-Data-Rate-in-an-3-axis-Accelerometer/m-p/8659) |
| Nhà máy Moulins-Yzeure: nối mạng 150 máy trước, rồi chỉ gắn cảm biến rung cho **30 máy** trong 2017–2018; máy trung bình 15 năm tuổi. Bài không công bố thuật toán. | C | [JDN](https://www.journaldunet.com/iot/1191687-bosch-usine-maintenance-predictive/) |
| Bosch Wuxi được mô tả có dùng cảm biến MEMS lấy dữ liệu rung qua nền tảng Production Performance Manager. | C, đoạn trích | [AMS](https://automotivemanufacturingsolutions.com/technology/illuminating-the-way) |

**Ta không tìm được tài liệu nào của Bosch công bố thuật toán chẩn đoán ổ bi hoặc độ chính xác đã kiểm chứng độc lập.**

### Trung Quốc

| Quan sát | Mức | Nguồn |
|---|---|---|
| Ronds (容知日新): hơn **18 vạn thiết bị** giám sát từ xa, hơn **3 vạn ca hỏng** và nhãn do chuyên gia gán nhiều năm. | B | [Báo cáo thường niên 2024](http://notice.10jqka.com.cn/api/pdf/8d00f0e0c1bb72d5.pdf) |
| Ronds nêu cơ chế "人类监督闭环": **các quyết định then chốt phải được chuyên gia chẩn đoán rà lại**. | B | Cùng báo cáo, tr. 62 |
| Ronds lọc ở biên: tính và phán đoán thời gian thực, chỉ giữ dữ liệu có giá trị. Có trung tâm chẩn đoán từ xa. | B | Cùng báo cáo, tr. 18, 24 |
| Baowu được báo cáo đạt trên 90% độ đúng cảnh báo, chẩn đoán và khuyến nghị. **Chỉ là trích dẫn qua báo cáo môi giới, ta không tìm được phương pháp đo gốc.** | C | [Soochow Securities](https://pdf.dfcfw.com/pdf/H3_AP202207071575932597_1.pdf), tr. 13 |
| **Masteel: 3 lần vỡ vòng cách ở hộp số cán. Hai lần sau, cảm biến rung trực tuyến không bắt được bất thường trước 24 giờ.** Cách sửa là đổi vật liệu vòng cách. | A, tóm tắt | [《冶金动力》2024](https://search.napstic.cn/literature/periodical/010yjdl202406018) |
| Foxconn Thành Đô: OEE tăng 17% nhờ bảo trì dự đoán. Thái Nguyên Heavy: tỉ lệ hỏng thiết bị giảm 28%. Đây là kết quả kinh doanh, không phải độ chính xác mô hình. | C | [Foxconn](https://www.foxconn.com/en-us/press-center/events/industry-events/572), [WEF 2025](https://reports.weforum.org/docs/WEF_Global_Lighthouse_Network_2025.pdf) |
| WEF 2025: các nhà máy đầu đàn triển khai IoT **có chọn lọc** vào nơi lợi ích cao nhất, trong đó có bảo trì dự đoán. | B | Cùng báo cáo WEF |

Không tìm được số liệu công khai về chẩn đoán ổ bi của Haier, CATL, SANY. Các tên này xuất hiện trong danh sách WEF nhưng không có phương pháp.

### Augury

Đây là nguồn kỹ thuật chi tiết nhất, vì là bài nói của chính kỹ sư công ty ([Hila Fox, Conf42 2021](https://conf42.com/Machine_Learning_2021_Hila_Fox_Monitoring_AI_Pipelines_Output_As_Product), mức B):

- Khoảng **1,3 điểm dữ liệu mỗi máy mỗi giờ**, khoảng 1.000 đặc trưng mỗi máy mỗi giờ, trên 80.000 máy.
- Bộ phát hiện bất thường **lập nền tương đối cho từng máy**; bộ phát hiện lỗi tìm dấu hiệu riêng (ví dụ mòn ổ bi) và trả về độ tin cậy.
- **99,87% phát hiện không được chuyển tiếp** ra ngoài tầng quản lý; chúng bị lọc do độ tin cậy thấp hoặc theo trạng thái máy.
- Chuyên gia rung quyết định có phải thay đổi sức khỏe thật không, trước khi báo khách. Nhãn của họ quay lại để học.
- Bốn mức trạng thái: Acceptable, Monitor, Alarm, Danger ([Augury KB](https://endpoint.augury.com/en/kb/articles/111-onboarding-resources-for-new-users), mức B).
- Tuyên bố "99% không bỏ sót, ít hơn 20% báo nhầm" là tự công bố, và trang gốc nay không truy cập được. Đừng dùng làm chuẩn so sánh.

### Nhà máy thật có số liệu kiểm chứng

[Nghiên cứu tại nhà máy điện và luyện thép ở Ba Lan](https://pmc.ncbi.nlm.nih.gov/articles/PMC8749854/) (mức A), rất gần hoàn cảnh DENSO:

- Cảm biến MEMS 3 trục không dây, đến 2,5 kHz, lấy mẫu mỗi 10–30 giây, trên 2 máy nghiền và 2 cầu trục trong 4–20 tháng.
- Không cần nhãn hỏng ban đầu. **Một mô hình phụ học từ quyết định của người vận hành xem cảnh báo có đáng quan tâm không**, có giải thích SHAP.
- Báo nhầm giảm trung bình 90,25% so với bộ phát hiện đứng riêng; nhưng vẫn bỏ sót một giai đoạn trước hỏng ở một cầu trục, và điểm tổng hợp chỉ 0,237–0,804 tùy máy.
- Tác giả coi 2 tuần trước hỏng là bất thường thật. Đây là cách đánh giá ta có thể dùng lại.

## Học thuật

| Quan sát | Mức | Nguồn |
|---|---|---|
| Chia theo đoạn hoặc theo điều kiện cho kết quả gần hoàn hảo giả tạo. Chia theo ổ, CWRU còn 94,8% / 53,9% / 78,7%. | A | [Vieira et al. 2025](https://arxiv.org/pdf/2509.22267) |
| **Số ổ khác nhau quan trọng hơn số mẫu:** cùng lượng mẫu, nhiều ổ hơn cho kết quả tốt hơn. | A | Cùng bài |
| Trên 2/4 bộ dữ liệu, học nông thắng học sâu; học sâu dễ được thổi phồng khi rò rỉ. **Giữ RF là hợp lý.** | A | Cùng bài |
| Đa nhãn thay vì đa lớp: cho phép lỗi kết hợp, điểm vận hành rõ ràng. | A | Cùng bài |
| Không học lỗi thật: chiếu tín hiệu vào không gian đặc trưng bất biến bằng thuật toán vật lý, rồi phân loại, báo cáo trên 6 bộ dữ liệu **với tín hiệu chuyên gia chẩn đoán được**. Đây là công trình gần AnchorSpec nhất. | C, chưa đọc toàn văn | [Matania et al. 2025](https://www.sciencedirect.com/science/article/abs/pii/S088832702401015X) |
| Mô hình động lực học + bao hình + phổ bậc, không có mẫu lỗi thật khi học. | C, tóm tắt | [EAAI 2026](https://pure.nwpu.edu.cn/en/publications/a-zero-fault-sample-diagnosis-method-of-rolling-bearings-via-dyna/) |
| **Thay đổi rộng tham số mô phỏng** để học được đặc trưng khái quát. Phù hợp kết quả TN2, TN2b: tiên nghiệm rộng thắng hiệu chỉnh hẹp. | A | [Hemmer et al.](https://papers.phmsociety.org/index.php/ijphm/article/view/2615) |
| Sobie et al.: học trên mô phỏng, kiểm trên 4 bộ dữ liệu trong đó có một tua-bin gió, dự báo trước hơn 1 tháng. | A, tóm tắt | [PHM AP](https://papers.phmsociety.org/index.php/phmap/article/view/1778) |
| DCASE "first-shot": chỉ có dữ liệu bình thường, cấm tinh chỉnh theo máy, nền rất ít mẫu ở điều kiện mới (990 nguồn + 10 đích). Baseline: autoencoder + Mahalanobis chọn lọc theo miền. | A | [DCASE 2023](https://arxiv.org/pdf/2303.00455), [DCASE 2025](https://arxiv.org/pdf/2506.10097) |
| Từ chối lớp lạ bằng lý thuyết giá trị cực trị là cách phổ biến. Chưa thấy bài nào áp conformal cho từng máy; **đó là thử nghiệm của ta, không phải thực tiễn đã có.** | A, tóm tắt | [Yu et al.](https://scholar.xjtu.edu.cn/en/publications/deep-learning-based-open-set-fault-diagnosis-by-extreme-value-the/) |
| Nhãn sai làm giảm mạnh mô hình công nghiệp; ước lượng độ tin cậy nhãn từ tính nhất quán lân cận. | C, tóm tắt | [TII 2025](https://bura.brunel.ac.uk/handle/2438/32456) |
| Hai giai đoạn: dùng biểu đồ kiểm soát tìm điểm đổi, rồi mới mô hình hóa suy giảm; Wiener đơn thuần sai số lớn. | C, tóm tắt | [Li et al. 2024](https://researchonline.jcu.edu.au/93851/), [EiN](https://ein.org.pl/Two-stage-Remaining-Useful-Life-Prediction-Based-on-the-Wiener-Process-With-Multi,189803,0,2.html) |
| Dự báo tuổi thọ tăng nhanh trong nghiên cứu nhưng triển khai công nghiệp mới thành công hạn chế. | C, tóm tắt | [Tổng quan tại Adelaide](https://digital.library.adelaide.edu.au/items/e753ae38-fb63-4e7a-a9a2-03e1136d51ea) |

## Vật lý và phần cứng

- **Bốn giai đoạn hỏng:** giai đoạn 1 ở dải siêu âm, giai đoạn 2 khoảng 500–2.000 Hz, giai đoạn 3 thấy tần số lỗi và hài, giai đoạn 4 nền nhiễu tăng. Dải 500–2.000 Hz nhất quán giữa các nguồn, còn dải giai đoạn 1 và thời gian cảnh báo thì không ([Acoem](https://www.acoem.com/en/blog/do-you-know-the-4-stages-of-bearing-failure/), [UE Systems](https://www.uesystems.com/en-gb/article-reduce-unplanned-downtime-learn-the-warning-signs-of-bearing-failure/), mức C).
- **Quy tắc 2,56:** thường được dùng, theo đó lấy mẫu 4 kHz chỉ dùng tin cậy đến khoảng 1,56 kHz. Tôi thấy quy tắc này trong đoạn trích kết quả tìm kiếm nhưng chưa đối chiếu được với tài liệu gốc (mức D). Cần kiểm tra lại khi biết mã cảm biến.
- **MEMS rẻ không nhất thiết băng hẹp:** ADI liệt kê MEMS $10–30 với 3–20+ kHz, và ADXL1002 có 25 µg/√Hz, ±50 g ([ADI](https://www.analog.com/en/resources/analog-dialogue/articles/choosing-the-most-suitable-accelerometer-for-your-application-part-2.html), mức C, tài liệu của hãng bán).
- **Nhiều ổ cùng trục:** khi các ổ giống nhau, thường khó xác định ổ nào cần thay từ rung ([bằng sáng chế](https://patents.google.com/patent/US6053047)). Một cách thực tế là so công suất dải tần giữa nhiều cảm biến ([IJPHM](https://papers.phmsociety.org/index.php/ijphm/article/download/2152/1150)).

## Cộng đồng kỹ sư

**Tìm không thấy chuỗi thảo luận Reddit, Eng-Tips hay ReliabilityWeb nào cụ thể,** và bài Zhihu chính bị chặn truy cập, nên đây là phần yếu nhất của tra cứu. Những điều lặp lại trong blog kỹ thuật (mức D):

- Cảnh báo sai thường đến từ cảm biến và lắp đặt, không phải thuật toán. Chỉ đọc được đoạn trích; trang gốc không truy cập được khi kiểm tra lại ([CSDN](https://blog.csdn.net/weixin_33686714/article/details/159775098)).
- Đổi tốc độ và tải gây trôi đặc trưng. Phải gắn nhãn điều kiện để so đúng với đúng ([CSDN](https://bbs.csdn.net/weixin_32770423/article/details/100448996)).
- Đặt ngưỡng theo nền riêng từng máy, thu khoảng 1–2 tuần; gắn cảm biến gần vùng chịu tải, ưu tiên bắt vít hoặc keo thay vì nam châm; máy quan trọng đo mỗi giờ; băng 5 kHz cho đa số lỗi công nghiệp ([NCD](https://ncd.io/blog/predictive-maintenance-with-vibration-sensors-the-complete-starter-guide/), tài liệu hãng).
- Cần nhiều mẫu liên tiếp mới đổi trạng thái ([nghiên cứu cảm biến giá rẻ](https://pmc.ncbi.nlm.nih.gov/articles/PMC12609400/); bài này có số liệu nội bộ không nhất quán nên chỉ dùng phần ý tưởng).

## Đối chiếu với lỗi của ta

| Lỗi đo được | Nguyên nhân hợp lý | Bằng chứng từ ngoài |
|---|---|---|
| Ổ đối chứng IMS đúng 14%; 46% cửa sổ nửa đầu đời bị gọi là lỗi | Nền 30 bản ghi; một mô hình làm hai việc; không lọc trạng thái | ODiN học nhiều tháng; Augury tách hai loại bộ phát hiện |
| Điểm tăng dần về cuối đời | Băng 1 kHz chủ yếu thấy giai đoạn muộn | Bốn giai đoạn hỏng |
| Vòng cách 0,009 | Công thức sai, và vốn là điểm mù | Masteel |
| RUL dưới 12% | Đường HI nhảy bậc; dữ liệu ít | Triển khai công nghiệp hạn chế; thực tiễn dùng mức trạng thái |
| Lớp chưa biết 0,55–0,80 | Softmax luôn chọn một lớp | Đa nhãn, cực trị |
| Cổng học lại nhận 88% lô nhãn sai | Bộ kiểm tra không có lỗi thật | Nhãn chuyên gia, xử lý nhãn nhiễu |
| IMS không chỉ được ổ hỏng | Các ổ giống nhau, cùng trục | Bằng sáng chế, mảng cảm biến |

**Điều ta đã làm đúng và được xác nhận:** chia theo ổ bi, giữ RF làm chuẩn, tiên nghiệm rộng, HI tham chiếu đóng băng, chuẩn hóa theo từng máy, và không tin các số 99%.

## Giới hạn của tra cứu

- Bosch, Haier, CATL, Foxconn không công bố thuật toán; các suy luận về họ dựa trên tài liệu giới thiệu và số tự báo cáo.
- Chưa đọc được toàn văn Matania et al. (bị chặn) và bài CNC của TU Munich (bị chặn). Trang Augury KB trả về 404 nên các số 20% và 99% chỉ thấy ở đoạn trích.
- Không tìm được chuẩn công khai về số báo nhầm trên máy mỗi tháng.
- Hầu hết nguồn định lượng từ hãng là số tự công bố.
