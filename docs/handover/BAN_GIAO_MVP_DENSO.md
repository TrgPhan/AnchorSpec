# Bàn giao MVP sinh dữ liệu lỗi DENSO — 07/10/2026

## 1. Kết luận để ra quyết định

**Bàn giao được MVP phần mềm offline; chưa đạt nghiệm thu vận hành và chưa chứng minh augmentation hữu ích.** Sản phẩm gồm bộ sinh waveform, thư viện có truy xuất nguồn, kiểm toán, detector/replay và báo cáo trước/sau trên tín hiệu thật. Không đổi mục tiêu thành chỉ detector và không đổi sang đề thu nhận tri thức chuyên gia.

- Generator release: **constrained surrogate**, chỉ biến thể cục bộ từ neo đã quan sát.
- Detector được chọn **trước test**: **real-only**. Không chọn lại theo bảng final.
- Thư viện: **3.000 windows** = 1.000 inner +1.000 outer +1.000 ball; 12 kHz, 2.048 điểm/window (~170,67 ms), float32. Không ghép thành waveform liên tục hoặc gọi là 3.000 incidents độc lập.
- **Gate chưa đạt:** FPR phải ≤5% ở mọi seed; real-only có seed xấu nhất 6,78%. Δrecall so real/simple = 0,00 điểm %, không đạt mục tiêu +2 điểm %.
- Chưa có dữ liệu/quyền/sign-off DENSO; PDF gọi A2 nhưng chủ đề predictive maintenance trên website là A1, cần mentor/BTC xác nhận.

## 2. Kết quả final đã khóa

| Phương pháp | Accuracy 4 lớp | Recall alarm | FPR trung bình | FPR seed xấu nhất |
|---|---:|---:|---:|---:|
| Real-only | 99,72% | 100,00% | 4,52% | **6,78%** |
| Simple | 99,02% | 100,00% | 7,34% | 11,86% |
| Surrogate | 99,86% | 100,00% | 20,90% | 25,42% |
| Physics unanchored | 99,58% | 100,00% | 23,16% | 33,90% |
| Physics anchored | 99,58% | 100,00% | 6,78% | 8,47% |
| Physics calibrated | 99,86% | 100,00% | 16,95% | 25,42% |
| DDPM prototype | 100,00% | 100,00% | 6,78% | 10,17% |
| Healthy-only IF | Không áp dụng | 98,31% | 23,73% | 25,42% |

Accuracy/F1 là argmax 4 lớp, recall/FPR là binary alarm threshold: **accuracy 100% không có nghĩa FPR=0**. Các giá trị accuracy/F1 máy tính vẫn tồn tại cho IF trong JSON legacy nhưng không có ý nghĩa chẩn đoán 4 lớp; báo cáo phải ghi “không áp dụng”.

Train 0 HP (8 windows/lỗi, 20 healthy), development 1 HP, calibration healthy 2 HP sau freeze, final 3 HP. Final có 237 windows từ bốn recordings (59 healthy, 178 fault); ba seeds là biến thiên training, không phải ba tập máy độc lập. Không có bearing-level CI hợp lệ. FPR real-only theo seeds 11/29/47: 4/59, 3/59, 1/59; 2/3 seeds vượt 5%.

Nguồn số liệu gốc: `C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007\final\summary.json`.

## 3. Mở và sử dụng ngay

Chạy PowerShell trong môi trường Python hiện có; đường dẫn đều tuyệt đối, không phụ thuộc thư mục hiện hành.

```powershell
Start-Process 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007\report.html'
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_cli.py' verify --release 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007'

python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_cli.py' generate --release 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007' --label inner --count 1000 --seed 9002 --output 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\handoff_demo_inner'
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_cli.py' audit --release 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007' --label inner --output 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\handoff_demo_inner'
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_cli.py' replay --release 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007' --input 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\handoff_demo_inner\shard_00000.npy' --fs 12000 --rpm 1797 --output 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\handoff_demo_replay.json'
```

Thư mục generation và tệp replay phải mới; lệnh chủ động từ chối overwrite. Replay ở đây minh họa luồng dữ liệu synthetic, **không phải đánh giá hiệu quả trên dữ liệu thật mới**. Chỉ dùng dữ liệu CWRU/geometry/fs đã mô tả; không ngầm chuyển sang máy DENSO. Generation không hỗ trợ yêu cầu RPM mới. Replay trả sensor-quality failure cho constant/nonfinite windows, không bỏ rows khó khỏi denominator.

Môi trường đã chạy: Windows 11, Python 3.12.10, NumPy 2.4.4, SciPy 1.17.1, scikit-learn 1.8.0; PyTorch 2.7.1+cu118 cho deep comparator/tests. Production surrogate/CLI không cần GPU. Không tự thay CUDA build trong môi trường đang chạy. Phiên bản requirements: `C:\Users\Ad\Downloads\DENSO\generator_benchmark\requirements_mvp.txt`.

## 4. Kiểm thử và bằng chứng

```powershell
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\test_generators.py'
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\test_mvp.py'
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\test_handoff_check.py'
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_handoff_check.py' --release 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007' --output 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\handoff_revalidation_new'
```

- **18/18 generator +14/14 MVP tests đạt**, chạy lại và lưu exit code riêng. **4/4 tests mới** kiểm tra validator từ chối ghi vào release/overwrite, giữ failure evidence và không sửa dữ liệu khi hash sai.
- **8/8 CLI acceptance cases** đã chạy trong release: generate, audit, replay, từ chối overwrite/fs/RPM; giữ invalid windows. Validator mới kiểm tra evidence này, không tự nhận đã chạy thêm tám lần.
- Full library audit: 3.000 accepted unique **trong từng lớp**, 3.002 attempts, 2 rejected; hashes/metadata/source/anchor/shard/quality đã đối chiếu. Không tuyên bố near-duplicate synthetic–synthetic được kiểm toán đầy đủ.
- Stress release: 3 labels ×3 seeds ×2 repeats, mỗi batch16, hashes lặp giống nhau.
- Manifest gốc: **484 files** khớp hash; không phải chữ ký số. Tệp nguồn Python đã bàn giao khớp bản chụp trong release.

