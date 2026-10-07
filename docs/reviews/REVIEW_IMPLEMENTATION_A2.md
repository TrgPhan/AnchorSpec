# Rà soát triển khai A2 và thử nghiệm lại — 06/10/2026

> **Cập nhật bàn giao 07/10/2026:** nội dung dưới đây là review generation-only lịch sử. MVP mới đã chạy downstream, calibration healthy riêng và final 3 HP: real-only được chọn trước test, accuracy 99,72%, recall alarm 100%, FPR trung bình 4,52% nhưng seed xấu nhất 6,78% nên **chưa đạt gate vận hành 5%**. Surrogate FPR 20,90%, DDPM FPR 6,78%; chưa chứng minh augmentation giúp mục tiêu vận hành. Xem `C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007\REPORT.md` và `C:\Users\Ad\Downloads\DENSO\generator_benchmark\MVP_README.md`. Không dùng các kết luận cũ về downstream “chưa chạy” làm trạng thái hiện tại; các giới hạn physics/paper/independent-bearing vẫn còn.

## Kết luận về tính đầy đủ

**Có lỗi triển khai và có khoảng cách đáng kể với A2/paper.** Kết quả prototype cũ không đủ để loại bỏ physics có neo hoặc diffusion. Đường surrogate hoạt động trong phạm vi augmentation cục bộ nhưng không thực hiện “Mở rộng” theo điều kiện vật lý của A2.

Nguồn đối chiếu: đọc trực tiếp `C:\Users\Ad\Downloads\DENSO\inputs\a2\A2.pdf` trang 4–5 và tài liệu tham khảo; mã nguồn hiện tại; toàn văn Kahr/Thompson đã lưu ở `C:\Users\Ad\Downloads\DENSO\research_evidence\r1.html` và `C:\Users\Ad\Downloads\DENSO\research_evidence\r3.html`; công thức DDPM tại https://arxiv.org/html/2006.11239v2. Trang MDPI trực tiếp trả 403; không coi lần fetch đó là thành công. Không có toàn văn Ma/Ping hoặc tái lập TimeGAN trong lượt này.

## Vấn đề xác nhận và sửa

| Vấn đề | Hậu quả | Sửa / giới hạn |
|---|---|---|
| DDPM 32 bước có terminal alpha-bar **0.265967** nhưng sampling từ N(0,I) | Forward terminal còn tín hiệu đáng kể, lệch phân phối khởi tạo reverse | Lịch cosine 128 bước với terminal alpha-bar gần 0, kiểm thử terminal |
| Denoiser chỉ gồm convolution local, receptive field 65 samples | Context ngắn hơn các chu kỳ fault đang xét | Residual U-Net bốn cấp, dilated bottleneck, time embedding, train-only x0 support clipping; original comparator, không paper reproduction |
| Audit anchor correlation chỉ 24 mẫu | Mẫu sao chép ở cuối batch có thể lọt gate | Audit mọi mẫu float64; test so với brute force; production chặn mọi candidate corr>0.99 |
| Production chỉ kiểm tra exact hash | Dịch vòng/đảo dấu/gain không bị xem là duplicate | Thêm correlation gate trước nhận mẫu; test fail-closed |
| Final rank projection phá bound pha | Mô tả ±0.65 rad ở output sai | Sửa scope thành intermediate spectral projection, xuất residual từng mẫu; không hứa hai ràng buộc exact đồng thời |
| V2 tái dùng metric cũ | So sánh không đồng nhất khi sửa metric | Tính lại metric tất cả arrays, thêm công cụ merge theo provenance |
| Physics chưa có signal calibration, RPM/provenance thiếu | Không thực hiện đủ bước Neo/Mở rộng | Thêm grid band-kurtosis, envelope peak/decay/jitter/amplitude, diagnostics, anchor-only refinement; provenance nền/neo biên độ/RPM |
| Fit decay thử nghiệm trừ noise floor rồi log epsilon | Sườn decay giả quá dốc | Fit envelope dương trực tiếp; xuất fallback/bound diagnostics; noisy overlapping pulses vẫn có bias |
| “physics_unanchored” vẫn dùng RMS neo | Không phải baseline không dùng faults thật | Ghi rõ chỉ tham số uncalibrated, xuất amplitude_uses_anchors; không dùng như bằng chứng healthy-only |
| Chạy lại overwrite results | Mất evidence cũ | CLI benchmark/finalizer từ chối thư mục có sẵn, hỗ trợ --output |
| Production import torch dù dùng NumPy/SciPy | Không đúng phạm vi dependency đã mô tả | Lazy import deep comparator; production không import torch |

Mã trước review được giữ ở `C:\Users\Ad\Downloads\DENSO\generator_benchmark\code_before_review_20261006`. Không có Git repository để cung cấp git diff; không xóa artifacts cũ.

## Audit toàn bộ production cũ

Thư mục evidence: `C:\Users\Ad\Downloads\DENSO\generator_benchmark\results_review_audit`.

