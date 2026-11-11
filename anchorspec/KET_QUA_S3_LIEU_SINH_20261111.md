# AnchorSpec S3: cần bao nhiêu dữ liệu lỗi, sinh bao nhiêu mẫu là hợp lý

> **Cập nhật 12/11, sáng:** kết quả mới nhất ở `KET_QUA_DEM_12112026.md`. Flow không qua kiểm chứng trên Paderborn; cấy lỗi vật lý cộng vài sự cố thật (ExtraTrees, hai tầng) qua kiểm chứng trên Paderborn và HUST.


**Ngày:** 11/11/2026. **Người chạy:** Hoàng Minh Quyền (ML), đội AIOverflow. **Nhánh:** `quyen-s3-curve`, chưa commit.
**Phạm vi:** dữ liệu công khai (XJTU-SY, UORED-VAFCLS) qua cảm biến giả lập 1 kHz, CPU. Mọi kết quả là **thăm dò** trên các bộ đã dùng nhiều lần, không phải xác nhận độc lập, không phải dữ liệu DENSO.

> **Cập nhật 12/11: đọc mục 11 trước.** Kiểm tra lại với RF 500 cây và cách chấm chỉ chọn loại lỗi (đúng cách DENSO dùng sau cảnh báo) cho thấy:
> - Trên XJTU, lợi ích của Flow ở các mục 2–6 chủ yếu đến từ RF quá nhỏ và từ việc dồn trọng số. Với RF ổn định, Flow không thêm gì.
> - Trên UORED, Flow vẫn còn tăng 5–8 điểm ở 3/5 bộ sự cố.

## Tóm tắt

| Câu hỏi | Trả lời ngắn |
|---|---|
| Có kết quả "ít dữ liệu lỗi hơn X lần" để đưa lên slide không? | **Không.** Khi dữ liệu ít, Flow không hơn chỉ mẫu thật một cách đáng tin |
| Khi sự cố lệch giữa các loại, nên sinh bao nhiêu mẫu mỗi loại? | Không có liều chung. Ứng viên ổn định nhất là **trộn 25% Flow, khoảng 30 mẫu mỗi loại**: không thua chỉ mẫu thật ở 6/6 bộ, trung bình +3,2 điểm. Đây là nhận xét sau khi xem kết quả, cần kiểm chứng lại |
| Có tỉ lệ với dữ liệu khỏe (kiểu 2 : 1 : 1 : 1) không? | Không cần. Pipeline đã cân bằng trọng số 1 : 1 : 1 : 1 giữa lớp khỏe và từng lớp lỗi; dồn thêm trọng số cho lớp lỗi cho kết quả trái dấu |
| Có chọn được liều lúc lắp đặt từ vài sự cố của máy không? | **Không**, với 1–2 sự cố mỗi loại. Nên dùng liều cố định đã khóa từ benchmark |
| Kết quả có ổn định không? | Chưa. Dao động do seed lên tới 6–22 điểm, lớn hơn chênh lệch giữa các liều (1–5 điểm) |
| Thứ gì quyết định độ chính xác? | **Số sự cố thật đã xác nhận:** mỗi loại có 1, 2, 4 sự cố cho 41,5%, 55,7%, 67,0% (UORED) |

## 1. Bối cảnh và kiểm tra dữ liệu

**Góp ý của mentor (11/11):** "Phương pháp bình thường cần bao nhiêu dữ liệu để đạt độ chính xác X; phương pháp của em cần bao nhiêu dữ liệu để đạt độ chính xác X."

Cấu hình S3 gốc chỉ đo ở một mức dữ liệu: 5 đoạn khỏe của ổ đích, 120 đoạn lỗi thật (12 ổ nguồn × 10 đoạn) và thêm 120 mẫu Flow. Kết quả báo cáo là macro recall cuối đời 77,22%.

