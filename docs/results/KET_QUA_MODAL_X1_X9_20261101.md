# Kết quả chạy trên Modal: X1–X9 — 01/11/2026

Chạy trên Modal, tổng chi phí **$2,15** theo `modal billing report` tại thời điểm viết, ngân sách $30. Kết quả thô: `anchorspec/results/x/*.json`; in lại bằng `python x_report.py`. Chưa có người thứ hai rà soát.

**Đính chính sau khi rà lại:** X7 chỉ đạt 1/4 chỉ tiêu, nhánh X1 cùng ổ không dùng được làm bằng chứng, số X9 tính lại theo ổ. Số liệu tính lại bằng `python x_recheck.py`; tổng hợp ở [báo cáo tiến độ](BAO_CAO_TIEN_DO_20261103.md).

## Kết luận

| Câu hỏi | Kết quả | Quyết định |
|---|---|---|
| Lỗi thật từ sự kiện khác có giúp nhận loại lỗi? (X1, E9) | **Có với vòng trong và ngoài, khi đi kèm cấy lỗi.** Nhánh cùng ổ không dùng được làm bằng chứng | Giữ hướng cấy + vài sự kiện xác nhận; cần xác nhận độc lập |
| Làm mới nền có giảm báo nhầm? (X2, E10) | Có, nhưng đổi bằng mất phát hiện | Chỉ làm mới có xác nhận; chưa đạt chỉ tiêu trên Bosch |
| Nền theo đúng điều kiện vận hành? (X3) | Chỉ giúp ở trường hợp giảm tải | Giữ theo dõi trạng thái máy; chưa cần một nền cho mỗi điều kiện |
| Micro có thay được rung? (X4) | Không | Không đưa micro vào phương án chính |
| Cảm biến 6 kHz, tiên nghiệm rộng? (X5, X8, X9) | **Không đạt giao thức X8**, có tín hiệu tốt | Giữ 1 kHz; 6 kHz là nhánh thử trên phần cứng |
| CNN có đáng thay RF? (X6) | Không rõ ràng | Giữ RF, chưa cần GPU |
| Thiết kế đã freeze trên bộ mới HUST? (X7) | Đạt 1/4 chỉ tiêu theo đúng công thức E8 | Độ đúng, tỉ lệ trả lời và lỗi lạ đều chưa đạt |

## X1 (E9): học từ lỗi thật

Macro vòng trong và ngoài theo ổ, 3 seed; XJTU 11 ổ, UORED 10 ổ. CI bootstrap theo ổ, phân tầng theo lớp, là hiệu so với chỉ cấy. **Khám phá, không có giao thức ghi trước, không hiệu chỉnh so sánh bội.**

| Nhánh | XJTU | UORED |
|---|---:|---:|
| Chỉ cấy | 0,820 | 0,418 |
| Chỉ lỗi thật, 1 sự kiện mỗi loại | 0,599 | 0,305 |
| Cấy + 5 cửa sổ, 1 sự kiện mỗi loại | 0,898 (+0,078; +0,014 … +0,133) | 0,653 (+0,235; +0,056 … +0,409) |
| Cấy + cả sự kiện, 1 sự kiện mỗi loại | 0,916 (+0,096; +0,029 … +0,146) | 0,718 (+0,300; +0,163 … +0,430) |
| Cấy + cả sự kiện, 4 sự kiện mỗi loại | 0,901 (+0,082; −0,004 … +0,141) | 0,721 (+0,304; +0,111 … +0,516) |
| Chỉ lỗi thật, 4 sự kiện mỗi loại | 0,747 | 0,475 |

- Ổ đang kiểm tra không nằm trong dữ liệu học, nên đây là phép thử hợp lệ cho câu hỏi "lỗi thật ở lần hỏng trước có giúp lần hỏng sau không". Vẫn là cùng giàn.
- Cấy + thật hơn chỉ dùng thật với cùng số sự kiện: 1 sự kiện XJTU +0,316 (+0,208 … +0,427), UORED +0,412 (+0,232 … +0,602).
- Bình thường đúng giảm nhẹ khi thêm lỗi thật vào cấy: XJTU 0,82 còn 0,78; UORED 0,93 còn 0,91.
- Bi và vòng cách vẫn không học được khi có cấy: UORED 1 sự kiện đều 0,00; 4 sự kiện bi 0,29, vòng cách 0,05. Không cấy được 0,73 và 0,63.

**Nhánh cùng ổ không dùng làm bằng chứng.** Ở nhánh này (macro 4 lớp 0,659 trên UORED, 3 lớp 0,797 trên XJTU với k = 10), lỗi thật đưa vào học chỉ mang nhãn đúng của chính ổ và lấy từ cùng lần chạy với đoạn kiểm tra, nên mô hình gần như được cho sẵn đáp án. TN6 cho thấy kết quả đi theo nhãn được đưa vào: vòng cách k = 10 đạt 0,926 khi nhãn đúng, 0,012 khi nhãn sai. Macro nhiều lớp cũng bất lợi cho nhánh chỉ cấy, vì nó không thể học bi và vòng cách.

