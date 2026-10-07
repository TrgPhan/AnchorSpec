# MVP — bộ sinh waveform + kiểm toán + báo cáo trước/sau

**Root:** `C:\Users\Ad\Downloads\DENSO\generator_benchmark`  
**Release:** `C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007`

## Kết quả bàn giao đã khóa — 07/10/2026

**PASS phần mềm trong phạm vi offline; KHÔNG đạt gate vận hành/utility.** Real-only được chọn trên development trước test và vẫn là detector replay; thư viện release dùng constrained surrogate, không phải DDPM và không phải bằng chứng surrogate cải thiện detector.

| Phương pháp | Accuracy 4 lớp | Recall alarm | FPR trung bình | FPR seed xấu nhất |
|---|---:|---:|---:|---:|
| Real-only | 99,72% | 100% | 4,52% | **6,78%** |
| Simple | 99,02% | 100% | 7,34% | 11,86% |
| Surrogate | 99,86% | 100% | 20,90% | 25,42% |
| DDPM | 100% | 100% | 6,78% | 10,17% |

Không đánh đồng accuracy argmax với alarm threshold. Gate yêu cầu FPR≤5% **mọi seed**, không chỉ trung bình. Chưa có bằng chứng augmentation cải thiện mục tiêu vận hành; không đổi threshold/winner dựa trên final đã xem. Chi tiết đủ tám phương pháp trong `C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007\REPORT.md`.

Thư viện **3.000 windows** (1.000/lỗi), 3.002 attempts; 2 rejected có ledger. Release đã có 18 generator tests +14 MVP tests, 8 black-box CLI cases đạt; stress 3 labels ×3 seeds ×2 repeats giống nhau; DDPM seed11 reload tái tạo đúng 128 inner windows. Manifest kiểm chứng 484 files. Số này là phần mềm/public benchmark, không chứng nhận vật lý hay triển khai DENSO.

## 1. Phạm vi nghiệm thu

MVP phần mềm offline cho **CWRU drive-end SKF6205, 12 kHz, 2048 samples/window**, healthy/inner/outer/ball. Không nhận mặc định dữ liệu DENSO với geometry/fs/units khác. Sinh dữ liệu, provenance, manifest, ledger rejected, classifier trước/sau, healthy-only reference, hiệu chuẩn ngưỡng riêng, báo cáo và replay. Không gửi dữ liệu lên dịch vụ, không PLC/điều khiển máy.

Các “week” là **mốc thực thi rút gọn theo kế hoạch 12 tuần**, không giả đã trải qua 12 tuần hoặc có sign-off mentor. Utility của augmentation là giả thuyết có thể sai; tham khảo kết quả thật, không chỉ việc code chạy.

## 2. Mở kết quả

```powershell
Start-Process 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007\report.html'
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_cli.py' verify --release 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007'
```

Report là HTML tự chứa, xem offline không CDN/server. Có bảng trước/sau, tín hiệu neo/synthetic, PSD/envelope, provenance và review từng mốc. Không gọi giao diện này là phần mềm điều khiển hoặc pilot tại nhà máy.

## 3. Sinh batch mới và audit

```powershell
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_cli.py' generate --release 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007' --label inner --count 1000 --seed 9002 --output 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\my_inner_batch'
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_cli.py' audit --release 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007' --label inner --output 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\my_inner_batch'
```

Output directory phải mới. Ba label: `inner`, `outer`, `ball`. Chỉ sinh trong điều kiện neo; `--rpm` cho generation bị từ chối. Lệnh luôn lưu:

- `config.json`: code/input hashes, seed, config và giới hạn.
- `shard_*.npy`: float32, tối đa 128 windows/shard; không ghép thành chuỗi liên tục.
- `attempts.jsonl`: mọi accepted/rejected attempt; có metadata nguồn, hash, reason, shard/row.
- `audit.json`: attempts/rejections/runtime; `manifest.json` chỉ xuất khi đủ quota.
- `FAILED.json`: quota thất bại; không silently fallback về copy neo.

Generation bounded-memory theo batch. Full audit hiện nạp thư viện vào RAM; quota 1000/lớp nhỏ (~8.2 MB/lớp). Không hứa audit streaming hàng tỷ rows. Không resume; dùng run mới thay vì append không kiểm soát.

Gate dùng train RMS/crest/envelope, corr cyclic với mọi neo ≤0.99, exact uniqueness. Đây là engineering screen, **không chứng nhận nhãn lỗi bằng cơ khí**. Surrogate giữ histogram nguồn, support hẹp. Bound pha áp intermediate, không exact ở output cuối.

