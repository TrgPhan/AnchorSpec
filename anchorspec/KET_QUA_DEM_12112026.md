# Kết quả đêm 11–12/11/2026: Flow không qua kiểm chứng, cấy lỗi vật lý thì qua

**Người thực hiện:** Hoàng Minh Quyền (ML) và Claude. **Nhánh:** `research/overnight-20261112` (chưa push).
**Phạm vi:** dữ liệu công khai qua cảm biến giả lập 1 kHz, CPU. **Chưa phải dữ liệu DENSO.**

> **Cập nhật 12/11, 10:00: phương pháp đã chốt là hai tầng + cấy lỗi** (mục 11). Kiến trúc này qua cả Paderborn (8 seed, PB-HIER) và HUST.
> Công thức Flow gốc của Trường được kiểm tra lại đúng cấu hình 50 cây: không có giá trị riêng (mục 12).

## Kết luận

1. **Flow matching (S3) không có giá trị được kiểm chứng.** Trên Paderborn hỏng thật, với cấu hình đã khóa, Flow so với chỉ mẫu thật là +1,9 / +0,4 / −0,7 điểm ở 1 / 2 / 4 sự cố mỗi loại, không mức nào có CI dương. Các mức tăng trước đây (77,22%) chủ yếu đến từ RF 50 cây không ổn định, từ cách chấm có lựa chọn "khỏe", và từ hiệu ứng dồn trọng số.
2. **Cấy lỗi vật lý vào nền khỏe của chính máy** (ý tưởng gốc của AnchorSpec), **cộng với vài sự cố thật và ExtraTrees, qua hai phép kiểm chứng** trên dữ liệu không dùng để chọn cấu hình:
   - **Paderborn** (vòng trong và ngoài): +11 đến +17 điểm (3 seed); +8 đến +19 điểm (5 seed mới).
   - **HUST** (vòng trong, ngoài, bi): +8 đến +10 điểm (3 seed); +5 đến +11 điểm (5 seed mới).

   Phần tăng đến từ mẫu cấy: cùng bộ phân loại mà không cấy thì gần bằng chỉ mẫu thật.
3. **Cấy phẳng làm sập lớp không có mẫu cấy** (vòng cách). **Thiết kế hai tầng** sửa được điều này: trên bộ phát triển, vòng cách tăng trung bình +10 điểm thay vì sập; trên HUST, lớp bi giữ nguyên.
4. **Không qua:** hồi quy logistic (dù rất mạnh trên bộ phát triển), cảm biến băng thông rộng (0/6 bộ), thư viện hỏng nhân tạo.
5. **Câu trả lời cho mentor (cần bao nhiêu dữ liệu lỗi)**, chỉ cho vòng trong và ngoài:
   - **Paderborn:** riêng cấy lỗi, **không cần sự cố thật nào**, đạt 76,9%, cao hơn chỉ mẫu thật có 4 sự cố mỗi loại (62,4%).
   - **HUST:** hai tầng với 1 sự cố mỗi loại (55,2%) ngang chỉ mẫu thật với 3 sự cố (56,5%).
   - Đây là so sánh giữa các mức của những lần chạy đã khóa, nhưng bản thân phép so này không phải tiêu chí khai báo trước.

## 1. Sửa cách đo trước khi kết luận

Ba thay đổi áp dụng cho mọi phép thử tối nay. Cả ba đều được rút ra từ kiểm tra lại ngày 12/11 (`KET_QUA_S3_LIEU_SINH_20261111.md`, mục 11).

| Vấn đề cũ | Sửa | Lý do |
|---|---|---|
| RF 50 cây: chỉ đổi seed đã lệch tới 15 điểm | RF 500 cây làm mốc | Trên XJTU, độ lệch theo seed còn 4,4 điểm |
| Cách chấm "có lựa chọn khỏe" | **Chỉ chọn loại lỗi** sau cảnh báo | Đúng cách DENSO dùng: bộ phát hiện phía trước đã báo bất thường. Loại bỏ hiệu ứng dồn trọng số giữa lớp khỏe và lớp lỗi |
| Thiếu đối chứng | Đối chứng bản sao, và cùng bộ phân loại khi không có mẫu sinh | Tách giá trị thật của mẫu sinh khỏi thay đổi trọng số hay bộ phân loại |