| Lỗi | Số mẫu | Corr median synthetic–anchor | P05–P95 | Corr median real-development–anchor | Median cyclic corr synthetic pairs cùng neo |
|---|---:|---:|---|---:|---:|
| Inner | 10.000 | 0.938080 | 0.924280–0.949595 | 0.160794 | 0.882429 |
| Outer | 10.000 | 0.955616 | 0.939490–0.967057 | 0.277706 | 0.921780 |
| Ball | 10.000 | 0.931815 | 0.918725–0.943548 | 0.233961 | 0.868388 |

Mọi array hash khớp scale.json; mọi provenance waveform hash khớp; 10.000 hashes unique/class; histogram **mọi** output bằng histogram neo nguồn; finite và fidelity gate đều qua. Không mẫu nào corr>0.99. Pair audit lấy 128 cặp/neo, không phải mọi cặp. Real khác tải không phải đối chứng condition-matched hay bằng chứng independent bearings. Phân bố same-record/heldout có trong JSON, không diễn giải low correlation thành bad fault fidelity.

Đã tái sinh **15 stress cases**: mỗi case lặp bitwise-identical và hash khớp stress artifacts cũ. Những numerical claims từng chưa có evidence đọc được nay được xác nhận bằng lần audit mới; không xác nhận hiệu quả downstream từ đó.

Pha cuối: trên 256 outputs đầu/class, median tỷ lệ bins vượt 0.65 rad là inner 23.14%, outer 38.48%, ball 22.56%. Bỏ bin DC và bins original magnitude <=1e-6 mức lớn nhất. Phase max chịu ảnh hưởng bins nhỏ, không đồng nghĩa sai label vật lý.

## Phase sweep train-only

3 seeds ×3 labels ×64 outputs/bound; không dùng development/test để chọn bound.

| Bound intermediate | Mean fidelity acceptance | Worst label/seed | Mean median anchor corr |
|---:|---:|---:|---:|
| 0.35 | 100% | 100% | 0.9818 |
| 0.65 | 99.83% | 98.44% | 0.9421 |
| 1.00 | 99.65% | 98.44% | 0.8723 |
| 1.50 | 96.35% | 89.06% | 0.7235 |
| pi | 59.72% | 10.94% | 0.3580 |

Acceptance ở bảng này là engineering fidelity gate, chưa gồm copy gate. Nới bound giảm corr nhưng vẫn giữ histogram, không tạo coverage điều kiện mới. **Không tự đổi default sang 1.0** dựa trên sweep nhỏ/post-hoc này.

## Chạy lại và evidence

- `C:\Users\Ad\Downloads\DENSO\generator_benchmark\results_review_v3`: chạy lại 9 methods ×3 seeds ×3 labels ×256 outputs; deep 300 bước và denoiser cũ sau sửa schedule. Giữ như intermediate evidence, không gọi DDPM ở đây là bản cuối.
- `C:\Users\Ad\Downloads\DENSO\generator_benchmark\results_review_physics_final`: calibrated physics/refinement bản cuối và surrogate, cùng seeds/quota. Physics đạt sanity gate nhưng diagnostic W1 còn lớn; không gọi đã vượt bước kiểm tra trước Mở rộng của A2.
- `C:\Users\Ad\Downloads\DENSO\generator_benchmark\results_review_deep_1500`: GAN và DDPM U-Net 1500 steps/seed. Cùng output quota nhưng không compute-matched với surrogate/physics; tăng budget và architecture/sampler cùng lúc nên không quy toàn bộ cải thiện cho riêng schedule.
- Lượt deep dài **hoàn tất exit code 0**, đủ 18 development rows, 9 heldout-load exploratory rows và scale 256 outputs/class. Scale DDPM finite/hash match, sanity 256/256 mỗi class; đây là scale benchmark không phải production đã qua mọi fidelity/copy gates. Tiến trình tự kết thúc trước lệnh dừng dự kiến; không có run bị kill. Trạng thái đã xác minh ở `C:\Users\Ad\Downloads\DENSO\generator_benchmark\results_review_deep_1500\run_status.json`.
- `C:\Users\Ad\Downloads\DENSO\generator_benchmark\results_review_final`: tái sản xuất 30.000 waveforms sau sửa production gates. Inner 10.001 attempts, outer 10.000, ball 10.014; tổng 15 rejects, 0 copy rejects. Mọi mẫu qua full gate, unique/hash/provenance được đọc kiểm tra lại ở verification.json; arrays khớp bản cũ vì cấu hình surrogate không đổi.
- `C:\Users\Ad\Downloads\DENSO\generator_benchmark\review_cli_smoke`: CLI 128 inner outputs, finite, unique và audited cả 128.
- `C:\Users\Ad\Downloads\DENSO\generator_benchmark\review_tests.log`: **17 tests pass**, có deep training/sampling smoke trên CUDA và gradient kiểm tra long context. Đã sửa lỗi CUDA nondeterministic linear interpolation bằng nearest upsampling, giữ deterministic algorithms bật.