**Kiểm tra trước khi chạy:**
- **Dữ liệu XJTU:** tải lại bằng `u_download.py` (390 CSV, kiểm tra CRC) rồi chạy `u_natural.py prepare`. Cache tạo ra khớp bản của Trường: 169 mảng, sai lệch lớn nhất 7×10⁻¹¹.
- **Mã nguồn:** giống bản của Trường khi bỏ qua ký tự xuống dòng.
- **Tái lập S3 từ đầu trên máy này** (dùng thư mục `data/s_generation`, `data/s3_generation` bạn gửi):
  - Dùng lại mẫu sinh đã lưu, huấn luyện lại RF: dự đoán trùng 39/39 lượt.
  - Huấn luyện lại bộ sinh với anchor và hạt giống gốc: dự đoán trùng 39/39 lượt, residual lệch tối đa 7,5×10⁻⁶, macro recall đúng **77,22%**.
- **Test:** 128/140 đạt. 12 test lỗi không liên quan phương pháp:
  - Hash của `cheap_sensor.py` và `features.py` được ghi theo kiểu xuống dòng Windows.
  - Thiếu `data/xjtu_u/joint`.

## 2. Đường cong theo số cửa sổ lỗi (S3 curve, XJTU)

**Thiết lập** (`s3_curve.py`, handoff `HANDOFF_S3_CURVE_20261111.md`):
- Giữ cấu hình S3, chỉ đổi k = số cửa sổ lỗi thật mỗi ổ nguồn (2, 3, 5, 10).
- 13 ổ × 3 seed × 4 mức = 156 lượt.
- Chỉ số: giai đoạn khỏe + cuối đời, 4 lớp.

| Cửa sổ/ổ | Tổng | Chỉ mẫu thật P / R / Acc | + Flow P / R / Acc | Chênh recall (CI 95% theo ổ) |
|---:|---:|---|---|---|
| 2 | 24 | 67,0 / 67,4 / 85,0 | 85,2 / 70,4 / 86,2 | +3,0 [−3,8; +9,8] |
| 3 | 36 | 67,2 / 66,9 / 84,4 | 81,0 / 68,1 / 84,1 | +1,2 [−6,3; +8,6] |
| 5 | 60 | 93,7 / 75,7 / 89,4 | 94,0 / 75,8 / 89,4 | +0,1 [−1,3; +1,4] |
| 10 | 120 | 86,9 / 76,2 / 89,9 | 95,7 / 81,9 / 92,0 | +5,7 [−2,8; +14,2] |

**Đối chiếu k = 10 với `results/priorities/Method_metrics.csv`:**
- Chỉ mẫu thật: khớp tuyệt đối (86,89 / 76,25 / 89,91).
- Flow: lệch dưới 1 điểm (95,65 / 81,94 / 91,97 so với 95,70 / 82,92 / 92,48). Nguyên nhân là thứ tự anchor và hạt giống lấy mẫu.

**Đọc đúng:**
- Precision tăng mạnh ở k = 2–3 chủ yếu do cách tính. Chỉ mẫu thật không dự đoán vòng cách lần nào, nên precision lớp này bị tính 0.
- Ở k = 3, recall vòng trong giảm từ 68,9% xuống 50,0%.
- Con số "ít hơn 1,9 lần" mà script tự in ra là sản phẩm của phép nội suy: chỉ mẫu thật đã đạt 75,7% recall ở k = 5, chỉ kém mốc 0,5 điểm.
- Theo mục 7 của handoff, đây là **trường hợp 3**: không đưa tuyên bố tiết kiệm dữ liệu.

**Kiểm tra độ nhạy, chỉ đổi hạt giống lấy mẫu của Flow ở k = 10:**
- P / R / Acc còn 91,23 / 78,75 / 90,60, tức giảm 4,4 điểm precision và 3,2 điểm recall.
- Chỉ 5/39 lượt cho dự đoán khác, đã đủ dịch chuyển trung bình.

## 3. Ghép Flow với căn chỉnh theo nền khỏe (S3-Delta, XJTU)

**Thiết lập** (`PROTOCOL_S3_DELTA.md`, `s3_delta.py`):
- Bốn nhánh: raw và delta (trừ trung bình 5 đoạn khỏe đầu của từng ổ), mỗi biểu diễn có hai biến thể là chỉ mẫu thật hoặc thêm Flow.
- Flow lấy trung bình 5 hạt giống lấy mẫu.