**Quy trình:**
- Phát triển trên XJTU và UORED. Khóa cấu hình theo quy tắc ghi trước, rồi chạy **một lần** trên Paderborn hoặc HUST.
- Mỗi thí nghiệm có giao thức `PROTOCOL_*.md` và `prerun.sha256` ghi trước khi chạy.
- CI 95% bootstrap theo ổ, phân tầng theo lớp.

## 2. PB-Flow: Flow trên Paderborn hỏng thật

Giao thức `PROTOCOL_PB_FLOW.md`. 6 ổ vòng trong, 5 ổ vòng ngoài hỏng thật; nền khỏe K001–K006; 3 seed.

| Sự cố/loại | Chỉ mẫu thật | Bản sao | Flow | Flow − thật (CI 95%) |
|---:|---:|---:|---:|---|
| 1 | 59,5 | 56,4 | 61,5 | +1,9 [−2,3; +8,7] |
| 2 | 48,7 | 47,8 | 49,1 | +0,4 [0,0; +0,9] |
| 4 | 62,4 | 60,6 | 61,6 | −0,7 [−5,1; +2,4] |

**Không đạt.** Chỉ mẫu thật trên Paderborn cũng gần mức đoán mò (đoán mò là 50% cho 2 lớp). Từ ổ này sang ổ khác, cảm biến 1 kHz với bộ đặc trưng hiện tại không đủ để phân biệt loại lỗi.

## 3. M-Dev: tìm phương pháp trên bộ phát triển

Giao thức `PROTOCOL_M_DEV.md`. 264 lượt: UORED 5 bộ sự cố và XJTU. Mốc là RF 500 cây.

| Nhánh | Chênh 3 lớp (TB / thấp nhất) | Chênh vòng trong + ngoài (TB / thấp nhất) |
|---|---|---|
| Hồi quy logistic | +12,4 / +3,2 (**khóa** theo quy tắc 3 lớp) | +10,1 / +1,6 |
| ExtraTrees 500 | +5,4 / −0,2 | +7,5 / +0,7 |
| Flow trộn 25% | +3,1 / −0,2 | +2,3 / +0,2 |
| Cấy trộn 50% | +0,8 / −16,9 | +17,2 / −2,8 |
| ExtraTrees + cấy trộn 25% | +1,0 / −10,9 | **+15,7 / +6,1** (khóa cho PB-INJ) |
| Chỉ cấy, không sự cố thật | −27,7 | −23,1 |

Cấy lỗi tăng mạnh vòng trong và ngoài, nhưng vòng cách sụp (UORED 16–50% xuống 5–14%, XJTU 45% xuống 0%).

## 4. Kiểm chứng trên Paderborn

| Thí nghiệm | Nhánh khóa | Kết quả |
|---|---|---|
| PB-M | Hồi quy logistic | **Không đạt:** −8,6 / +3,4 / +13,9, mức 1 sự cố thua |
| BW-LIB, băng thông | Chỉ sự cố thật, 1/2/6 kHz | **Không đạt:** 0/6 bộ có 6 kHz hơn 1 kHz từ +5 điểm với CI dương |
| BW-LIB, thư viện nhân tạo | 12 ổ hỏng nhân tạo | **Không đạt:** chỉ thư viện 46,5% so với 1 sự cố thật 59,5% |
| BW-LIB, chỉ cấy | A0, không sự cố thật | 76,9%, hơn 1 sự cố thật +17,4 [+1,8; +34,7] |
| **PB-INJ** | **ExtraTrees + cấy trộn 25%** | **Đạt** (bảng dưới) |