## 4. Replay waveform đã chuẩn bị

```powershell
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_cli.py' replay --release 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007' --input 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\my_inner_batch\shard_00000.npy' --fs 12000 --rpm 1797 --output 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\my_replay.json'
```

Replay dùng seed 11 của detector đã chọn trước test; bảng report lấy trung bình 3 seed. Input `.npy` không pickle, shape `(n,2048)`, người dùng xác nhận CWRU. Không thể tự xác minh dataset qua waveform; đừng đưa DENSO hoặc dữ liệu khác vào rồi diễn giải như đã được hỗ trợ. RPM ngoài 1720–1810 hoặc fs khác 12k bị từ chối. Trong dải này chỉ là sanity range của benchmark, không chứng minh mọi operating condition.

Trả `sensor_quality_failure`, `known_fault_alarm`, `no_alarm`; mechanism là hypothesis, không known-unknown classifier, không severity/RUL. Constant/nonfinite windows không được coi như healthy. Probability RF chưa được calibration thành xác suất lỗi thực tế. Gate threshold là strict `>`.

## 5. Chạy kiểm thử

```powershell
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\test_generators.py'
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\test_mvp.py'
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\test_handoff_check.py'
```

NumPy/SciPy/scikit-learn đã có trong môi trường; PyTorch 2.7.1+cu118 và GPU dùng cho DDPM. Không tự thay CUDA build. Phiên bản runtime lưu trong release. NumPy/SciPy path và RF không cần GPU; DDPM optional cho production CLI nhưng cần nếu chạy toàn bộ experiment hoặc legacy test.

### Kiểm tra lại release mà không ghi đè

```powershell
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_handoff_check.py' --release 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007' --output 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\handoff_check_repeat'
```

Output phải mới và **nằm ngoài release**. Công cụ chạy lại hai test suites gốc, full-row library audit, reload DDPM cả ba checkpoints (128 inner windows/seed trên CPU), tính lại 24 metric rows từ predictions và kiểm tra mean/worst-seed trong summary, verify hash trước/sau. Không train model, không fit threshold và không mở lại raw final để tuning. Tám CLI acceptance cases được đối chiếu từ evidence đã khóa, không được mô tả là tám lượt mới của lệnh này.

Nếu Chrome tại đường dẫn đã dùng trong release có sẵn, công cụ render desktop/mobile và kiểm tra đổi ba labels, mở provenance, 12 mốc review và 8 dòng methods. Không có Chrome thì ghi SKIPPED rõ ràng; không coi đó là browser PASS. Bằng chứng lượt bàn giao nằm ngoài release tại `C:\Users\Ad\Downloads\DENSO\generator_benchmark\handoff_validation_20261007`. Bản chụp `C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007\delivery_code` giữ nguyên lịch sử; validator/hướng dẫn bổ sung không được chèn vào manifest cũ.

**Lượt bàn giao đã PASS:** checkpoint seeds11/29/47 tái tạo đúng batch128 inner/seed; 24 metric rows khớp; original release không đổi. Chrome interaction PASS không tự chứng nhận responsive: ảnh cửa sổ hẹp trực tiếp bị crop. Kiểm tra iframe riêng xác nhận innerWidth390/1440 không tràn trang, bảng hẹp cuộn cục bộ; xem `C:\Users\Ad\Downloads\DENSO\generator_benchmark\handoff_validation_20261007\layout_verified.json`. Tổng hợp commands/evidence/limitations: `C:\Users\Ad\Downloads\DENSO\docs\handover\BAN_GIAO_MVP_DENSO.md`.

## 6. Tái chạy nghiên cứu với output mới

```powershell
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_run.py' prepare --output 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_reproduction' --deep-steps 1500 --quota 1000
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_run.py' develop --output 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_reproduction'
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_run.py' finalize --output 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_reproduction'
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_run.py' report --output 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_reproduction'
```

Prepare cần mạng để đối chiếu links/tải 3HP; 12 bản ghi cũ theo `C:\Users\Ad\Downloads\DENSO\generator_benchmark\data_manifest.json` phải tồn tại và đúng hash. Các stage còn lại offline. Paths trong manifests/checkpoints là absolute cho máy này: khi chuyển máy, tạo run mới trên raw inputs đã cấp quyền; không hứa package arbitrary relocation bằng copy thư mục.

