# AnchorSpec: kết quả và bộ trình bày ngày 04/11/2026

Đã bổ sung đối chứng trực tiếp surrogate cũ và cấy vật lý, một nhánh chọn nguồn,
một nhánh biểu diễn phổ, kiểm tra nguồn mới KAIST, cổng chất lượng tín hiệu và
replay offline. Mục tiêu phương pháp vượt trội toàn diện CHƯA được xác nhận.
Không bỏ kết quả âm tính và không đổi ngưỡng sau khi xem test để tạo điểm đẹp.

## Phương pháp thay đổi ở đâu

Surrogate giữ phân bố biên độ và gần giữ phổ mẫu lỗi thật, thay đổi pha có giới
hạn. Physics tạo thành phần lỗi rồi cộng vào nền khỏe. W Select chọn nguồn,
biểu diễn raw/delta và classifier bằng validation trên ổ donor. W-Spectral
kiểm tra phổ công suất và bao hình để giảm phụ thuộc vào đặc trưng vòng trong
và vòng ngoài. Các thuật toán thành phần có sẵn; chưa tuyên bố phát minh mới.

Tất cả biến thể surrogate của ổ validation bị loại khỏi training cùng ổ gốc.
SVM giữ cùng tổng trọng số theo số cửa sổ thật, không tự tăng độ mạnh chỉ vì
thêm nhiều mẫu sinh. Một sự kiện mỗi lớp không đủ inner validation đủ lớp:
dùng fallback đã khai báo, không tạo điểm CV giả.

## UORED: cùng 20 ổ, cùng donor, bốn loại lỗi

| Phương án | 1 sự kiện | 2 sự kiện | 4 sự kiện |
|---|---:|---:|---:|
| RF cũ, chỉ dữ liệu thật | 41.0% | 45.3% | 60.1% |
| RF cũ, thêm cấy lỗi | 33.0% | 34.9% | 42.4% |
| RF cũ, thêm surrogate | 40.4% | 44.6% | 61.4% |
| Chỉ dữ liệu thật W | 40.4% | 56.2% | 48.0% |
| Surrogate hai lớp vòng | 44.1% | 55.9% | 53.6% |
| Cấy lỗi vật lý W | 38.8% | 52.7% | 51.5% |
| Surrogate mọi lớp | 37.6% | 40.9% | 53.0% |
| Chọn nguồn W | 40.4% | 45.4% | 55.4% |
| Chỉ lỗi thật Y | 41.0% | 63.6% | 66.7% |
| Phổ cố định | 39.6% | 60.7% | 62.5% |
| Ghép đặc trưng cố định | 42.5% | 62.5% | 65.7% |
| Chọn biểu diễn phổ | 40.4% | 61.3% | 63.2% |
| Thêm biên độ vào Y | Không chạy | 55.9% | 57.5% |
| Thêm phổ và biên độ vào Y | Không chạy | 51.8% | 65.9% |
| Chọn view có biên độ | Không chạy | 57.1% | 66.2% |

Đây là macro recall late khi đầu vào đã được biết là có lỗi. Tính trung bình
seed trước rồi theo ổ và lớp. 180 cấu hình outer có tái sử dụng 20 ổ, không phải
180 thí nghiệm độc lập. RF cũ+surrogate là hàm sinh cũ chạy trong giao thức
UORED chung, không phải tái hiện con số CWRU của release07/10. Hai nhánh
surrogate_ring và physics chỉ bổ sung hai lớp vòng; surrogate_all bổ sung cả4.
RF cũ vẫn có lớp healthy; các mô hình W chỉ học lỗi vì bài toán có điều kiện.

Chọn biểu diễn phổ so với đối chứng real-only Y ở4 sự kiện:
-3.4 điểm phần trăm; bootstrap theo ổ95% từ
-13.3 đến +5.6 điểm.
Các CI chưa hiệu chỉnh nhiều phép so sánh. UORED đã được xem nhiều lần.
Nhánh phổ xuất hiện SAU kết quả W và KAIST: chưa được xác nhận trên nguồn mới.

W-Amplitude được thử tiếp sau W-Spectral: thêm log RMS và log peak theo nền
khỏe vào bộ chẩn đoán Y. Chạy 120 cấu hình, tái lập khớp prediction counts
gốc của Y trước khi diễn giải. Nhánh này cũng chưa vượt đối chứng Y. Cả bốn
đợt W, KAIST, W-Spectral, W-Amplitude được giữ lại, không chỉ chọn lần tốt.

## Phân tầng: kết quả hứa hẹn ở lỗi đang phát triển

Sau phân tích trade-off giữa các lớp, W-Hierarchy được khai báo rồi chạy riêng
60 cấu hình: phân biệt nhóm vòng với nhóm bi/vòng cách, sau đó dùng chuyên gia
phù hợp cho từng nhóm. Cổng nhóm và chuyên gia bi/vòng cách dùng243đặc trưng;
chuyên gia vòng dùng45đặc trưng. Cả ba học từ các sự kiện thật đã xác nhận,
không thêm dữ liệu sinh. Nhân điểm nhóm và chuyên gia, gộp nhân quả5cửa sổ.

| Trạng thái UORED | Đối chứng Y | Phân tầng |
|---|---:|---:|
| Lỗi đang phát triển | 70.3% | 81.1% |
| Lỗi nặng | 66.7% | 62.8% |

Lỗi đang phát triển tăng 10.9 điểm phần trăm; CI95%
chưa hiệu chỉnh từ +0.2 đến +22.8 điểm.
Phải đọc cùng kết quả giảm ở lỗi nặng. Nhãn developing fault đã chứa lỗi,
không phải dự báo trước thời điểm hỏng hay đo lead time. Đây là phát hiện
exploratory sau nhiều lần thử trên cùng20ổ; chưa được xác nhận nguồn độc lập.
Chưa dùng nhãn early/late của test để chuyển giữa hai mô hình khi vận hành.
Runtime demo vẫn dùngY; kiến trúc phân tầng là ứng viên nghiên cứu tiếp.