**PB-INJ** (giao thức `PROTOCOL_PB_INJ.md`, ghi trước khi xem bất kỳ con số cấy lỗi nào trên Paderborn):

| Sự cố/loại | Chỉ mẫu thật | ExtraTrees | ExtraTrees + cấy | Cấy − thật (CI 95%) | Cấy − ExtraTrees (CI 95%) | Lượt đúng (thật / cấy, trên 33) |
|---:|---:|---:|---:|---|---|---|
| 1 | 59,5 | 51,7 | **73,1** | +13,5 [0,0; +32,6] | +21,3 [+3,3; +42,1] | 21 / 25 |
| 2 | 48,7 | 52,4 | **59,9** | **+11,2 [+2,5; +20,9]** | +7,5 [−0,2; +17,6] | 16 / 20 |
| 4 | 62,4 | 74,3 | **79,3** | **+17,0 [+0,7; +37,5]** | +5,0 [−0,4; +12,2] | 20 / 27 |

**5 seed mới** (101, 202, 303, 404, 505), kiểm tra độ nhạy, không chọn lại gì:

| Sự cố/loại | Chỉ mẫu thật | ExtraTrees | ExtraTrees + cấy | Cấy − thật (CI 95%) |
|---:|---:|---:|---:|---|
| 1 | 35,9 | 38,3 | 55,0 | **+19,2 [+5,2; +32,3]** |
| 2 | 43,9 | 43,0 | 52,2 | **+8,3 [+0,6; +17,6]** |
| 4 | 60,1 | 66,7 | 76,5 | **+16,4 [+3,0; +33,0]** |

Mức tuyệt đối dao động mạnh theo seed (sự cố nào được chọn, nền khỏe nào), nhưng **chênh do cấy lỗi luôn dương**. Riêng ExtraTrees thì gần bằng chỉ mẫu thật.

## 5. Hai tầng: giữ lớp không có mẫu cấy (HIER)

Giao thức `PROTOCOL_HIER.md`.
- **Tầng 1:** ExtraTrees chỉ dùng sự cố thật, phân biệt khỏe, nhóm vòng (trong + ngoài), và lớp khác (vòng cách, bi).
- **Tầng 2:** ExtraTrees phân biệt vòng trong và ngoài, có cấy trộn 25%.

**Bước 1, phát triển** (macro 3 lớp):

| Bộ | Chỉ mẫu thật | Cấy phẳng | **Hai tầng** | Vòng cách: thật / hai tầng | Hai tầng − thật (CI 95%) |
|---|---:|---:|---:|---|---|
| UORED 5-2-1 | 56,6 | 56,6 | **70,4** | 41,8 / 53,0 | +13,8 [+4,4; +24,4] |
| UORED 1-2-5 | 44,1 | 54,3 | **57,5** | 16,5 / 30,2 | +13,5 [+0,9; +25,3] |
| UORED 2-2-2 | 55,2 | 58,8 | **61,2** | 28,4 / 40,7 | +6,0 [−5,1; +17,7] |
| UORED 1-1-1 | 52,6 | 54,5 | **58,8** | 40,4 / 51,2 | +6,2 [−3,3; +15,3] |
| UORED 4-4-4 | 67,8 | 69,1 | **77,8** | 49,8 / 59,6 | +9,9 [−6,2; +27,4] |
| XJTU | 77,6 | 66,7 | **80,9** | 45,0 / 48,3 | +3,3 [−1,1; +7,8] |

Trung bình +8,8 điểm, thấp nhất +3,3, vòng cách trung bình +10,2: **đủ điều kiện khóa.**

**Bước 2, HUST** (5 loại ổ là 5 "máy"; mỗi máy có nền khỏe riêng; lớp bi không có mẫu cấy; 14 ổ đích):