**Kiểm tra bàn giao bổ sung đã kết thúc: PASS.** Nguồn xác nhận: `C:\Users\Ad\Downloads\DENSO\generator_benchmark\handoff_validation_20261007\results.json`.

- Reload **cả ba DDPM checkpoints seeds11/29/47**, mỗi checkpoint tái tạo **128 inner windows** từ seed gốc, sampling CPU: **bitwise identical**. Không mở rộng phát biểu này thành mọi label/device hoặc retraining.
- **24 metric rows** tính lại từ predictions khớp, mean và worst-seed summary khớp; selection khớp freeze. Không chỉnh threshold hoặc thay model.
- Headless Chrome: đổi inner/outer/ball, mở provenance, đủ 12 SVG/12 mốc review/8 methods, 5 local links hợp lệ. Desktop screenshot đã xem: `C:\Users\Ad\Downloads\DENSO\generator_benchmark\handoff_validation_20261007\report_desktop.png`.
- Ảnh dùng trực tiếp `--window-size=390,1100` bị cắt, không dùng nó chứng nhận responsive. Kiểm tra độc lập iframe **innerWidth=390 và 1440** xác nhận **không tràn ngang trang**; bảng trên 390px có thanh cuộn ngang cục bộ. Evidence: `C:\Users\Ad\Downloads\DENSO\generator_benchmark\handoff_validation_20261007\layout_verified.json` và `C:\Users\Ad\Downloads\DENSO\generator_benchmark\handoff_validation_20261007\report_390px_iframe.png`. Harness đầu so nhầm clientWidth (trừ scrollbar) với innerWidth; giữ log FAIL ban đầu và log sửa kiểm tra riêng, không sửa report.
- Verify trước/sau và lượt verify cuối cùng vẫn **484/484**, `locked_release_unchanged=true`; không còn worker kiểm tra. Đây không phải certification accessibility hoặc thử trên điện thoại thật.

Log gốc nằm tại `C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007\validation`; tám CLI cases tại `C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007\acceptance\results.json`. Validator bổ sung ghi riêng vào `C:\Users\Ad\Downloads\DENSO\generator_benchmark\handoff_validation_20261007`, không sửa release đã khóa.

## 5. Recovery, tái lập và bảo toàn kết quả

- GPU RTX A1000 4GB sampling chậm mạnh; các lượt sampling gián đoạn được lưu riêng. Seeds11/29 train CUDA; seed47 CUDA/prefit dừng trước checkpoint, sau đó **train đủ 1.500 bước trên CPU**. Sampling cuối cả ba seeds dùng CPU; không trộn kết quả GPU bị gián đoạn.
- Reload checkpoint cùng môi trường/device khác với retraining. Không hứa fresh all-CPU training bitwise giống mixed-device release. Không gọi prototype là paper reproduction/hội tụ.
- Runtime comparator không gồm đầy đủ attempts GPU bị dừng, nên không so total compute công bằng.
- **Không chạy lại finalize/report vào release cũ.** Hướng dẫn reproduction ra output mới nằm trong `C:\Users\Ad\Downloads\DENSO\generator_benchmark\MVP_README.md`. Chuỗi prepare/develop/finalize/report là reproduction của tập đã biết, không một confirmatory test mới.
- Manifests/checkpoints chứa absolute paths của máy này; copy thư mục sang máy khác không bảo đảm chạy ngay. Chuyển máy cần raw inputs được cấp quyền và run mới. Chỉ load local trusted pickle sau verify, không load checkpoint uploads từ người lạ.

## 6. Tài liệu chính và khoảng trống còn lại

| Tài liệu/artifact | Đường dẫn |
|---|---|
| Hướng dẫn kỹ thuật và commands đầy đủ | `C:\Users\Ad\Downloads\DENSO\generator_benchmark\MVP_README.md` |
| Report kết quả đã khóa | `C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007\REPORT.md` |
| UI offline | `C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007\report.html` |
| Thư viện waveform | `C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007\library` |
| Review từng mốc | `C:\Users\Ad\Downloads\DENSO\docs\reviews\MVP_REVIEW_THEO_TUAN.md` |
| Kế hoạch 12 tuần, kết quả thực thi mục 13.6 | `C:\Users\Ad\Downloads\DENSO\docs\plans\KE_HOACH_NGHIEN_CUU_DENSO_A2_12_TUAN.md` |

Các “tuần” là work packages rút gọn, không thời gian vận hành đã tích lũy. Chưa có independent bearings, unknown mechanisms, severity thật, onset/RUL, long healthy exposure, field pilot hay downtime benefit. Native fs healthy=48 kHz vẫn là working assumption cần metadata chính thức. Thư viện có correlation cao với neo, chỉ support hẹp; engineering gate không chứng nhận nhãn lỗi bằng cơ khí. Không public raw/derived/checkpoints khi quyền commercial/redistribution chưa chốt.

**Vòng tiếp theo:** xác nhận mã đề/quyền/metadata với DENSO; đăng ký protocol mới với development mới, calibration healthy riêng và fresh independent holdout. Giữ ngang ngân sách neo thật giữa anchored/unanchored; tách unknown faults khỏi operating-context shift. Không tune threshold hoặc đổi winner dựa trên final 3 HP đã công bố.
