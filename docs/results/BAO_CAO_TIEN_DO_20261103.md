# Báo cáo tiến độ AnchorSpec cho buổi 10h thứ Ba 03/11/2026

Tổng hợp đến tối 01/11/2026. **Toàn bộ chạy trên dữ liệu công khai qua giả lập cảm biến rẻ, chưa có dữ liệu DENSO. Minh chưa rà soát số liệu.** Các số ở mục đính chính và nhánh X1 tính lại được bằng `python anchorspec/x_recheck.py`.

## Thông điệp chính

1. **Phát hiện lệch nền theo từng máy dùng được cho lỗi vòng trong và ngoài,** nhưng còn bỏ sót lỗi bi, vòng cách và chưa đo được báo nhầm dài hạn.
2. **Chỉ cấy lỗi chưa đủ để nhận loại lỗi trên giàn mới.** Cùng cách cấy, các lần kiểm chứng có giao thức cho kết quả rất khác nhau: 0,384 (UORED), 0,752 (HUST), 0,775 (XJTU), 0,795 (IMS, nhưng đối chứng kém).
3. **Hướng hứa hẹn nhất là cấy lỗi cộng một sự kiện lỗi thật cho mỗi loại:** vòng trong và ngoài tăng từ 0,820 lên 0,916 (XJTU), từ 0,418 lên 0,718 (UORED). Đây mới là khám phá, chưa được xác nhận.
4. **Dự báo thời gian còn lại chưa dùng được.** Đề xuất thay bằng 4 mức trạng thái.
5. **Chưa có bằng chứng cho các lỗi quan trọng khác:** công thức vòng cách thất bại (0,009); dị vật và hết dầu chưa từng được đối chiếu với lỗi thật.

**Về trọng tâm:** theo trao đổi với DENSO, phần còn thiếu là Bài 2 (hỏng cái gì) và Bài 3 (bao giờ hỏng). Kết quả mạnh nhất của đội lại thuộc về phát hiện bất thường. Vì vậy nên trình bày phát hiện như cổng của hệ thống, còn câu trả lời cho Bài 2 là thông điệp 3. Cả đội cần chốt điểm này.

## Đính chính so với báo cáo trước

| Đã báo cáo | Thực tế sau khi rà lại | Hệ quả |
|---|---|---|
| X7 HUST: đúng khi trả lời 0,865, đạt; tổng 2/4 chỉ tiêu | 0,865 tính gộp theo cửa sổ. Theo công thức của E8 (theo máy, rồi macro theo lớp), số đúng là **0,727, không đạt** | **X7 chỉ đạt 1/4** |
| X1: học từ lỗi thật cùng ổ là kết quả rõ nhất (0,797 và 0,659) | Lỗi thật đưa vào học chỉ mang nhãn đúng của chính ổ đó và kiểm tra trong cùng lần chạy, nên mô hình gần như được cho sẵn đáp án. TN6 đã cho thấy kết quả đi theo nhãn được đưa vào: vòng cách k = 10 đạt 0,926 khi nhãn đúng, 0,012 khi nhãn sai | **Không dùng làm bằng chứng.** Bằng chứng hợp lệ là nhánh dùng lỗi từ ổ khác |
| X9 UORED 6 kHz: đúng khi trả lời giảm còn 0,689 | Số này gộp theo cửa sổ. Theo ổ là 0,875 trên 5/10 ổ có trả lời | 6 kHz không kém ở chỉ số này, nhưng vòng trong gần như không được trả lời (0,007) |
| E8: đúng khi trả lời 0,19 | Vẫn là số chính thức, nhưng rất nhiễu: chạy lại cùng cấu hình, chỉ đổi dòng ngẫu nhiên cấy lỗi, được 0,75. Cả hai lần chỉ trả lời 3–4% cửa sổ | Kết luận bền vững là **hệ thống gần như không trả lời**, chưa đủ mẫu để nói nó trả lời đúng hay sai |

## Kết quả có thể báo cáo

### A. Có giao thức ghi trước, kiểm tra một lần