| Nhánh | Macro recall cuối đời | Dao động theo hạt giống | Vòng cách | Gán lỗi trên khỏe |
|---|---:|---|---:|---:|
| Chỉ mẫu thật, raw | 68,33 | | 11,67 | 0 |
| Flow, raw | 74,06 | 67,64–78,38 | 34,33 | 0 |
| Chỉ mẫu thật, delta | **77,73** | | **45,00** | 3,08 |
| Flow + delta | 75,86 | 68,70–78,47 | 42,67 | 3,90 |

**Kết luận:**
- Ghép hai cách **không cộng dồn:** Flow + delta kém riêng delta 1,87 điểm, CI [−4,12; 0,00].
- Con số 77,22% của S3 nằm ở phía trên của dải dao động theo hạt giống.
- Nhánh delta tái tạo đúng 77,73% của đợt T, nên phần cài đặt là đúng.

## 4. Cần bao nhiêu sự cố, có và không có Flow (S3-UORED)

**Thiết lập** (`PROTOCOL_S3_UORED_EVENTS.md`, `s3_uored.py`):
- UORED 20 ổ, 4 lớp lỗi, trạng thái nặng.
- Số ổ nguồn mỗi loại: 1, 2, 4. Tổng 180 lượt.

| Sự cố/loại | Chỉ mẫu thật | + Flow | Chênh (CI 95%) |
|---:|---:|---:|---|
| 1 | 35,6 | 26,0 | −9,6 [−18,9; −0,8] |
| 2 | 47,9 | 51,5 | +3,6 [−2,6; +10,2] |
| 4 | 63,0 | 66,2 | +3,2 [−0,5; +8,2] |

Tiêu chí khai báo trước (Flow hơn ít nhất 5 điểm, CI dương, ở mức 1 hoặc 2 sự cố): **không đạt.**

## 5. Kiểm tra cách đo: thiếu đối chứng bản sao

Thêm mẫu sinh làm tăng tổng trọng số của lớp lỗi so với lớp khỏe. Mẫu Flow lại gần như trùng anchor (tương quan khoảng 0,994). Vì vậy phép so "Flow − chỉ mẫu thật" gộp hai thứ: hiệu ứng dồn trọng số và giá trị mới của mẫu sinh.

Giao thức ở mục 3 và 4 thiếu nhánh bản sao. Nhánh này được thêm **sau khi đã xem kết quả** (`dupcheck.py`), nên chỉ là phân tích bổ sung. Mã được kiểm tra: dự đoán trùng 39/39 lượt với đường cong; nhánh bản sao tái tạo đúng 72,64% của đợt S.

| Dữ liệu | Thật | Bản sao | Flow | Bản sao − thật | Flow − bản sao |
|---|---:|---:|---:|---|---|
| XJTU, 3 lớp | 68,33 | 72,64 | 74,06 | +4,31 [−3,84; +12,45] | +1,42 [−0,07; +2,90] |
| UORED, 1 sự cố/loại | 35,6 | 21,7 | 26,0 | −13,9 [−29,6; +0,4] | +4,4 [−5,4; +12,9] |
| UORED, 2 sự cố/loại | 47,9 | 53,3 | 51,5 | +5,4 [−0,6; +12,5] | −1,8 [−6,7; +2,8] |
| UORED, 4 sự cố/loại | 63,0 | 62,7 | 66,2 | −0,3 [−3,8; +3,0] | +3,5 [+0,3; +6,7] |

**Hệ quả:**
- Trên XJTU, phần lớn "lợi ích" của Flow là hiệu ứng trọng số. Phần đóng góp riêng của mẫu Flow chỉ khoảng 1,4 điểm.
- Flow kém khi chỉ có 1 sự cố/loại là do cách dồn trọng số, không phải do bộ sinh: riêng bản sao đã giảm 13,9 điểm.
- RF rất nhạy với tổng trọng số của lớp lỗi.

## 6. Sinh bao nhiêu khi sự cố bị lệch (S3-Dose)