| Sự cố/loại | Chỉ mẫu thật | Cấy phẳng | **Hai tầng** | Hai tầng không cấy | Bi: thật / hai tầng | Hai tầng − thật (CI 95%) |
|---:|---:|---:|---:|---:|---|---|
| 1 | 46,4 | 56,4 | **55,2** | 47,2 | 86,4 / 85,8 | **+8,8 [+1,9; +16,5]** |
| 2 | 47,6 | 59,7 | **57,2** | 50,3 | 85,6 / 89,2 | **+9,6 [+3,3; +16,3]** |
| 3 | 56,5 | 69,0 | **64,1** | 60,2 | 86,9 / 89,2 | **+7,6 [+1,6; +15,2]** |

**Đạt cả ba tiêu chí.** Với 5 seed mới: +4,8 [−0,3; +10,1], +5,5 [+0,3; +11,0], +11,4 [+3,4; +19,7].

## 6. Cần bao nhiêu sự cố thật (câu hỏi của mentor)

| Bộ | Cách | 0 sự cố | 1 | 2 | 3–4 |
|---|---|---:|---:|---:|---:|
| Paderborn, trong + ngoài (3 seed) | Chỉ mẫu thật | | 59,5 | 48,7 | 62,4 (4) |
| | Cấy lỗi (RF) | **76,9** | | | |
| | ExtraTrees + cấy | | **73,1** | 59,9 | **79,3** (4) |
| HUST, 3 lớp (3 seed) | Chỉ mẫu thật | | 46,4 | 47,6 | 56,5 (3) |
| | Hai tầng | | **55,2** | 57,2 | **64,1** (3) |
| UORED, 3 lớp (phát triển) | Chỉ mẫu thật | | 52,6 | 55,2 | 67,8 (4) |
| | Hai tầng | | 58,8 | 61,2 | **77,8** (4) |

**Câu có thể dùng:** "Với cùng số sự cố, cấy lỗi vật lý vào nền khỏe của máy tăng 8–17 điểm. Trên HUST, 1 sự cố mỗi loại cộng cấy lỗi đạt mức mà chỉ dùng sự cố thật cần 3 sự cố. Trên Paderborn, chỉ cấy lỗi đã vượt mức của 4 sự cố thật."

**Phải nói kèm:**
- Chỉ áp dụng cho **vòng trong và ngoài**, vì chỉ có công thức cấy cho hai loại này.
- Chưa đúng trên UORED khi không có sự cố thật nào: cấy không kèm sự cố thật kém hẳn.
- Mức tuyệt đối dao động mạnh theo seed.

## 7. Pipeline đề xuất (v2)

```text
Cờ bất thường từ hệ thống DENSO
  -> kiểm tra tín hiệu (SignalContract)
  -> 45 đặc trưng mỗi trục (1 kHz)
  -> Tầng 1, ExtraTrees 500 cây, chỉ sự cố thật:
       nhóm vòng (trong/ngoài)  |  vòng cách  |  lớp khác đã có sự cố
  -> Tầng 2, ExtraTrees 500 cây: vòng trong hay vòng ngoài
       học từ sự cố thật + 150 mẫu cấy A0 mỗi loại vào nền khỏe của chính máy, chiếm 25% trọng số
  -> trung bình nhân quả 5 cửa sổ -> giả thuyết loại lỗi -> kỹ sư xác nhận -> thêm sự cố vào thư viện
```

**Chi phí đo trên laptop** (CPU một luồng, UORED 4-4-4):
- Khởi tạo một máy: cấy lỗi 0,84 s, huấn luyện hai tầng 0,55 s.
- Suy luận một cửa sổ: trung vị 46 ms, p95 49 ms, gồm tính đặc trưng.
- Kích thước mô hình: 3,5 MiB.

**Chưa đo trên Pi 5.** Nếu chậm, có thể giảm số cây.

## 8. Giới hạn