## KAIST: nguồn mới cho chuyển tải và mức khuyết tật

21 MAT,18 tệp lỗi và3 nền khỏe; 1.327GB dữ liệu giải nén. Dùng một trục x housingA.
Hai lớp inner/outer, ba tải0/2/4Nm, ba mức03/10/30. Mỗi lần học ở một tải và
hai mức khuyết tật, kiểm tra ở tải khác và mức chưa học. Tổng18split, ba seed.
Các split dùng chung tệp nên không tạo CI giả từ hàng nghìn cửa sổ.

| Phương án | Macro recall |
|---|---:|
| Chỉ dữ liệu thật W | 99.14% |
| Surrogate hai lớp vòng | 99.92% |
| Cấy lỗi vật lý W | 95.06% |
| Surrogate mọi lớp | 99.92% |
| Chọn nguồn W | 99.14% |
| RF cũ, chỉ dữ liệu thật | 99.22% |
| RF cũ, thêm cấy lỗi | 94.88% |
| RF cũ, thêm surrogate | 98.20% |
| Chỉ dữ liệu thật Y | 99.22% |

Điểm cao không chứng minh vượt trội khi real-only cũng gần100%. Bộ này không
xác nhận bi/vòng cách, thiếu bôi trơn, dị vật hay điều kiện nhà máy DENSO.
Không so trực tiếp phần trăm hai lớp KAIST với bốn lớp UORED.

Schema: MAT có struct Signal, time riêng và4 cột rung; metadata ghi lưu MKS,
display g, factor0.101971621297793. Đã áp dụng factor theo metadata; ghi lại
giả định và không coi raw numbers là g. Tệp healthy0Nm dài300s, khác120s trong
mô tả; chỉ lấy30s nền theo protocol nên không tạo lợi thế về dữ liệu khỏe.
CRC từng ZIPmember và SHA256 local đã kiểm tra; không xác nhận hash toànZIP.

## Replay và khả năng sử dụng

- Đã replay toàn bộ20ổ bằng nhánh DiagnosticExperts real-only Y, seed11,
  bốn sự kiện mỗi lớp. Lưu lựa chọn, donor, hash model và kết quả từng cửa sổ.
- Kiểm tra kích thước cửa sổ, tần số lấy mẫu, nonfinite, bão hòa và tín hiệu phẳng;
  dữ liệu không đạt trả `needs_signal_check`, không cố đoán loại lỗi.
- Cờ bất thường trong replay lấy từ nhãn để kiểm tra giao diện. Đây KHÔNG phải
  đo end-to-end, báo nhầm hay đánh giá bộ phát hiện của DENSO.
- Model lớn nhất 200.5KiB;
  thời gian chia đều theo cửa sổ trong batch, median
  2.00ms trên máyWindows.
  Không phải latency online đã đo trênPi5; không bao gồm I/O và nhận tín hiệu.

## Phần có thể trình bày và phần chưa đạt

Có thể trình bày nguồn dữ liệu, pipeline, đối chứng minh bạch, phân tích giới
hạn cảm biến, demo replay và cách kiểm soát dữ liệu trước chẩn đoán. Không nên
nói đã giải quyết đủ hết dầu, vỡ vòng cách, dị vật hoặc dự báo giờ hỏng.

Chưa có bằng chứng vượt SOTA, chưa có thắng ổn định trước đối chứng tốt nhất
trên nhiều nguồn bốn lớp, chưa xác nhận lỗi lạ, chưa hiệu chuẩn độ tin cậy và
chưa đo số báo nhầm mỗi máy mỗi tháng. Trạng thái là MVP nghiên cứu offline.

## Mở và chạy lại

- [Demo kết quả tương tác](results/w/evidence_demo.html).
- [PowerPoint cập nhật](results/w/AnchorSpec_Bang_chung_20261104.pptx).
- [Giao thức so nguồn](PROTOCOL_W_COMPARE.md), [KAIST](PROTOCOL_W_KAIST.md),
  [phổ](PROTOCOL_W_SPECTRAL.md), [biên độ](PROTOCOL_W_AMPLITUDE.md),
  [phân tầng](PROTOCOL_W_HIERARCHY.md).
- Biểu đồ `results/w/uored_comparison.png` và `kaist_comparison.png`.

```powershell
python anchorspec/w_compare.py prepare
python anchorspec/w_compare.py run
python anchorspec/w_kaist.py
python anchorspec/w_kaist_eval.py prepare
python anchorspec/w_kaist_eval.py run
python anchorspec/w_spectral.py prepare
python anchorspec/w_spectral.py run
python anchorspec/w_amplitude.py prepare
python anchorspec/w_amplitude.py run
python anchorspec/w_hierarchy.py
python anchorspec/w_replay.py
python anchorspec/w_delivery.py
python -m pytest -q anchorspec
```

Nguồn: [UORED](https://data.mendeley.com/datasets/y2px5tg92h/5),
[KAIST](https://data.mendeley.com/datasets/ztmf3m7h5x/6),
[bài mô tả KAIST](https://pmc.ncbi.nlm.nih.gov/articles/PMC10036499/),
[mã dự án](https://github.com/TrgPhan/AnchorSpec).
Raw data, caches và pickle model nằm trong data/ đượcGitignore. Không push
dữ liệu hoặc nội dung thảo luận nhà máy. Kết quả/public code hiện chưa commit.