### Thiết lập

Giao thức `PROTOCOL_S3_DOSE.md`, mã `s3_dose.py`, ghi hash trước khi chạy.

- **UORED, 15 ổ** (vòng trong, vòng ngoài, vòng cách), 5 bộ sự cố (trong-cách-ngoài): **5-2-1** (ví dụ của bạn), 1-2-5, 2-2-2, 1-1-1, 4-4-4. "Vòng giữa" được hiểu là vòng cách. Khi ổ đích cùng lớp, "5" thực tế còn 4.
- **XJTU, bộ sự cố tự nhiên:** 3 trong, 8 ngoài, 2 cách.
- Tổng **264 lượt**, không lỗi. Flow lấy trung bình 3 hạt giống lấy mẫu.

**Các nhánh:**
- `real`: chỉ mẫu thật.
- `dup_add_a`: bản sao, dồn thêm a trọng số cho lớp lỗi.
- `flow_add_a_N`: N mẫu Flow mỗi loại, thêm a trọng số.
- `flow_mix_b_N`: N mẫu Flow mỗi loại, chiếm b phần trọng số, **tổng trọng số lớp không đổi**.
- `flow_prop`: 10 mẫu mỗi sự cố, như cách S3 gốc.
- `uw_real`, `uw_topup`: không dùng trọng số; nhánh thứ hai sinh bù cho mỗi lớp lỗi bằng số mẫu của lớp nhiều nhất.
- `selector`: chọn liều lúc lắp đặt, chỉ dùng sự cố của máy (giữ lại từng sự cố một để kiểm tra).

Chỉ số: macro recall 3 lớp lỗi ở trạng thái nặng hoặc cuối đời.

### Kết luận theo quy tắc khai báo trước

| Quy tắc | Kết quả |
|---|---|
| Có liều sinh chung | **Không.** Không nhánh nào vừa ≥ real ở mọi bộ, vừa sát nhánh tốt nhất trong vòng 2 điểm |
| Mẫu sinh có giá trị riêng, so ở cùng khối lượng | **Đạt theo quy tắc, nhưng không nhất quán.** Có so sánh CI dương ở 5/6 bộ, nhưng mỗi bộ là một nhánh khác; khoảng 90 phép so sánh chưa hiệu chỉnh |
| Chọn được liều lúc lắp đặt | **Không.** Trung bình −0,29 điểm so với real; ở bộ 1-1-1 không chọn được |

### Chỉ mẫu thật theo bộ sự cố

| Bộ | 1-1-1 | 1-2-5 | 5-2-1 | 2-2-2 | 4-4-4 | XJTU |
|---|---:|---:|---:|---:|---:|---:|
| Macro | 41,5 | 42,9 | 52,6 | 55,7 | 67,0 | 68,3 |
| Dao động theo seed | 35,1–45,3 | 39,6–45,3 | 40,0–62,5 | 52,6–60,0 | 63,9–69,5 | 63,3–76,1 |

### Độ nhất quán của từng nhánh (chênh so với real, điểm)

| Nhánh | 5-2-1 | 1-2-5 | 2-2-2 | 1-1-1 | 4-4-4 | XJTU | TB | Số bộ ≥ real |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Trộn 25%, 30 mẫu/loại** | +1,8 | +1,9 | +3,7 | +6,9 | +1,6 | +3,5 | **+3,2** | **6/6** |
| 10 mẫu/sự cố, thêm 25% (cách S3) | −2,5 | +0,2 | +1,1 | +4,7 | +1,7 | +4,0 | +1,5 | 5/6 |
| Trộn 25%, 90 mẫu/loại | −0,5 | −1,3 | +5,2 | +0,4 | +4,9 | −2,7 | +1,0 | 3/6 |
| Trộn 50%, 30 mẫu/loại | +1,4 | +0,2 | +1,2 | −4,6 | +1,1 | +2,0 | +0,2 | 5/6 |
| Thêm 25%, 30 mẫu/loại | −4,1 | −2,3 | −1,6 | −0,3 | +0,9 | +4,4 | −0,5 | 2/6 |
| Bản sao, thêm 25% | −3,4 | −0,8 | +1,3 | +0,6 | −4,2 | +4,3 | −0,4 | 3/6 |
| Bù cho bằng số mẫu, không trọng số | −6,5 | +1,4 | −0,6 | −2,3 | +0,6 | +10,7 | +0,5 | 3/6 |
| Bộ chọn lúc lắp đặt | −2,3 | −0,5 | −2,9 | 0,0 | +0,7 | +3,3 | −0,3 | 3/6 |

