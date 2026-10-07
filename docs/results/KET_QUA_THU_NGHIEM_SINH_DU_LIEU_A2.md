# A2 — Thử nghiệm sinh dữ liệu và quyết định một hướng triển khai

> **Trạng thái cuối 07/10/2026:** release MVP mới có **3.000 waveform** (1.000/lỗi), khác thư viện 30.000 mẫu lịch sử dưới đây. Downstream trước/sau đã chạy, chọn real-only trước test; recall alarm 100%, accuracy 99,72%, FPR trung bình 4,52%, seed xấu nhất 6,78%. **Phần mềm chạy được; augmentation chưa chứng minh có ích và gate FPR≤5% mọi seed chưa đạt.** Nguồn kết luận mới: `C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007\final\summary.json`; hướng dẫn: `C:\Users\Ad\Downloads\DENSO\generator_benchmark\MVP_README.md`. Giữ các quyết định/số liệu cũ bên dưới làm lịch sử, không thay thế giao thức cuối hoặc dùng lại holdout đã xem để tuning.

> **Đính chính sau review 06/10/2026:** đây là báo cáo V1/V2 lịch sử, không phải đánh giá bản triển khai cuối. Có lỗi DDPM terminal noise, giới hạn context, audit chỉ 24 mẫu và mô tả bound pha cuối chưa đúng; đã sửa và chạy lại. Xem `C:\Users\Ad\Downloads\DENSO\docs\reviews\REVIEW_IMPLEMENTATION_A2.md`. Không dùng kết quả prototype cũ để loại bỏ diffusion/physics hoặc khẳng định đã hoàn tất A2. Giữ số liệu cũ để bảo toàn evidence.

**Ngày:** 06/10/2026. **A2 ở đây là hồ sơ “Neo và Mở rộng” của đội**, theo yêu cầu người dùng; khác mã bài scarce-fault trên website không làm đổi mục tiêu thí nghiệm. **Mục tiêu chính là sinh nhiều dữ liệu lỗi ổn định, không tìm detector tốt nhất.**

## 1. Quyết định duy nhất

**Triển khai bộ sinh surrogate có ràng buộc phổ–biên độ và giới hạn biến đổi pha (bounded-phase IAAFT), kèm quality gate dựa trên anchors, provenance và giới hạn retry.** Tên code: `constrained_surrogate`.

Không chọn GAN, diffusion, healthy-only hoặc mạng embedding làm lõi hiện tại. Không tiếp tục mặc định simulator vật lý có neo chỉ vì đó là ý tưởng trong PDF. Đây là lựa chọn engineering từ thử nghiệm thực tế trên CWRU; chưa phải bằng chứng thắng trên dữ liệu DENSO.

Đầu ra: nhiều **cửa sổ tín hiệu rung thô** cho một loại lỗi đã có mẫu neo, có fs, label synthetic, nguồn neo, seed, cấu hình và hash. Không chỉ sinh feature vectors, không chỉ huấn luyện detector. Giữ nhiệm vụ báo cáo trước/sau augmentation là kiểm tra downstream phụ, không tiêu chí chính quyết định generator.

**Phạm vi trung thực:** sinh biến thể cục bộ của lỗi đã quan sát, không tạo thêm thông tin về cơ chế lỗi chưa có. Cùng histogram và tương quan neo khoảng 0,94 cho thấy support còn hẹp; dữ liệu sinh nhiều không biến 1 sự cố thành 10.000 sự cố độc lập. Nếu yêu cầu chính thức bắt buộc lỗi chưa từng thấy hoặc waveform liên tục dài, thử nghiệm này **chưa giải được phần đó**.

## 2. Dữ liệu thật đã tải và xử lý

Đã tải **12 tệp MATLAB từ máy chủ chính thức CWRU**, có SHA-256 trong `C:\Users\Ad\Downloads\DENSO\generator_benchmark\data_manifest.json`:

| Vai trò | Healthy | Inner | Outer @6:00 | Ball | Motor load |
|---|---|---|---|---|---|
| Anchor train | 97 | 105 | 130 | 118 | 0 HP |
| Development | 98 | 106 | 131 | 119 | 1 HP |
| Heldout load | 99 | 107 | 132 | 120 | 2 HP |