- **Không hoàn toàn độc lập:** cấy A0 đã được xem trên Paderborn ở TN2; HUST đã dùng ở X7 và V với cách làm khác. Đây là lần nhìn thứ 3–4 vào Paderborn trong đêm (PB-Flow, PB-M, BW-LIB, PB-INJ), và mỗi lần đều khóa nhánh trước.
- **Đơn vị độc lập ít:** Paderborn 11 ổ; HUST 14 ổ, các mức tải của cùng ổ là cùng mẫu hỏng. CI rộng.
- **Nền khỏe:** trên Paderborn, nền khỏe là ổ khỏe khác trên cùng giàn (không có nền của chính ổ hỏng). HUST có nền của cùng loại ổ.
- **Phạm vi lớp:** cấy chỉ cho vòng trong và ngoài. Vòng cách, bi, thiếu bôi trơn, dị vật vẫn cần sự cố thật. Thiết kế hai tầng mới được kiểm chứng giữ được lớp không cấy trên HUST (bi); vòng cách chỉ có ở bộ phát triển.
- **Cách chấm:** chỉ chọn loại lỗi, giả định bộ phát hiện phía trước đã đúng; không đo báo nhầm.
- **Cảm biến giả lập:** 1 kHz, ±8 g. Cảm biến thật của DENSO chưa biết. Đơn vị gia tốc của Paderborn và HUST là giả định.

## 9. Không nên nói

- "Flow / học sâu giúp", hay con số 77,22%.
- "Cấy lỗi chẩn đoán được mọi loại lỗi" hay "không cần dữ liệu lỗi". Chỉ đúng cho vòng trong và ngoài, và không đúng ở mọi bộ.
- Các con số của nhánh `uw` hay của lần thử đầu Flow trên Paderborn ở cách chấm có lựa chọn khỏe.

## 10. Việc tiếp theo

1. Khóa pipeline v2 (hai tầng, ExtraTrees, cấy 25%), chạy trên dữ liệu DENSO theo giao thức ghi trước.
2. Có đoạn khỏe kiểm tra ở phiên khác để đo báo nhầm.
3. Đo trên Pi 5; thử giảm số cây.
4. Công thức cấy cho vòng cách hoặc thiếu bôi trơn: chỉ đáng làm khi có sự cố thật để kiểm chứng.

## 11. Chốt phương pháp: hai tầng trên Paderborn (PB-HIER, 12/11)

Giao thức `PROTOCOL_PB_HIER.md` (hash ghi trước khi chạy), mã `pb_hier.py`. Kiến trúc `hier` giữ nguyên như khi khóa; 11 ổ đích, 8 seed (11, 29, 47, 101, 202, 303, 404, 505), 264 lượt. Nhánh cấy phẳng và nhánh chỉ mẫu thật trùng dự đoán với PB-INJ ở lượt kiểm tra mã.

| Sự cố/loại | Chỉ mẫu thật | Cấy phẳng | **Hai tầng** | Hai tầng không cấy | Hai tầng − thật (CI 95%) | Hai tầng − phẳng |
|---:|---:|---:|---:|---:|---|---|
| 1 | 44,8 | 61,8 | **65,8** | 45,2 | **+21,0 [+6,2; +36,2]** | +4,0 [+0,9; +7,5] |
| 2 | 45,7 | 55,1 | **61,4** | 46,7 | **+15,7 [+4,4; +28,9]** | +6,3 [+1,2; +11,8] |
| 4 | 61,0 | 77,6 | **76,3** | 70,1 | **+15,3 [+1,4; +33,0]** | −1,3 [−3,2; +0,2] |

**Đạt cả hai tiêu chí ở cả ba mức.** Tách riêng 3 seed cũ và 5 seed mới đều dương ở mọi mức. Paderborn chỉ có vòng trong/ngoài nên đây là kiểm tra nhất quán (dự kiến gần cấy phẳng), không phải phát hiện mới.