### Ví dụ 5-2-1 (thực tế trung bình 4,7 trong / 2 cách / 1 ngoài)

| Nhánh | Macro | Vòng trong | Vòng ngoài (1 sự cố) | Vòng cách |
|---|---:|---:|---:|---:|
| Chỉ mẫu thật | 52,6 | 89,8 | 31,6 | 36,5 |
| Trộn 25%, 30 mẫu/loại | 54,5 | 93,6 | 31,5 | 38,4 |
| Thêm 100%, 90 mẫu/loại | 56,6 | 95,2 | 42,2 | 32,5 |
| Bù cho bằng số mẫu, không trọng số | 46,1 | 95,0 | 21,5 | 21,8 |
| Bộ chọn lúc lắp đặt | 50,3 | 93,1 | 26,9 | 31,0 |

Lớp chỉ có 1 sự cố (vòng ngoài) gần như không được cứu bởi nhánh ổn định nhất. Nhánh "thêm 100%, 90 mẫu/loại" nâng vòng ngoài lên 42,2%, nhưng chính nhánh đó lại kém ở bộ 1-1-1 và 1-2-5.

## 7. Trả lời các câu hỏi

### 7.1. Cùng dữ liệu thì phương pháp nào tốt hơn?

- Trên XJTU đủ dữ liệu, Flow cao hơn chỉ mẫu thật khoảng 5,7 điểm (lấy trung bình hạt giống). Nhưng **khoảng 4,3 điểm trong đó chỉ là hiệu ứng dồn trọng số**, như nhánh bản sao cho thấy; phần riêng của mẫu Flow khoảng 1,4 điểm.
- Khi dữ liệu ít (k = 2–3 trên XJTU, 1 sự cố/loại trên UORED), không có lợi thế đáng tin.

### 7.2. Với bao nhiêu dữ liệu thì đạt độ chính xác cần thiết?

- Thứ quyết định là **số sự cố thật đã xác nhận**, không phải số mẫu sinh. Trên UORED 3 lớp: 1 sự cố/loại cho 41,5%, 2 cho 55,7%, 4 cho 67,0%. Đi từ 1 lên 4 tăng khoảng 25 điểm, trong khi các liều sinh chỉ đổi từ −10 đến +7 điểm.
- Ở các mức thử, chưa phương án nào đạt 80%. Đó cũng là chỉ tiêu "macro ≥ 80%" ghi trong cổng nghiên cứu của đợt T.

### 7.3. Sự cố lệch (ví dụ 5 trong, 2 cách, 1 ngoài): sinh bao nhiêu cho mỗi loại?

- Không có số đúng cho mọi trường hợp.
- **Ứng viên mặc định:** trộn mẫu Flow chiếm 25% trọng số của mỗi lớp lỗi, khoảng 30 mẫu mỗi loại, **cùng số mẫu cho mọi loại** bất kể số sự cố. Với loại có 1 sự cố (10 đoạn), tức khoảng 3 mẫu sinh cho mỗi đoạn thật; loại có 5 sự cố thì khoảng 0,6.
- Không dùng 90 mẫu mỗi loại hay 100% trọng số làm mặc định: kết quả trái dấu giữa các bộ.
- Mẫu sinh **không thay được sự cố thật** cho loại chỉ có 1 sự cố. Muốn cải thiện loại đó, cần thu thêm sự cố của chính nó.

### 7.4. Có tỉ lệ với dữ liệu khỏe không?