Công cụ mới: `C:\Users\Ad\Downloads\DENSO\generator_benchmark\review_audit.py`, `C:\Users\Ad\Downloads\DENSO\generator_benchmark\review_compare.py`, `C:\Users\Ad\Downloads\DENSO\generator_benchmark\physics_calibration.py`. Tất cả code Python qua syntax parse. Benchmark tương lai lưu state_dict cuối cùng cho deep models; không có best-checkpoint chọn bằng heldout. Lượt deep dài đã khởi động trước thay đổi save checkpoint, vì vậy không tự hứa có checkpoints cho lượt đó.

## Những phần chưa full implement / chưa chứng minh

### Bảng so sánh development sau sửa (đủ ba seeds)

Evidence thống nhất tại `C:\Users\Ad\Downloads\DENSO\generator_benchmark\results_review_comparison\selection.json`. Mean W1 càng nhỏ càng gần real-development theo diagnostics hiện tại; eligibility cần sanity/fidelity >=95% ở **mọi** label/seed, no audited copies, uniqueness, finite và seed repeat.

| Method | Mean W1 | Worst fidelity acceptance | Qua toàn bộ gates? |
|---|---:|---:|---|
| constrained_surrogate | 0.7289 | 99.22% | Có |
| DDPM U-Net, 1500 steps | **1.1503** | **99.22%** | **Có** |
| physics_anchored cũ | 3.2846 | 95.70% | Có |
| physics_calibrated mới | 4.6825 | 92.19% | Không |
| GAN prototype, 1500 steps | 6.2944 | 0.39% | Không |

DDPM mới có worst sanity acceptance 99.22%, mean fidelity acceptance 99.78%; không output nào corr>0.99. Across 9 label/seed rows, median-of-medians anchor cyclic correlation là **0.3499**, disjoint synthetic-pair cyclic correlation là **0.3043** (128 pairs/row). Đây là bằng chứng giảm near-anchor similarity trong tested distribution, **chưa chứng minh new-condition coverage hoặc downstream utility**. Pair sampling khác same-source surrogate pair audit, không so sánh như một effect size condition-matched.

Kết quả này **thay đổi đánh giá cũ**: diffusion không còn là comparator bị sanity/fidelity gate loại. Surrogate vẫn thắng mean diagnostic W1, nhưng đó không đồng nghĩa thắng trade-off fidelity–diversity hay downstream. Không thể chọn duy nhất surrogate cho toàn bộ yêu cầu A2 từ W1; giữ baseline local augmentation và giữ DDPM như candidate đáng đánh giá tiếp.

Calibrated physics qua sanity toàn bộ nhưng fail fidelity ở một label/seed. Việc giới hạn fc trong band chọn bằng kurtosis và một oscillator có thể làm mất các thành phần cộng hưởng khác; refinement không chữa model misspecification. Không mở rộng miền hay export production physics như fault-verified. Simple gain/shift/noise cũng qua fidelity nhưng 100% audited corr>0.99: gate này là lựa chọn engineering anti-near-copy, **không chứng minh simple augmentation vô ích**.

1. Physics calibrated không phải fast kurtogram chính xác, chưa joint fit aligned impulses, chưa contact-dynamics 3D của Kahr, chưa Bayesian uncertainty posterior. Jitter/decay estimates có fallbacks và bound clipping; một oscillator không biểu diễn đầy đủ đường truyền đa cộng hưởng.
2. A2 đòi miền vật lý hợp lệ cho RPM/load/severity/SNR và healthy background condition-matched. Code mới truyền RPM theo metadata nguồn, **chưa chứng minh extrapolation RPM/load/severity**, chưa dữ liệu condition-matched toàn miền. Các orders cố định CWRU SKF6205, ball là 2×BSF; không áp ngầm sang DENSO.
3. GAN vẫn BCE convolutional comparator, không TimeGAN embedding/recovery/supervised latent losses. DDPM vẫn original conditional generator, không Thompson multivariate healthy-to-fault transfer, không tái lập Ping/Ma. Loss giảm không chứng minh hội tụ/label fidelity.
4. Không thực hiện đai/LM guide/hard negatives/nhánh detector A–B–C vì thiếu data và nằm ngoài generator experiment hiện tại. Chưa có real-only vs real+synthetic test, independent-bearing validation, licensing DENSO/public redistribution.
5. Tất cả heldout-load đã được quan sát nhiều lần: exploratory, không fresh confirmatory test. Feature W1/gates cùng họ diagnostics dễ ưu ái surrogate và anchor-feature-fit physics; cần external checks trước claim utility.

**Quyết định có căn cứ hiện tại:** giữ surrogate như baseline local augmentation với gates đã sửa; tiếp tục diffusion/physics như hướng nghiên cứu, không gọi surrogate là hoàn tất A2, không loại bỏ diffusion/physics chỉ từ prototype cũ. Số lượng, uniqueness, fidelity gate, diversity và downstream utility là năm điều khác nhau.