Nguồn: [12k faults](https://engineering.case.edu/bearingdatacenter/12k-drive-end-bearing-fault-data), [normal](https://engineering.case.edu/bearingdatacenter/normal-baseline-data), [apparatus](https://engineering.case.edu/bearingdatacenter/apparatus-and-procedures), [bearing information](https://engineering.case.edu/bearingdatacenter/bearing-information).

- Vòng bi drive-end SKF6205, lỗi EDM 0,007 inch; artificial testbed defects, không lỗi nhà máy DENSO.
- Tín hiệu lỗi fs=12 kHz; 2048 điểm/cửa sổ, không overlap. Neo **8 cửa sổ đầu của 1 record/lỗi**, ~1,365 s/lỗi; không gọi là 8 shots/sự cố độc lập.
- Healthy downsample 48→12 kHz có ghi rõ **working assumption**, vì normal table không có fs từng tệp. Kiểm tra peak rotor hỗ trợ nhưng chưa thay metadata gốc. Hướng được chọn không dùng healthy background, nên không phụ thuộc giả định này.
- `99.mat` chứa cả arrays `X098` và `X099`: loader chọn **đúng `X099_DE_time`**, không chọn tùy tiện key đầu gây leak.
- Khác tải không được mặc định khác physical bearing. Chưa có independent-bearing external validation.
- Public download không tự cấp quyền commercial/redistribution. Không phát hành public raw/derived bundle khi chưa chốt quyền.

## 3. Thử nghiệm đã thực sự chạy

### 3.1. V1: bảy comparator

Chạy **7 bộ sinh ×3 seed ×3 lỗi ×256 cửa sổ =16.128 cửa sổ** để so sánh trên development. Các bộ sinh: simple augmentation, unrestricted IAAFT, physics chưa neo, physics có neo, envelope surrogate, conditional GAN prototype, DDPM prototype.

GAN/DDPM là code prototype nhỏ tự hiện thực trong PyTorch, **300 optimizer steps**, không phải TimeGAN hoặc tái lập bài Thompson. Physics là impulse-response approximation, không tái lập 3D finite-element của Kahr. Chỉ có thể kết luận về prototype/cấu hình/ngân sách đã thử, không bác bỏ toàn bộ họ phương pháp.

### 3.2. V2: sửa failure envelope, không che lần thử trước

IAAFT không ràng buộc pha ban đầu đứng đầu trong các hướng không copy, nhưng kiểm tra thêm phát hiện envelope harmonic lỗi inner bị suy yếu: gate envelope tốt nhất chưa đạt ổn định; mức acceptance thấp nhất 12,5%. Vì vậy **không chọn chỉ vì sinh hữu hạn 100%**.

Thêm bounded-phase surrogate, chạy **3 seed ×3 lỗi ×256=2.304 cửa sổ**. Đồng thời bổ sung cùng một gate dựa trên anchor cho toàn bộ comparator V1. Mức ±0,65 rad và factor4 là cấu hình engineering exploratory, **không threshold vật lý phổ quát**.

V1 đã tự động đánh giá load2 trước khi V2 sửa method. V2 không đọc kết quả V1 test để rank hoặc tune, nhưng load2 **không còn là test confirmatory mới**. Báo V2 là **heldout-load exploratory**, cần dataset/group độc lập mới cho xác nhận chính thức.

### 3.3. Chỉ tiêu generation-first

Không fit classifier. Đo:

1. Hữu hạn và tỷ lệ RMS/crest hợp lệ theo anchors.
2. Giữ energy các harmonic envelope tại fault order trong khoảng anchor expanded factor4.
3. Exact duplicate hash và maximum circular correlation sau căn dịch với anchors (audit 24 mẫu mỗi batch so sánh).
4. Seed lặp lại cho kết quả giống hệt trong cùng môi trường.
5. Sai lệch waveform diagnostics: normalized Wasserstein-1 trên 18 features, gồm log RMS/kurtosis/crest, 12 PSD bands, 3 envelope harmonic energies. Scale cố định từ anchor, không fit theo generator/test.
6. Speed, fit time, lượng bộ nhớ/disk, retry/reject ledger.

**W1 càng nhỏ càng gần các diagnostics đã chọn**, không phải accuracy, không có ngưỡng tuyệt đối chứng minh fault fidelity. Normalization và tập features có thể thiên vị phương pháp bảo toàn phổ; phải báo đây là hạn chế.

## 4. Kết quả từng nhánh generator

Từ `C:\Users\Ad\Downloads\DENSO\generator_benchmark\results_v2\selection.json`. Tỷ lệ dưới đây là **mức thấp nhất trong các tổ hợp class/seed**, không tỷ lệ gộp đẹp hơn:

| Nhánh | Dev mean W1 ↓ | SD giữa seed ↓ | Sanity thấp nhất | Envelope gate thấp nhất | Kết luận |
|---|---:|---:|---:|---:|---|
| Simple shift/gain/noise | 0,852 | 0,006 | 100% | 100% | Rất nhanh nhưng audit cả 24/24 samples mỗi batch có corr>0,99; biến đổi gần-copy, không chọn làm generator chính |
| Unrestricted IAAFT | 1,114 | 0,005 | 100% | 12,5% | Sinh ổn định số học, làm yếu cấu trúc fault envelope; không chọn bản không giới hạn pha |
| Physics chưa neo | 4,260 | 0,003 | 98,83% | 0% | Rất nhanh, tham số dễ kiểm toán nhưng domain gap lớn; chưa đạt fidelity |
| Physics có neo | 3,487 | 0,303 | 100% | 100% | Neo có ích so với chưa neo, song sai lệch phổ và biến thiên fit vẫn cao; không chọn lõi hiện tại |
| Envelope surrogate | 4,436 | 0,009 | 100% | 100% | Giữ envelope nhưng thay carrier làm PSD sai lớn; gate một mặt không đủ chứng minh chất lượng |
| Conditional GAN prototype | 5,961 | 0,393 | 52,34% | 0% | Sampling GPU nhanh nhưng training/small-data không ổn định trong budget; không chọn |
| DDPM prototype | 2,417 | 0,173 | 0,78% | 0% | Sai amplitude/envelope ở một seed/class, chậm hơn surrogate; không chọn cấu hình này |
| **Bounded-phase constrained surrogate** | **0,728** | **0,0023** | **100%** | **99,22%** | **Chọn duy nhất:** biến thể lỗi quan sát, ổn định và ít lệch diagnostics nhất trong các hướng qua gate |

Physics có neo, envelope surrogate và bounded surrogate qua feasibility gates; **chọn bằng development W1 +0,25×seed SD**. Gate không bị thay đổi tùy variant để chọn winner. Không dùng test accuracy.

Tốc độ dev trung bình của bounded surrogate khoảng **206 cửa sổ/s**, CPU. Không phải fastest method, nhưng “nhiều mẫu nhanh mà fidelity sai” không giải yêu cầu.

### Heldout-load exploratory

Hướng đã chọn cho mean W1 **0,996**, seed SD **0,0066**; sanity và envelope gate đều 100% trong 9 batch. Chưa bằng chứng perfect distribution match: RMS outer generated ~0,675 so với real load2 ~0,571 cho thấy còn domain shift.

Tương quan neo median trung bình dev **0,942**, không có audited corr>0,99. **Không nên diễn giải là hoàn toàn không memorization**: bộ sinh cố ý giữ phân bố giá trị của anchor, support hạn chế và audit correlation không bao phủ mọi mẫu/kiểu sao chép.

## 5. Đánh giá khả thi các paper/nhánh trong phần 5 báo cáo nghiên cứu

| Nguồn/nhánh | Có sinh waveform không? | Đã chạy gì? | Quyết định cho A2 sinh nhiều |
|---|---|---|---|
| Kahr — simulation + healthy | Có | Impulse-response surrogate physics chưa/có neo; **không tái lập FE3D/CNN** | Có cơ sở vật lý nhưng chưa đủ gần waveform trong prototype; không chọn hiện tại |
| Ma — physics few-shot | Theo metadata là hướng gần | Full text/code chưa có; không giả đã tái lập | Chưa đủ evidence để chọn hoặc loại trên kết quả paper |
| Thompson — diffusion | Có | Conditional DDPM nhỏ; **không tái lập original paper** | Không chọn cho budget few-anchor hiện tại; không kết luận diffusion nói chung vô dụng |
| TS2Vec | Không, encoder | Không chạy vì không có output generator | Không phải hướng chính đáp ứng yêu cầu; chỉ optional evaluator sau này |
| Deep SVDD | Không, one-class detector | Không chạy để tránh đổi mục tiêu | Không phải hướng triển khai generator |
| Kim — rigorous TSAD evaluation | Không, methodology | Áp dụng nguyên tắc chống đánh giá đẹp giả | Dùng làm guardrail, không giải sinh dữ liệu |
| TSB-AD | Không phải fault generator | Không chạy benchmark detector | Không chọn làm architecture chính |
| TimeGAN | Có | GAN nhỏ, **không TimeGAN original** | Chưa tái lập TimeGAN; prototype GAN không ổn định đủ, không chọn mặc định |
| Surrogate constrained randomization (Schreiber/Schmitz) | Có, variations | IAAFT và bounded-phase extension trực tiếp | **Chọn hướng constrained waveform augmentation**, không claim bài gốc chứng minh hiệu quả bearing few-shot |

Nguồn surrogate: [Schreiber & Schmitz — Surrogate time series](https://arxiv.org/abs/chao-dyn/9909037). Bounded-phase variant và gates là hiện thực engineering của lượt này, không novelty học thuật đã được xác minh.

## 6. Thiết kế triển khai duy nhất

```text
Fault anchors được phép sử dụng + metadata/fs/label
          ↓
Windowing không overlap + kiểm tra unit/finite/sensor
          ↓
FFT magnitude + empirical amplitude distribution của anchor
          ↓
Random phase có bound ±0,65 rad
          ↓
30 vòng spectral projection ↔ amplitude-rank projection
          ↓
Anchor-only RMS/crest/envelope gate
          ↓
Unique hash + retry tối đa 4× quota, lỗi thì dừng
          ↓
Waveforms.npy + provenance.json + manifest.json
```

Chưa có anchors hoặc label/condition không được hỗ trợ → **không tự sinh rồi gán nhãn lỗi**. Không fallback âm thầm về copy mẫu thật. Chưa hỗ trợ continuous long record; xuất nhiều windows độc lập về seed, không độc lập về nguồn vật lý. Healthy background không dùng trong lõi này; proposal sửa để phản ánh quyết định mới thay vì ép “tiêm lỗi” không được kiểm chứng.

## 7. Code và tái chạy

Thư mục code đầy đủ: `C:\Users\Ad\Downloads\DENSO\generator_benchmark`.

```powershell
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\test_generators.py'
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\generate.py' --label inner --count 1000 --seed 901 --output 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\new_run'
```

Code downloader/benchmark/deep prototypes/CLI/tests và hướng dẫn nằm cùng thư mục. Kết quả V1/V2 lưu lại, không chỉ bảng tóm tắt bằng lời. Không cần GPU cho hướng chọn. PyTorch chỉ dùng ở comparator.

## 8. Production và stress đã hoàn tất

| Loại | Mẫu hợp lệ xuất | Attempts | Rejected | Thời gian sinh | Accepted/s |
|---|---:|---:|---:|---:|---:|
| Inner | 10.000 | 10.001 | 1 | 49,72 s | 201,11 |
| Outer | 10.000 | 10.000 | 0 | 51,44 s | 194,40 |
| Ball | 10.000 | 10.014 | 14 | 48,81 s | 204,89 |
| **Tổng** | **30.000** | **30.015** | **15** | **149,97 s** | **~200** |

Mỗi class 10.000 unique hashes, mọi output finite; waveform files tổng 245,76 MB (float32, chưa tính headers/provenance). **99,95% attempts được nhận**, không 100% vì đã ghi cả rejected. Output gate quality không chứng minh mọi label vật lý đúng.

Stress thêm **5 seeds ×3 labels ×64 quota=960 outputs**, sinh lại cùng seed cho mọi batch giống hệt trong môi trường hiện tại. **7 unit tests qua**, gồm histogram preservation, seed repeat/difference, shape/finite, unsupported method, fail-closed quota và duplicate refusal. CLI smoke 128 inner samples cũng chạy thành công.

Kết quả thực: `C:\Users\Ad\Downloads\DENSO\generator_benchmark\results_v2\scale.json`, `C:\Users\Ad\Downloads\DENSO\generator_benchmark\results_v2\stress.json`. Dataset ở cùng thư mục với `production_inner.npy`, `production_outer.npy`, `production_ball.npy` và provenance riêng. Không suy audited 24-sample correlation là audit mọi mẫu.

**Kết luận:** đã tìm và hiện thực một hướng sinh nhiều waveform ổn định trong phạm vi CWRU tested. Giữ constrained surrogate làm **hướng triển khai duy nhất hiện tại**, không đánh tráo thành detector; vẫn cần anchors DENSO và fresh independent validation để gọi đây là bộ sinh DENSO có fault fidelity xác nhận.