- Không cần đặt tỉ lệ số mẫu kiểu 2 : 1 : 1 : 1. Pipeline cân bằng bằng **trọng số**: lớp khỏe và mỗi lớp lỗi có cùng tổng trọng số, không phụ thuộc số mẫu hay số sự cố.
- Dồn thêm trọng số cho lớp lỗi không ổn định (bản sao: −4,2 đến +4,3 điểm), và cái giá về báo nhầm không đo được ở đây.
- Bù cho bằng số mẫu mà không dùng trọng số cũng không ổn định (−6,5 đến +10,7 điểm).
- **Đề xuất:** giữ trọng số 1 : 1 : 1 : 1; mẫu sinh chỉ chiếm một tỉ lệ cố định bên trong mỗi lớp lỗi.

### 7.5. Có phải đến khi lắp đặt mới xác định được số mẫu sinh?

- Đã thử chọn liều chỉ từ sự cố của chính máy: kết quả không hơn chỉ mẫu thật (−0,29 điểm).
  - **1 sự cố mỗi loại:** không chọn được, vì không còn sự cố để kiểm tra.
  - **2 sự cố:** mẫu kiểm tra quá ít nên lựa chọn nhiễu.
- **Quy trình đề xuất khi lắp đặt:**
  1. Dùng liều cố định đã khóa từ benchmark (trộn 25%, 30 mẫu mỗi loại).
  2. Chạy song song với kỹ thuật viên, ghi từng sự cố được xác nhận.
  3. Chỉ chọn lại liều khi máy có khoảng 4–5 sự cố mỗi loại, bằng giữ lại từng sự cố để kiểm tra.

### 7.6. Có thật sự ổn định không?

- **Chưa.** Chỉ đổi seed (cách chọn sự cố và huấn luyện), kết quả đã dao động 6–22 điểm, ví dụ bộ 5-2-1 từ 40,0 đến 62,5%. Chỉ đổi hạt giống lấy mẫu của Flow, kết quả dao động khoảng 1–10 điểm.
- Các chênh lệch 1–5 điểm giữa các liều nằm trong biên độ đó.

## 8. Câu có thể đưa lên slide

> "Lợi ích lớn nhất đến từ việc có thêm sự cố được kỹ sư xác nhận: mỗi loại từ 1 lên 4 sự cố tăng khoảng 25 điểm. Dữ liệu sinh, khi trộn 25% và giữ cân bằng giữa các lớp, không làm kém đi ở cả 6 kịch bản thử và tăng trung bình khoảng 3 điểm; cấu hình này đang được khóa để kiểm chứng trên dữ liệu mới."

**Không nên nói:**
- "Cần ít dữ liệu lỗi hơn X lần", kể cả con số "1,9 lần" do script tự in.
- "Flow thắng chắc chắn".
- Con số 77,22% đứng một mình (nó là một lần chạy ở phía trên của dải dao động).
- "Tỉ lệ sinh tối ưu là ..." như một quy tắc chung.

## 9. Giới hạn

- Hai bộ dữ liệu đã được dùng nhiều lần. Không có hiệu chỉnh so sánh bội. Nhánh ổn định nhất được nhận ra sau khi xem kết quả.
- **Đoạn khỏe dùng để kiểm tra nằm cùng tệp với nền**, nên tỉ lệ gán lỗi trên khỏe gần như luôn 0%. Vì vậy không đo được cái giá báo nhầm của việc dồn trọng số.
- Mỗi lớp chỉ có 5 ổ (UORED), riêng vòng cách XJTU chỉ có 2. Nhiều đoạn của cùng một ổ không phải nhiều sự cố độc lập.
- Cảm biến giả lập 1 kHz, ±8 g; chưa phải cảm biến DENSO.
- Đối chứng bản sao cho mục 3 và 4 được thêm sau khi xem kết quả.

## 10. Việc tiếp theo

1. Khóa cấu hình "trộn 25%, 30 mẫu mỗi loại", rồi kiểm tra trên bộ dữ liệu chưa dùng hoặc dữ liệu DENSO, với giao thức ghi trước.
2. Có đoạn khỏe kiểm tra ở phiên hoặc ngày khác, để đo cái giá báo nhầm.
3. Ưu tiên thu thêm sự cố thật có xác nhận, nhất là loại hiếm như vòng cách.