| Thí nghiệm | Kết quả | Phải nói kèm |
|---|---|---|
| **TN2b, XJTU, 13 ổ** | Cấy lỗi thắng dữ liệu máy khác: vòng trong và ngoài 0,775 so với CWRU 0,448, hiệu +0,327 (CI +0,214 … +0,456). Lỗi thật từ ổ khác đạt 0,836 | Chỉ đo ở 10% cuối đời; vòng cách 0,009; cùng một giàn |
| **E8, UORED, 20 ổ hỏng tự nhiên** | Phát hiện: 10/10 ổ vòng trong và ngoài, 100% cửa sổ ở cả hai giai đoạn. Bi và vòng cách: 5/10 ổ ở giai đoạn đang phát triển, 7/10 ổ ở giai đoạn nặng (tính ổ có ≥ 50% cửa sổ vượt ngưỡng). Loại lỗi: **đạt 2/5 chỉ tiêu**; 3 lớp 0,384 so với CWRU 0,249, CI của hiệu vẫn chứa 0; trả lời 4%; AUROC lỗi lạ 0,56 | Báo nhầm 0,00 chỉ đo trên 4 s ngay sau 6 s nền, không nói được gì về dài hạn |
| **X7, HUST, 15 "máy"** | **Đạt 1/4:** bình thường bị gọi lỗi 0,067 (đạt); đúng khi trả lời 0,727; trả lời 0,427; AUROC lỗi lạ 0,55. Bộ phân loại không từ chối đạt 0,752; bỏ phiếu đúng 13/15 vòng trong, 10/15 vòng ngoài | Lỗi cắt dây 0,2 mm do người tạo; các "máy" có thể dùng chung ổ |
| **TN2, Paderborn** | **Nhánh chính trượt:** 0,463 so với CWRU 0,716 | Hiệu chỉnh riêng từng lớp làm kết quả xấu đi |
| **TN2c, IMS, 3 ổ hỏng** | 0,795 so với CWRU 0,093, nhưng ổ đối chứng chỉ đúng bình thường 14% | Mô hình gọi gần như mọi thứ cuối thí nghiệm là lỗi |
| **X8, cảm biến 6 kHz** | **Không đạt** vì báo nhầm vượt 0,10 (XJTU 0,113; HUST 0,571). Hiệu so với 1 kHz: UORED +0,330 (CI +0,052 … +0,630), HUST +0,156, XJTU +0,024 (CI −0,075 … +0,110) | Đo trên bộ phân loại thô, chưa qua ngưỡng từ chối; dùng lại dữ liệu đã thấy. Giữ 1 kHz |

### B. Khám phá, phải nói rõ chưa được xác nhận

**X1, học từ sự kiện trên ổ khác cùng giàn.** Ổ đang kiểm tra không có trong dữ liệu học. Macro vòng trong và ngoài, CI bootstrap theo ổ:

| Nhánh | XJTU (11 ổ) | UORED (10 ổ) | Bình thường đúng, XJTU / UORED |
|---|---:|---:|---:|
| Chỉ cấy lỗi | 0,820 | 0,418 | 0,82 / 0,93 |
| Chỉ lỗi thật, 1 sự kiện mỗi loại | 0,599 | 0,305 | 0,99 / 1,00 |
| Cấy + 5 cửa sổ của 1 sự kiện mỗi loại | 0,898 (+0,078; CI +0,014 … +0,133) | 0,653 (+0,235; CI +0,056 … +0,409) | 0,77 / 0,89 |
| **Cấy + cả sự kiện, 1 sự kiện mỗi loại** | **0,916** (+0,096; CI +0,029 … +0,146) | **0,718** (+0,300; CI +0,163 … +0,430) | 0,78 / 0,91 |
| Cấy + cả sự kiện, 4 sự kiện mỗi loại | 0,901 (+0,082; CI −0,004 … +0,141) | 0,721 (+0,304; CI +0,111 … +0,516) | 0,71 / 0,90 |
| Chỉ lỗi thật, 4 sự kiện mỗi loại | 0,747 | 0,475 | 0,92 / 1,00 |