## X2 (E10): làm mới nền trên Bosch CNC

| Quy tắc | Báo nhầm | Phát hiện | AUC | Mẫu tốt/xấu |
|---|---|---|---|---|
| Cố định theo nguyên công | 0,596 | 0,583 | 0,611 | 763/12 |
| Cố định, gộp | 0,399 | 0,621 | 0,719 | 1452/29 |
| Làm mới có xác nhận, OP40 | 0,400 | 0,667 | 0,585 | 763/12 |
| Làm mới có xác nhận, gộp 100 | 0,149 | 0,517 | 0,713 | 1452/29 |
| Làm mới có xác nhận, gộp 300 | 0,098 | 0,379 | 0,794 | 1452/29 |
| Làm mới tự động, gộp 300 | 0,632 | 0,862 | 0,755 | 1452/29 |

Làm mới có xác nhận giảm báo nhầm từ 0,399 xuống 0,098, nhưng phát hiện giảm từ 0,621 xuống 0,379. AUC tăng ít, nên phần lớn là đổi ngưỡng. Làm mới tự động báo nhầm nhiều. Số mẫu xấu nhỏ, và Bosch là lỗi quá trình gia công, không phải lỗi ổ. Không so trực tiếp với E5: X2 đi theo thứ tự thời gian và chỉ tính tệp sau khi đủ nền, nên còn 12 và 29 tệp xấu so với 62 tệp ở E5, cách lập ngưỡng cũng khác.

## X3: nền theo điều kiện vận hành (Paderborn)

| Điều kiện | Báo nhầm: nền gốc / đúng điều kiện | Phát hiện: nền gốc / đúng điều kiện |
|---|---|---|
| N15_M07_F10 | 0,01 / 0,01 | 0,83 / 0,83 |
| N09_M07_F10 | 0,02 / 0,03 | 0,77 / 0,76 |
| N15_M01_F10 | 0,03 / 0,00 | 0,83 / 0,80 |
| N15_M07_F04 | 0,19 / 0,00 | 0,69 / 0,56 |

Ngưỡng lấy từ chính cửa sổ nền. Chỉ giảm lực hướng kính (F04) làm báo nhầm tăng rõ; đổi nền đúng điều kiện loại được báo nhầm nhưng phát hiện giảm.

## X4: micro và rung (UORED)

Macro 4 loại lỗi ở giai đoạn 2: rung 1 kHz 0,49, rung 6 kHz 0,51, micro 1 kHz 0,37, micro 6 kHz 0,42.

## X5, X8, X9: cảm biến 6 kHz và tiên nghiệm rộng

X5 chỉ so hai tiên nghiệm ở 6 kHz: XJTU 0,749 → 0,878, UORED 0,437 → 0,734. X5 không đo báo nhầm, nên X8 được ghi [giao thức](../../anchorspec/PROTOCOL_X8.md) trước khi chạy.

**X8, RF thô, 3 seed (macro / báo nhầm):**

| Nhánh | XJTU | UORED | HUST |
|---|---|---|---|
| `1k_cu` | 0,824 / 0,221 | 0,389 / 0,074 | 0,704 / 0,552 |
| `1k_rong` | 0,804 / 0,103 | 0,335 / 0,021 | 0,708 / 0,384 |
| `6k_cu` | 0,801 / 0,159 | 0,514 / 0,014 | 0,599 / 0,317 |
| `6k_rong` | 0,848 / 0,113 | 0,719 / 0,043 | 0,860 / 0,571 |

Hiệu `6k_rong - 1k_cu`: XJTU +0,024 (CI −0,075…+0,110), UORED +0,330 (CI +0,052…+0,630), HUST +0,156.

**Đối chiếu chỉ tiêu:** (1) đạt, (2) đạt, (3) **không đạt**: báo nhầm XJTU 0,113 và HUST 0,571 vượt 0,10. Theo giao thức: **giữ cấu hình 1 kHz**. Cả `1k_cu` cũng không đạt chỉ tiêu báo nhầm này khi dùng RF thô.

**X9, khám phá qua phễu đã freeze, chỉ vòng trong và ngoài, không lật kết quả X8.** Đúng khi trả lời tính theo ổ như E8:

| Bộ, nhánh | Đúng khi trả lời | Tỉ lệ trả lời | Số ổ có trả lời | Báo nhầm |
|---|---:|---:|---:|---:|
| XJTU `1k_cu` | 0,999 | 0,524 | 11/11 | 0,051 |
| XJTU `6k_rong` | 1,000 | 0,518 | 10/11 | 0,000 |
| UORED `1k_cu` | 0,750 | 0,033 | 4/10 | 0,000 |
| UORED `6k_rong` | 0,875 | 0,321 | 5/10 | 0,000 |
| HUST `1k_cu` | 0,727 | 0,427 | 25/30 | 0,067 |
| HUST `6k_rong` | 0,981 | 0,651 | 26/30 | 0,121 |

6 kHz trả lời nhiều hơn trên UORED và HUST, độ đúng không kém, nhưng UORED gần như không trả lời vòng trong (0,007) và HUST báo nhầm 0,121. X8, X9 dùng lại dữ liệu đã thấy, **chưa phải xác nhận độc lập**. UORED `1k_cu` đạt 0,750 ở đây nhưng E8 đạt 0,19 dù cùng cấu hình, chỉ khác dòng ngẫu nhiên cấy lỗi: khi chỉ trả lời 3–4% cửa sổ, chỉ số này rất nhiễu.

## X6: CNN 1D (T4, 1 seed)

| Nhánh | Đúng | Bình thường đúng |
|---|---|---|
| XJTU, cấy | ngoài 0,55; trong 0,22 | 0,94 |
| XJTU, lỗi thật ổ khác | ngoài 0,09; trong 0,12 | 0,94 |
| UORED, cấy | trong 0,55; ngoài 0,74 | 0,98 |
| UORED, lỗi thật ổ khác | trong 0,40; ngoài 0,40; bi 0,41; cách 0,22 | 0,97 |

Thua RF trên XJTU, nhỉnh hơn RF M0 trên UORED. Một seed chưa đủ để đổi mô hình.

## X7: HUST, giao thức ghi trước, 15 "máy", 3 seed

| Chỉ tiêu | Kết quả | Ngưỡng | |
|---|---|---|---|
| Đúng khi trả lời, theo máy như E8 | **0,727** (gộp theo cửa sổ: 0,865) | ≥ 0,85 | **Không đạt** |
| Tỉ lệ trả lời | 0,427 | ≥ 0,60 | Không đạt |
| Bình thường bị gọi lỗi | 0,067 | ≤ 0,10 | Đạt |
| AUROC nhận lỗi lạ | 0,55 | ≥ 0,85 | Không đạt |

**Đính chính:** bản trước báo 0,865 và "đạt 2/4" vì `x_report.py` gộp theo cửa sổ, trong khi giao thức dùng chỉ tiêu của E8, tính theo ổ. Máy nào không trả lời thì bỏ khỏi trung bình, như E8 (25/30 tổ hợp máy và loại lỗi có trả lời). Theo cỡ ổ, độ đúng dao động từ 0,371 đến 1,000.

Bộ phân loại không từ chối đạt macro 0,752, bỏ phiếu đúng 13/15 vòng trong và 10/15 vòng ngoài. HI z ≥ 10: bình thường 0,06; I 0,80; O 0,82; IO 0,93; B 1,00. Đây là lỗi cắt dây 0,2 mm do con người tạo trên các "máy" có thể dùng chung ổ, nên không nên so trực tiếp với lỗi hỏng tự nhiên của E8.

## Dữ liệu đã xóa khỏi máy

Khoảng 25 GB, `data/` còn 17 GB. Mã các thí nghiệm liên quan không chạy lại được ở máy nếu chưa tải lại.

| Đường dẫn | Dung lượng | Lý do | Cách lấy lại |
|---|---|---|---|
| `data/pronostia/` | 6,3 GB | RUL kém (TN3), đặc trưng còn ở `data/tn3_cache` | Tải lại từ nguồn FEMTO; **không có bản trên Modal** |
| `data/ims/` | 9,7 GB | TN2c có đối chứng yếu | Modal còn `ims/cache`; dữ liệu thô tải lại từ nguồn IMS |
| `data/paderborn/rar/` | 4,6 GB | TN2 không đạt G1 | Modal còn `paderborn/rar` và `cond`; [nguồn](https://mb.uni-paderborn.de/en/kat/research/bearing-datacenter/data-sets-and-download) |
| `data/bosch_cnc/` | 1,8 GB | E5, X2 không đạt | Modal còn `bosch_cnc/repo/data`; [repo](https://github.com/boschresearch/CNC_Machining) |
| `data/xjtu/cache_bw/` | 2,4 GB | E4, X8 không đạt | Modal còn bản 6 kHz; tạo lại từ RAR của XJTU |

**Giữ lại:** CWRU, UORED, XJTU (kể cả `extracted/` 12 GB), `paderborn/cache`, `tn3_cache`, mọi JSON kết quả và `results/data_inventory.json`. HUST chỉ có trên Modal.