## Tệp kết quả

| Thí nghiệm | Giao thức | Mã | Kết quả |
|---|---|---|---|
| Đường cong S3 | `../HANDOFF_S3_CURVE_20261111.md` | `s3_curve.py` | `results/s3_curve/` (`curve.md`, `curve.csv`, `curve.png`, `validation.md`, `seedcheck.py`) |
| S3-Delta | `PROTOCOL_S3_DELTA.md` | `s3_delta.py` | `results/s3_delta/` |
| S3-UORED | `PROTOCOL_S3_UORED_EVENTS.md` | `s3_uored.py` | `results/s3_uored/` (`summary.md`, `audit.md`, `dupcheck.py`) |
| S3-Dose | `PROTOCOL_S3_DOSE.md` | `s3_dose.py` | `results/s3_dose/` (`summary.md`, `interpretation.md`, `dose.png`) |

Các thư mục `s3_delta`, `s3_uored`, `s3_dose` có `prerun.sha256` ghi trước khi chạy. Thư mục `s3_curve` không có, vì script đó được chuyển giao sẵn. Mọi thư mục đều lưu toàn bộ dự đoán từng lượt trong `tasks/`.

## 11. Kiểm tra lại (12/11): nguồn ngẫu nhiên và cách chấm

Đây là phân tích **sau khi đã xem kết quả**, không có giao thức ghi trước. Script và dữ liệu thô ở `results/s3_recheck/`.

### 11.1. Hai điều thay đổi cách đọc

**Một là nguồn ngẫu nhiên.** Trên XJTU, danh sách ổ nguồn cố định, chỉ hạt giống RF thay đổi, vậy mà nhánh chỉ mẫu thật vẫn dao động 13–15 điểm. Lý do là RF 50 cây quá nhỏ.

| XJTU, chỉ mẫu thật, 5 seed | RF 50 cây | RF 500 cây |
|---|---:|---:|
| Chỉ chọn loại lỗi: trung bình (độ rộng theo seed) | 72,8 (15,0) | **78,1 (4,4)** |
| Có lựa chọn khỏe: trung bình (độ rộng theo seed) | 68,1 (13,9) | 63,1 (4,4) |

Trên UORED, seed còn đổi cả **ổ nào được chọn làm sự cố**. Vì vậy dao động không giảm khi tăng số cây: bộ 5-2-1 vẫn rộng khoảng 30 điểm. Đây là phần ngẫu nhiên vốn có, do máy tình cờ có những sự cố nào.

**Hai là cách chấm.** Cách chấm "có lựa chọn khỏe" (selective) dùng ở mục 2–6 trộn hai việc: phân biệt khỏe/lỗi và phân biệt loại lỗi. Dồn trọng số về lớp lỗi làm mô hình bớt gọi lỗi là khỏe, nên điểm tăng mà chẩn đoán loại lỗi không tốt hơn. Trên XJTU với RF 500 cây, riêng bản sao đã tăng +15,6 điểm ở cách chấm này. Cách chấm **chỉ chọn loại lỗi** (conditional) đúng với cách DENSO sẽ dùng sau cảnh báo, và loại bỏ được hiệu ứng đó.

### 11.2. Kết quả với RF 500 cây, chỉ chọn loại lỗi