Tái chạy test đã biết là **reproduction**, không phải fresh confirmatory experiment. Không thay parameters rồi gọi 3HP là “unseen” lần nữa. Muốn nghiên cứu vòng tiếp theo cần dataset/test mới.

**Recovery được ghi nhận trong release này:** tiến trình GPU sampling chậm mạnh trên RTX A1000 4GB đã dừng trước freeze/final; checkpoints CUDA seed11/29 được giữ, seed47 huấn luyện tiếp cùng budget. Sampling DDPM cả ba seeds chạy CPU thống nhất. `interrupted_gpu_sampling` lưu metrics/arrays bị thay và protocol cũ; `protocol.json/recovery_amendment` ghi lý do. `--resume-development` chỉ phục hồi điểm đã hoàn tất tất cả base non-DDPM, chưa grid/freeze/final; không phải resume tổng quát hay production-resume. CPU/GPU seed bitwise khác không được hứa giống nhau. Cost sau recovery không bao gồm đầy đủ thời gian GPU sampling bị gián đoạn; xem logs/timestamps, không dùng làm phép so sánh total compute công bằng.

Một thử nghiệm worker `mvp_prefit.py` nhằm overlap CUDA training seed47 với CPU sampling cũng đã dừng **trước khi xuất checkpoint**, vì không hoàn tất trước khi main worker tới seed47. Main worker tự train seed47; không ghép weights của hai workers. Prefit logs rỗng không là bằng chứng train hoàn tất. Worker này là tiện ích optional, không dùng trong lệnh tái chạy chuẩn ở trên.

**Recovery lần hai:** main CUDA training seed47 vẫn chậm quá mức, dừng trước checkpoint/freeze. Hai kết quả DDPM CPU seed11/29 được giữ; seed47 train lại đủ 1500 bước trên CPU có progress log. Amendment `cpu_training_recovery` và `interrupted_gpu_training` giữ bằng chứng. Fresh-run hiện mặc định CPU cho DDPM training/sampling; do seed11/29 release này đã train CUDA, chỉ hứa seed reproducibility trong cùng môi trường/device, không hứa fresh all-CPU run bitwise giống mixed-device release. Những GPU attempts bị dừng không tính là hoàn tất training.

## 7. Giao thức đã khóa

- Train 0HP: 8 windows/fault class, 20 healthy; cùng real access cho mọi method.
- Dev 1HP: 7 base methods ×3 seeds; vòng hai chỉ simple/surrogate với counts 32/256, synthetic class mass .25/.5. Base 128, mass .5. RF 200 trees, bootstrap=False, cùng cấu hình.
- Trọng số mỗi class tổng=1; khi augmentation, real/synthetic chia theo mass. Không để tăng count vô tình tăng prior lớp lỗi.
- Comparator dùng **raw finite synthetic** với quota cố định; không anti-copy filter gây bất lợi cho simple. Production library là quality-filtered surrogate riêng. Không tuyên bố downstream của raw batch chính là hiệu quả accepted release library.
- Selection: recall rồi F1; FPR dev ≤5% từng seed, real-only nếu hòa. Dev healthy dùng threshold để chọn, không là final calibration.
- Freeze `FROZEN.json`; healthy 2HP chỉ fit threshold cuối; final 3HP không dùng tuning. Tất cả base methods báo cuối để minh bạch, không chọn lại winner.
- IF healthy-only C báo riêng, **không fusion**. Classification accuracy/F1 của C không áp dụng.
- Primary gate mô tả: +2 điểm % macro fault recall so real và simple, FPR≤5% mọi seed. Đây là engineering criterion do dự án đặt, không yêu cầu chính thức DENSO.

## 8. Giới hạn, quyền và bàn giao

Chưa đủ independent-bearing, DENSO permissions, unknown faults, true severity, long healthy exposure, downtime benefit. Healthy native fs=48k là assumption còn thiếu metadata chính thức. Không có bearing-level CI; 59 windows cùng recording là correlated.

CWRU public download không tự cho phép commercial/redistribution. Không public raw/derived/checkpoints chưa chốt quyền. PU có CC BY-NC 4.0; thương mại cần liên hệ tác giả. Prototype này không cấp giấy phép thay chủ dữ liệu.

Pickle chỉ là local trusted checkpoints, được verify hash trước load; không load uploads/checkpoints từ người lạ. Integrity manifest không phải chữ ký số. Không tự cập nhật model sau khi có kết quả test.