Với cùng số sự kiện, cấy + thật hơn hẳn chỉ dùng lỗi thật (1 sự kiện: XJTU +0,316, CI +0,208 … +0,427; UORED +0,412, CI +0,232 … +0,602). Đây là luận điểm tốt nhất hiện có cho ý tưởng cấy lỗi: **không thay được lỗi thật, nhưng làm vài lỗi thật có giá trị hơn nhiều.**

Giới hạn:
- Không có giao thức ghi trước, nhiều nhánh được so mà không hiệu chỉnh so sánh bội.
- Cùng giàn, nên có thể chung đặc điểm đợt đo. Lỗi học và lỗi kiểm tra đều ở giai đoạn muộn.
- Mới xét trường hợp mọi loại lỗi đều đã xuất hiện trước đó.
- Tỉ lệ bình thường đúng giảm 2–5 điểm so với chỉ cấy khi có 1 sự kiện, và giảm 11 điểm ở XJTU khi có 4 sự kiện.
- **Bi và vòng cách vẫn không học được khi có cấy** (UORED, 1 sự kiện: cả hai 0,00; 4 sự kiện: bi 0,29, vòng cách 0,05). Không cấy thì được 0,73 và 0,63, tức lớp cấy đang lấn lớp thật.

**Các kết quả khám phá khác:**

| Chủ đề | Kết quả | Dùng để nói gì |
|---|---|---|
| Cảm biến rẻ (TN1, CWRU) | Độ đúng 99,72% còn 87,99% ở 3 HP, 49,58% ở 1 HP; mất mát chủ yếu do hạ băng thông | Cần biết băng thông thật trước các thông số khác |
| Học nhiều tải (TN1b) | 1 HP từ 0,496 lên 0,999 khi học 0 + 2 HP | Nên thu nền ở nhiều tải; CWRU dễ nên không suy rộng |
| Nền của chính máy (E3) | Cấy vào nền máy thắng thư viện lỗi giàn khác: XJTU 0,848 / 0,518; Paderborn 0,669 / 0,606; IMS 0,633 / 0,333 | Giữ "mỗi máy một mô hình" |
| Trôi theo thời gian (E5, Bosch 3 năm) | Nền cố định báo nhầm 0,596, có giai đoạn 0,88–0,93 | Đây là rủi ro lớn khi triển khai; đây là lỗi gia công, không phải lỗi ổ |
| Làm mới nền (X2) | Có xác nhận: báo nhầm 0,399 còn 0,098, nhưng phát hiện 18/29 còn 11/29. Tự động: báo nhầm 0,632 | Chỉ làm mới khi có người xác nhận; chưa có cấu hình tốt |
| Cổng thời gian thực (TN3b) | Không có cổng HI: 46% cửa sổ nửa đầu đời bị gọi là lỗi. Có cổng: đúng loại 0,90 ở 10% cuối đời trên XJTU | Phải tách phát hiện và phân loại |
| 4 mức trạng thái (E7) | Số lần tụt mức giảm 3–4 lần (FEMTO 12,1 còn 3,1; XJTU 2,3 còn 0,7; IMS 7,3 còn 1,7) | Giữ thiết kế có trễ |
| Khả thi (TN2b, TN6) | RF 50 cây 0,24–0,44 MB; khoảng 19 ms/cửa sổ trên laptop; khởi tạo 1,4–2,6 s phần tính; tốc độ sai tối đa 0,67% với 80 s dữ liệu | **Chưa đo trên Pi 5**; chỉ 4 phép đo tốc độ, tốc độ không đổi |

### C. Kết quả âm nên nói thẳng

- **Thời gian còn lại:** α-λ 3–13%, khoảng 80% của Wiener chỉ phủ 0–46%.
- **Vòng cách:** 0,009; công thức v2 đạt 0,232 nhưng làm giảm vòng trong và ngoài.
- **Lỗi lạ:** AUROC 0,55–0,56 trên vòng cách XJTU, UORED và HUST; chỉ tiêu là 0,85.
- **Cổng học lại tự động:** nhận 45/90 lô nhãn sai và 66/90 lô nhãn đúng, trượt cả hai. Đề xuất mọi lô đều cần hai người xác nhận.
- **Những thứ đã thử và không đổi quyết định:** micro kém rung (0,37–0,42 so với 0,49–0,51); CNN 1D thua RF trên XJTU, nhỉnh hơn trên UORED, mới một seed; MiniRocket 0,32 so với 0,775; nền riêng từng điều kiện chỉ giúp khi giảm tải (báo nhầm 0,19 còn 0,00, nhưng phát hiện 0,69 còn 0,56).