| Bộ | Chỉ mẫu thật | Bản sao +25% | Trộn 25% Flow, 30/loại | Trộn − thật (CI 95%) | Thêm Flow − bản sao (CI 95%) | Sự cố chẩn đoán đúng (thật / trộn) |
|---|---:|---:|---:|---|---|---|
| XJTU tự nhiên | 78,1 | 80,7 | 77,9 | −0,2 [−1,3; +0,9] | −1,2 [−2,3; −0,2] | |
| UORED 5-2-1 | 56,6 | 55,4 | 57,5 | +0,9 [−5,3; +6,6] | +0,5 [−4,9; +5,8] | 26 / 26 trên 45 |
| UORED 1-2-5 | 44,1 | 43,4 | 49,1 | **+5,0 [+0,2; +10,3]** | +0,8 [−3,0; +3,9] | 19 / 24 |
| UORED 2-2-2 | 55,2 | 58,4 | 60,0 | +4,8 [0,0; +9,1] | −1,4 [−7,0; +3,7] | 24 / 26 |
| UORED 1-1-1 | 52,6 | 53,2 | 52,7 | +0,1 [−13,5; +11,8] | +1,2 [−1,8; +4,4] | 23 / 22 |
| UORED 4-4-4 | 67,8 | 67,3 | 75,4 | **+7,6 [+1,5; +15,3]** | **+5,0 [+0,8; +10,4]** | 30 / 34 |

"Sự cố chẩn đoán đúng" là số lượt (ổ đích × seed) mà hơn một nửa cửa sổ lỗi nặng được gán đúng loại. XJTU không có số này vì script kiểm tra lại không tính.

### 11.3. Đọc lại

- **XJTU: Flow không thêm gì.** Các mức tăng ở mục 2–6 chủ yếu do RF 50 cây không ổn định và do cách chấm có lựa chọn khỏe. Chỉ tăng số cây đã đưa nhánh chỉ mẫu thật lên 78,1%, ngang con số 77,22% của S3 có Flow. Riêng dồn trọng số (bản sao) tăng +2,6 điểm, CI [+0,2; +4,9].
- **UORED: Flow còn giúp ở 3/5 bộ** (+4,8 đến +7,6 điểm), gần 0 ở hai bộ còn lại. Phần tăng này không do dồn trọng số, vì nhánh bản sao gần bằng chỉ mẫu thật. Ở bộ 4-4-4, số sự cố đúng tăng từ 30 lên 34 trên 45.
- **Tính trên cả 6 bộ:** chênh "trộn 25%, 30 mẫu/loại" so với chỉ mẫu thật là +0,9, +5,0, +4,8, +0,1, +7,6, −0,2. Trung bình +3,0, thấp nhất −0,2. Đây vẫn là phân tích hậu nghiệm, nhiều phép so sánh, cần kiểm chứng.
- **Dao động do sự cố nào có mặt** (đến 30 điểm ở 5-2-1) lớn hơn mọi hiệu ứng phương pháp. Thứ quyết định vẫn là số sự cố thật.

### 11.4. Thay đổi đề xuất cho pipeline (không phụ thuộc Flow)

1. Dùng RF 500 cây thay cho 50 cây. Dao động theo hạt giống giảm khoảng 3 lần trên XJTU; mô hình lớn hơn nhưng vẫn nhẹ (cần đo lại thời gian và kích thước).
2. Báo cáo chẩn đoán bằng cách chấm chỉ chọn loại lỗi sau cảnh báo. Việc phân biệt khỏe/lỗi do bộ phát hiện phía trước đảm nhận, và đo riêng.

### 11.5. Phép kiểm chứng còn đáng chạy

**Khóa cấu hình** (RF 500 cây, chỉ chọn loại lỗi, trộn 25% Flow 30 mẫu/loại, đối chứng chỉ mẫu thật và bản sao) rồi chạy **một lần** trên **Paderborn hỏng thật**: 5 ổ vòng ngoài (KA04, KA15, KA16, KA22, KA30), 6 ổ vòng trong (KI04, KI14, KI16, KI17, KI18, KI21), nền khỏe từ K001–K006. Dữ liệu đã có sẵn ở `data/paderborn/cache`. Flow chưa từng chạy trên bộ này, và cấu hình được chọn chỉ từ XJTU và UORED.

- **Đạt** nếu: ở ít nhất một mức 1, 2 hoặc 4 sự cố/loại, trộn − thật ≥ +3 điểm với CI không chứa 0; không mức nào thấp hơn thật quá 1 điểm; và trộn cao hơn bản sao.
- **Đạt:** được nói "Flow cải thiện X điểm trên dữ liệu không dùng để chọn cấu hình".
- **Không đạt:** bỏ dữ liệu sinh khỏi luận điểm chính.