**Gộp 8 seed cho HUST** (gộp hai lần chạy đã khóa, `final_slides_20261112.py`): chỉ mẫu thật 55,9 / 57,5 / 56,0; hai tầng 62,2 / 64,6 / 65,9; chênh +6,3 [+1,8; +11,2], +7,0 [+2,4; +12,2], +10,0 [+3,7; +17,6].

**Chỉ cấy lỗi, 0 sự cố thật, Paderborn 8 seed** (`pb_inj_only8.py`, cùng code với BW-LIB; tái tạo đúng 76,9% trên 3 seed cũ): 73,3%, cao hơn chỉ mẫu thật với 4 sự cố (61,0%).

**Phương pháp chốt:** hai tầng + cấy A0 (mục 7). Slide nộp: `results/final/AnchorSpec_Ket_qua_20261112.pptx`.

## 12. Kiểm tra lại công thức Flow gốc của Trường (12/11, hậu nghiệm)

Công thức: 120 cửa sổ lỗi thật (12 ổ × 10) sinh 1:1, mỗi mẫu sinh nặng 0,25 mẫu thật, cộng thêm vào trọng số thật (lớp lỗi thành 1,25 lần lớp khỏe). Đối chứng: bản sao cùng số lượng và trọng số. Mã `truong_recipe.py`, `truong_in_ours.py`.

- XJTU, 50 cây (tái tạo đúng bảng S3 gốc): Flow − bản sao +1,8 [−0,6; +5,0]. Với 500 cây: −3,9 [−8,3; −0,6].
- Paderborn, 50 và 500 cây, sinh 1:1 và 2:1: không mức nào hơn chỉ mẫu thật có CI dương.
- Gắn vào kiến trúc cấy lỗi: Flow − bản sao = 0,0 / −0,8 / −0,1.
- Mẫu Flow cách neo 1,42 (đặc trưng chuẩn hóa), trong khi hai cửa sổ cùng ổ cách 5,26 và hai ổ khác nhau cách 9,13: mẫu sinh gần như bản sao.

## Tệp

| Thí nghiệm | Giao thức | Mã | Kết quả |
|---|---|---|---|
| Flow trên Paderborn | `PROTOCOL_PB_FLOW.md` | `pb_flow.py`, `pb_common.py` | `results/pb_flow/` |
| Phát triển | `PROTOCOL_M_DEV.md` | `m_dev.py` | `results/m_dev/` |
| Hồi quy logistic trên Paderborn | `PROTOCOL_M_DEV.md` (PB-M) | `pb_m.py` | `results/pb_m/` |
| Băng thông, thư viện nhân tạo | `PROTOCOL_PB_BW_LIB.md` | `pb_bw_lib.py` | `results/pb_bw_lib/` |
| Cấy lỗi trên Paderborn | `PROTOCOL_PB_INJ.md` | `pb_inj.py`, `pb_inj_seeds.py` | `results/pb_inj/`, `results/pb_inj_seeds/` |
| Hai tầng, HUST | `PROTOCOL_HIER.md` | `m_hier.py`, `hier_hust_seeds.py` | `results/hier_dev/`, `results/hier_hust/`, `results/hier_hust_seeds/` |
| Hai tầng, Paderborn (chốt) | `PROTOCOL_PB_HIER.md` | `pb_hier.py`, `pb_inj_only8.py` | `results/pb_hier/`, `results/pb_inj_only8/` |
| Công thức Flow của Trường | (hậu nghiệm) | `truong_recipe.py`, `truong_in_ours.py` | `results/truong_recipe/`, `results/truong_in_ours/` |
| Slide nộp 12/11 | | `final_slides_20261112.py` | `results/final/` |

Dữ liệu mới thêm vào `data/` (không có trong Git):
- `hust_v`, `hust_v6204`: chép từ bản worktree của Trường.
- `s_generation`, `s2_generation`, `s3_generation`, `y_cache`: thư mục bạn gửi, đã chuyển vào `data/`.