## Không nên trích

| Con số | Lý do |
|---|---|
| 0,865 (HUST) như một chỉ tiêu đạt | Sai công thức so với giao thức |
| 0,797, 0,659 (X1 cùng ổ); 0,80–0,96 (TN6) | Mô hình gần như được cho sẵn đáp án |
| 0,878 và 0,734 (X5, 6 kHz) đứng riêng | Không có báo nhầm, không so với 1 kHz; so đúng cách thì XJTU gần như không tăng |
| 0,824 (A0, Paderborn) | Chọn nhánh sau khi đã xem test |
| 1,00 khi trả lời trên XJTU | Không lặp lại trên giàn khác |
| 0,795 (IMS) đứng riêng | Đối chứng chỉ đúng 14% |
| 1,00 (TN1b) | CWRU dễ, cả hai tải đã xem |
| Thời gian báo trước theo giờ (kể cả 840 h của IMS) | Không có nhãn khởi phát, thử nghiệm tăng tốc |
| "HI 100%" không kèm lỗi bi, vòng cách và giới hạn báo nhầm | Gây hiểu là đã giải xong phát hiện |

## Thí nghiệm đáng thử, xếp theo giá trị cho quyết định

Chi phí là ước tính dựa trên các đợt Modal đã chạy. Đã dùng $2,15/$30. Mọi thí nghiệm mới cần ghi giao thức trước khi chạy.

### Làm được trước 10h thứ Ba, nếu đội muốn có số mới

| # | Thí nghiệm | Câu hỏi | Dữ liệu, chi phí | Kết quả sẽ quyết định gì |
|---|---|---|---|---|
| 1 | **Đường cong học theo sự kiện** | Cần bao nhiêu lỗi thật đã xác nhận? Xếp ngẫu nhiên các ổ như các lần hỏng nối tiếp trên một máy, học từ các lần trước, kiểm tra lần kế tiếp. So chỉ cấy, chỉ thật, cấy + thật; đo cả khi chưa đủ mọi loại lỗi | UORED, XJTU; < $1, < 30 phút | Trả lời trực tiếp nỗi đau "phải chờ máy hỏng". Nếu đường cong tăng sớm: đây là hình chính của buổi báo cáo. Nếu không: bỏ thông điệp 3 |
| 2 | **Đối chứng nhãn sai cho nhánh cùng ổ** | Nhánh cùng ổ có đang chỉ học thuộc nhãn được đưa vào không? | UORED, XJTU; < $0,5, < 10 phút | Khóa lại đính chính ở trên bằng số cùng thiết kế với X1 |

### Tuần 04–08/11, không cần dữ liệu DENSO

