# MVP DENSO — báo cáo thực thi theo mốc tuần

> Đây là MVP phần mềm trên CWRU, không phải 12 tuần lịch đã trôi qua hoặc nghiệm thu tại DENSO.

## Kết luận

- Detector chọn **trước test**: `real_only`.
- Thay đổi recall so với real-only: **+0.00 điểm %**.
- Thay đổi recall so với simple tốt nhất trên dev: **+0.00 điểm %**.
- Gate utility mô tả (>=2 điểm % trên cả hai đối chứng; FPR<=5%): **False**.
- Bộ sinh release: constrained surrogate, local augmentation; không sinh cơ chế/RPM/severity chưa có.
- Không tái chọn phương pháp theo test. Không có CI theo vòng bi do chỉ một bản ghi/lớp/tải.

## Kết quả cuối — tải mới 3 HP

| Phương pháp | Recall lỗi | FPR khỏe | Accuracy 4 lớp | Macro-F1 |
|---|---|---|---|---|
| real_only | 100.00% | 4.52% | 99.72% | 99.72% |
| simple | 100.00% | 7.34% | 99.02% | 99.01% |
| constrained_surrogate | 100.00% | 20.90% | 99.86% | 99.86% |
| physics_unanchored | 100.00% | 23.16% | 99.58% | 99.58% |
| physics_anchored | 100.00% | 6.78% | 99.58% | 99.58% |
| physics_calibrated | 100.00% | 16.95% | 99.86% | 99.86% |
| ddpm_prototype | 100.00% | 6.78% | 100.00% | 100.00% |
| healthy_only | 98.31% | 23.73% | Không áp dụng | Không áp dụng |

Trung bình ba seed huấn luyện, không phải ba thí nghiệm máy độc lập. Threshold fit trên healthy 2 HP (59 windows), so sánh strict >. Không bảo đảm FPR thực địa hoặc exchangeability giữa tải.
Accuracy/F1 là argmax 4 lớp; recall/FPR là binary alarm threshold. Có thể classification đúng 100% nhưng alarm vẫn báo giả do threshold riêng — không đánh đồng hai endpoint.

### Recall alarm theo lỗi và dao động seed

| Method | Inner | Outer | Ball | Macro recall min–max seeds |
|---|---:|---:|---:|---|
| real_only | 100.00% | 100.00% | 100.00% | 100.00–100.00% |
| simple | 100.00% | 100.00% | 100.00% | 100.00–100.00% |
| constrained_surrogate | 100.00% | 100.00% | 100.00% | 100.00–100.00% |
| physics_unanchored | 100.00% | 100.00% | 100.00% | 100.00–100.00% |
| physics_anchored | 100.00% | 100.00% | 100.00% | 100.00–100.00% |
| physics_calibrated | 100.00% | 100.00% | 100.00% | 100.00–100.00% |
| ddpm_prototype | 100.00% | 100.00% | 100.00% | 100.00–100.00% |
| healthy_only | 100.00% | 100.00% | 94.92% | 94.92–100.00% |

### Hai vòng development (không dùng final chọn cấu hình)

| Variant | Mean recall | Mean F1 | Mean FPR | Eligible |
|---|---:|---:|---:|---|
| constrained_surrogate | 100.00% | 100.00% | 2.26% | True |
| constrained_surrogate_n256_w25 | 100.00% | 100.00% | 1.69% | True |
| constrained_surrogate_n256_w50 | 100.00% | 100.00% | 1.69% | True |
| constrained_surrogate_n32_w25 | 100.00% | 100.00% | 2.26% | True |
| constrained_surrogate_n32_w50 | 100.00% | 100.00% | 2.82% | True |
| ddpm_prototype | 100.00% | 100.00% | 2.82% | True |
| physics_anchored | 100.00% | 100.00% | 3.39% | True |
| physics_calibrated | 100.00% | 100.00% | 3.39% | True |
| physics_unanchored | 100.00% | 100.00% | 2.26% | True |
| real_only | 100.00% | 100.00% | 3.39% | True |
| simple | 100.00% | 100.00% | 2.26% | True |
| simple_n256_w25 | 100.00% | 100.00% | 2.82% | True |
| simple_n256_w50 | 100.00% | 100.00% | 2.26% | True |
| simple_n32_w25 | 100.00% | 100.00% | 2.26% | True |
| simple_n32_w50 | 100.00% | 100.00% | 2.26% | True |

Không chọn weight/count bằng test. Tất cả phương pháp cùng extractor/RF/real access; ngân sách fit physics/deep không compute-matched.

### Chi phí comparator (ba seeds)

| Method | Tổng giây ghi nhận | Ghi chú |
|---|---:|---|
| constrained_surrogate | 19.30 | fit + sample + feature/I/O; phụ thuộc máy |
| ddpm_prototype | 1599.32 | DDPM recovery: không bao gồm toàn bộ training/sampling bị gián đoạn; không so total compute |
| physics_anchored | 7.55 | fit + sample + feature/I/O; phụ thuộc máy |
| physics_calibrated | 21.49 | fit + sample + feature/I/O; phụ thuộc máy |
| physics_unanchored | 0.85 | fit + sample + feature/I/O; phụ thuộc máy |
| simple | 0.59 | fit + sample + feature/I/O; phụ thuộc máy |

Recovery minh bạch: GPU 4GB chậm mạnh; seed11/29 checkpoints train CUDA, seed47 train đủ budget CPU; sampling CPU thống nhất cả ba seeds trước freeze. Protocol amendments và interrupted artifacts giữ trong release. Cost table không bao gồm mọi attempts bị dừng.

## Review tuần