| # | Thí nghiệm | Câu hỏi | Dữ liệu, chi phí | Kết quả sẽ quyết định gì |
|---|---|---|---|---|
| 3 | **Khởi tạo khi máy đang ở giữa đời** | Máy nhà máy không phải ổ mới. Lấy nền ở 25, 50, 70% đời thì phát hiện và cấy lỗi còn dùng được không? | XJTU; FEMTO, IMS phần HI đã có đặc trưng; < $1 | Quy trình khởi tạo máy, và rủi ro lớn nhất của phát hiện: E8 có 3 ổ không phát hiện được, đúng là 3 ổ có RMS nền cao nhất |
| 4 | **Autoencoder so với HI** | Cổng của đội có hơn cách DENSO đang dùng không? | UORED, XJTU, HUST; < $1 | Nếu không hơn: dùng điểm của DENSO làm cổng, không phát triển tiếp HI |
| 5 | **Cân bằng lớp cấy và lớp thật** | Có giữ được bi, vòng cách đã học từ lỗi thật mà không mất vòng trong, ngoài không? | UORED, XJTU; < $1 | Cách học từ lỗi xác nhận trong vòng học lại |
| 6 | **Xác nhận độc lập lần 3 trên bộ chưa mở** | Cấu hình tốt nhất sau mục 1 và 5 có giữ được không? | Ứng viên: [KAIST](https://data.mendeley.com/datasets/ztmf3m7h5x), [UNSW](https://data.mendeley.com/datasets/h4df4mgrfb), [Ottawa đổi tốc độ](https://data.mendeley.com/datasets/v43hmbwxpm), [dữ liệu nhà máy MDPI](https://www2.mdpi.com/2306-5729/8/7/115). Phải kiểm tra giấy phép và cách tạo lỗi trước; < $2 | Chỉ kết quả này mới cho phép nói thông điệp 3 là đã xác nhận |
| 7 | **Đo trên Pi 5 thật** | Độ trễ và bộ nhớ có đạt < 100 ms/cửa sổ không? | Cần thiết bị; không tốn Modal | Chốt khả năng chạy tại biên |

### Cần dữ liệu DENSO

| # | Thí nghiệm | Câu hỏi | Kết quả sẽ quyết định gì |
|---|---|---|---|
| 8 | **Phát lại dữ liệu bình thường nhiều ngày** | Mỗi máy có bao nhiêu cảnh báo sai mỗi tháng? | Số còn thiếu quan trọng nhất của phát hiện |
| 9 | **Máy thử ổ bi của DENSO, so với AutoML của họ** | Trên chính các lớp lỗi của họ, đủ 3 trục, đúng bao nhiêu sự kiện? | Kiểm chứng thật duy nhất cho cuộc thi |
| 10 | **Công thức dị vật và hết dầu** | Lỗi cấy có giống lỗi thật không? | Giữ hay bỏ hai lớp này. Lượt tìm nhanh chưa thấy bộ công khai nào có đúng hai lỗi này, nên hiện phụ thuộc dữ liệu DENSO |

### Không đáng làm tiếp

Chỉnh tiên nghiệm ở 1 kHz (X8: không tăng); micro; thêm cấu hình CNN hoặc MiniRocket; thư viện lỗi từ giàn khác; làm mới nền tự động; dự báo thời gian còn lại theo giờ; chỉnh công thức vòng cách trên 2 ổ XJTU đã mở; chỉnh ngưỡng trên các bộ đã xem rồi báo như xác nhận.

## Cần DENSO hỗ trợ

1. **Mã cảm biến, băng thông thật, dải đo, cách gá, số cảm biến mỗi máy.** Quyết định có thấy được lỗi sớm không, và 6 kHz có đáng xét không.
2. **Dữ liệu bình thường dạng sóng thô, kèm chương trình, tốc độ, tải, trong nhiều ngày.** Cần cho mục 8.
3. **Dữ liệu và nhật ký lỗi của máy thử ổ bi:** ngày, bộ phận, ảnh, người xác nhận. Cần cho mục 9, 10.
4. **Bao nhiêu cảnh báo sai là chấp nhận được, và cần báo trước bao lâu?** Quyết định chỉ tiêu báo nhầm và có bỏ hẳn dự báo thời gian còn lại không.

Danh sách đầy đủ ở [kế hoạch v1.5](../plans/KE_HOACH_ANCHORSPEC_v1.5.md).

## Tài liệu và tái lập

- Chi tiết: [TN1–TN3](KET_QUA_SO_BO_TN1_TN2_TN3_20261031.md), [TN2b, TN3b](KET_QUA_TN2B_TN3B_REALTIME_20261101.md), [các việc CPU](KET_QUA_CAC_VIEC_CPU_20261101.md), [E1–E8](KET_QUA_E1_E8_20261101.md), [X1–X9](KET_QUA_MODAL_X1_X9_20261101.md).
- Giao thức: `anchorspec/PROTOCOL_*.md`. Kết quả thô: `anchorspec/results/`.
- In lại số liệu: `conda activate anchorspec && cd anchorspec && python x_report.py && python x_recheck.py`.
- Một phần dữ liệu thô đã xóa khỏi máy để lấy dung lượng; xem cuối [báo cáo X1–X9](KET_QUA_MODAL_X1_X9_20261101.md). Dữ liệu thô không đưa lên repo.