| Mốc | Trạng thái | Kết luận |
|---|---|---|
| 1 | PUBLIC_ONLY | Confirmed generation task; 17 legacy tests after CuBLAS repair; DENSO permissions/mentor pending. |
| 2 | PASS_WITH_LIMITS | Disjoint recording hashes; predeclared development budget; 3HP reserved. No independent bearings; healthy native fs=48k assumption. |
| 3 | PASS | Real-only/simple/surrogate and fixed-weight RF evaluated; baseline is not replaced by generator quality metrics. |
| 4 | RESEARCH_ONLY | Three legacy physics variants evaluated fresh; amplitude-unanchored is NOT healthy-only. No unseen-RPM/severity claim. |
| 5 | PASS_SCOPED | Audited shard writer with bounded attempts and fail-closed support. Hard-negative DENSO transitions unavailable. |
| 6 | PASS_SCOPED | DDPM trained anew, checkpoints saved; no claim of paper reproduction/convergence or equal compute. |
| 7 | PASS_SCOPED | Predeclared count/weight dose grid complete; count does not increase evidence independence. |
| 8 | GAP | Development selection complete; independent-bearing/PU evaluation not claimed. No data imported under assumed commercial permission. |
| 9 | GAP | Unknown faults/severity/DENSO target unvalidated. Reject unsupported conditions. Frozen candidates include all base methods for transparency. |
| 10 | UTILITY_NOT_ESTABLISHED | Final load opened once; gain vs real=0.0000, vs simple=0.0000. Do NOT retune on these outcomes. |
| 11 | PASS_OFFLINE | Sharded known-condition library fully audited; demo is read-only and not a factory pilot. |
| 12 | PASS_SOFTWARE_WITH_RESEARCH_GAPS | Both test suites passed; full library audited; 3 seeds x 3 labels x 2 repeats identical. No DENSO/independent-bearing sign-off. |

## Chất lượng dữ liệu sinh

| Lỗi | Accepted | Attempts | Unique | Corr max | Thời gian |
|---|---:|---:|---:|---:|---:|
| inner | 1000 | 1000 | 1000 | 0.95855 | 22.23s |
| outer | 1000 | 1000 | 1000 | 0.97637 | 23.75s |
| ball | 1000 | 1002 | 1000 | 0.95854 | 23.30s |

Mọi attempts có ledger; output là windows 2048 điểm, fs=12 kHz. Giữ histogram neo và tương quan cao: không gọi đó là hàng nghìn sự cố độc lập. Mọi hashes/quality/copy kiểm tra lại; raw waveform của rejected không lưu, hash/metadata/reason được lưu.

## Giới hạn bắt buộc

- Train: 0 HP; development: 1 HP; calibration: healthy 2 HP; final: 3 HP tải về sau protocol. Không random split windows. Các fault 2 HP cũ không dùng chọn mô hình trong run này.
- Tám fault windows/lớp từ một recording, 20 healthy windows. Native fs healthy=48 kHz là giả định công khai, resample anti-alias 48→12 kHz. Cần metadata gốc trước ứng dụng thật.
- CWRU lỗi nhân tạo 0.007 inch; khác tải chưa được xác nhận khác physical bearing. Chưa kiểm tra independent-bearing, real severity, unknown mechanisms, drift hay máy DENSO.
- Chưa có quyền commercial/redistribution CWRU. Không public raw/synthetic/checkpoints. Paderborn CC BY-NC 4.0 cần chốt mục đích/quyền trước gói thương mại.
- Physics/deep là original comparators; amplitude của physics_unanchored vẫn dùng faults. Không healthy-only physics, không TimeGAN/paper reproduction. DDPM clipping support lấy từ train.
- Không fuse detector A và C; C báo riêng. Mẫu sensor lỗi được giữ trong denominator; có sensor-alert rate riêng. Không giả abstention thành recall cao.
- Đạt sản phẩm chạy được không đồng nghĩa chứng minh augmentation có ích. Nếu gate fail, giữ kết quả âm; bước tiếp cần data mới chứ không tune lại final.

## Nguồn và tái lập

- CWRU: https://engineering.case.edu/bearingdatacenter/12k-drive-end-bearing-fault-data
- Healthy: https://engineering.case.edu/bearingdatacenter/normal-baseline-data
- PU license: https://mb.uni-paderborn.de/en/kat/research/bearing-datacenter
- Mã đề website A1 khác tên hồ sơ A2; vẫn bám anomaly generator + augmented data + before/after report.
- Artifacts: `C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007`.
- Hướng dẫn: `C:\Users\Ad\Downloads\DENSO\generator_benchmark\MVP_README.md`.
- `delivery_code` chứa bản chụp mã và hướng dẫn bàn giao; `code_snapshot` là mã tại protocol ban đầu.
- `acceptance/results.json`: tám black-box CLI cases, gồm generation/audit/replay, từ chối overwrite/fs/RPM và giữ invalid windows.
- Report HTML: `C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007\report.html`.
- Checkpoints pickle chỉ load local với hash trong freeze. Không load pickle từ bên không tin cậy.
- `integrity.json` là manifest kiểm tra thay đổi accidental, không chữ ký số hoặc chứng minh chống kẻ sửa cả file lẫn manifest.

## Kiểm tra phần mềm và thời gian suy luận

- 18 generator tests (17 cũ + explicit CPU regression) và 14 MVP tests; 8 CLI acceptance cases; 3 labels ×3 seeds ×2 lần stress generation; reload DDPM và so đúng 128 waveform đã lưu.
- Tính lại metrics từ prediction arrays; verify metadata/source/shard/ledger/anchor hashes và nghiệm thu HTML links/SVG.
- CPU feature+RF một cửa sổ, median **64.78 ms**, p95 **70.93 ms**, n=20 gồm warmup. Window duration **170.67 ms**. Không phải hard-realtime guarantee.
