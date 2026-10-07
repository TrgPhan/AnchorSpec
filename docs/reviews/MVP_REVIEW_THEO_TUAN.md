# Review thực thi MVP theo mốc tuần — 07/10/2026

## 1. Cách hiểu yêu cầu và điều kiện dừng

Giữ mục tiêu gốc: **bộ sinh dữ liệu lỗi → tập tăng cường có truy xuất → báo cáo so sánh trước/sau trên tín hiệu thật**, không thay thành chỉ detector, không chuyển sang RAG của mã A2 trên website. Mã đề chính thức vẫn cần BTC/mentor xác nhận; hồ sơ đội gọi A2 còn website gọi chủ đề này A1.

“Lặp đến khi đạt” được thực hiện bằng vòng **implement → chạy → review → sửa → kiểm thử lại**, nhưng có hai giới hạn không được đánh đổi:

1. Không lặp tuning trên final-test cho tới khi có số đẹp. Sau final, chỉ sửa packaging/UI hoặc lỗi code với disclosure; thí nghiệm mới cần test mới.
2. Không thể tự tạo ra quyền dữ liệu, xác nhận mentor, physical failures độc lập hay thời gian vận hành tại DENSO. Các gate đó vẫn GAP, dù MVP phần mềm hoạt động.

Mức hoàn thiện kỹ thuật và độ phức tạp mô hình là hai điều khác nhau. Một baseline tốt không được cố ý làm yếu để nhường thắng cho physics/DDPM.

## 2. Review điểm xuất phát và sửa lỗi

| Phát hiện | Hành động | Evidence |
|---|---|---|
| Context summary cũ không phản ánh toàn workspace | Kiểm kê và đọc lại implementation/review/12-week plan | Các tài liệu thực tế tồn tại trong workspace |
| DDPM direct test lỗi CuBLAS deterministic | Cấu hình trước CUDA tại module; rerun | 17 tests legacy pass; log mới trong release validation |
| Chưa có downstream detector evaluation | Thêm extractor không nhận ground-truth label, RF, IF, weight contract, metric/calibration | `C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_core.py` |
| CWRU test cũ đã xem nhiều lần | Giữ lịch sử; dành tải mới 3HP sau protocol/freeze | Records + FROZEN + final artifacts |
| Production chỉ có accepted provenance | Shards + attempt ledger cả rejected + fail-closed quota | Library/attempts.jsonl |
| Chưa có sản phẩm dễ bàn giao | CLI generation/audit/replay, offline HTML, source snapshots và hashes | MVP_README, report.html, integrity.json |
| Baseline dev chạm trần | Không ép gain; chạy grid đã đăng ký và giữ real-only khi hòa | Development metrics/selection |
| GPU 4GB sampling DDPM chậm mạnh | Dừng đúng process của lượt thí nghiệm trước freeze; giữ checkpoint và evidence, chuyển tất cả DDPM sampling sang CPU | Protocol recovery amendment, interrupted_gpu_sampling, recovery logs; không chọn theo test |

## 3. Mapping từng tuần

| Tuần | Việc thực thi | Điều không được tự nhận hoàn tất |
|---|---|---|
| 1 | Kiểm kê, legacy tests, đề bài, raw hashes | Mentor sign-off và DENSO permissions |
| 2 | Protocol, role allowlist, recording split, tải mới 3HP | Independent-bearing split và healthy native fs đã xác minh |
| 3 | RF real-only, simple/surrogate, metrics/tests | Accuracy đẹp là bằng chứng augmentation giúp |
| 4 | Fresh legacy physics downstream + diagnostics | Healthy-only theoretical physics, posterior/identifiability đầy đủ |
| 5 | Sharded writer, gate, rejection ledger, anti-copy và fail-closed | Resume/streaming audit vô hạn hoặc hard negatives DENSO |
| 6 | Fresh DDPM 1500 steps×3 seeds + saved states | Paper reproduction/hội tụ/equal-compute |
| 7 | Vòng dose/weight development và library quota 1000/lớp | Tăng count tăng số incidents độc lập |
| 8 | Review shift/generalization gaps, chọn trên dev | Independent-bearing/PU results chưa chạy |
| 9 | Khóa candidate/config; unsupported-domain rejection | Unknown/severity/field validation |
| 10 | Separate healthy calibration và final 3HP sau freeze | Window-level kết quả là plant-level efficacy |
| 11 | Read-only offline report/replay, source/data cards trong README | Pilot trên máy hoặc kết nối PLC |
| 12 | Unit/integration/CLI/stress/corruption/hash verification | Independent expert/mentor acceptance |

Chi tiết tự động theo từng tuần ở `C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007\week_01.json` đến `C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007\week_12.json`. File nào chưa có thì mốc đó chưa được xác nhận, không suy từ bảng kế hoạch.

## 4. Vòng cải tiến được cho phép

- **Vòng sửa kỹ thuật:** test legacy fail → sửa CuBLAS → rerun pass.
- **Vòng development 1:** 7 methods×3 seeds, cùng real access và RF; raw synthetic không bị anti-copy gate làm lệch đối chứng simple.
- **Review:** task gần trần; W1/quality không chứng minh ích lợi detector. Không chọn theo test.
- **Vòng development 2:** counts 32/256 × synthetic class mass .25/.5 cho simple/surrogate; chạy theo protocol định trước, không thêm endless trials.
- **Freeze:** chọn trên dev, healthy calibration tách biệt; final không tái tune.
- **Vòng hoàn thiện release:** full-row quality/hash/copy audit, repeat seeds, black-box CLI, invalid input/domain/overwrite checks và offline report.

Không tự bảo đảm giả thuyết khoa học sẽ dương. Nếu cuối cùng real-only vẫn tốt nhất/hòa hoặc FPR không đạt, sản phẩm vẫn có thể bàn giao nhưng **nghiên cứu augmentation chưa chứng minh thành công**. Cách nâng bằng chứng là thêm independent bearings/healthy exposure/dữ liệu DENSO được phép, không thay target hoặc loại samples khó sau khi xem test.

## 5. Đường dẫn kết quả

- Hướng dẫn chạy: `C:\Users\Ad\Downloads\DENSO\generator_benchmark\MVP_README.md`.
- Báo cáo số liệu cuối (chỉ tạo sau final + tests): `C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007\REPORT.md`.
- Giao diện offline: `C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007\report.html`.
- Final metrics gốc: `C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007\final\metrics.json`.
- Acceptance: `C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007\acceptance\results.json`.
- Full integrity manifest: `C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007\integrity.json`.

## 6. Nguồn đối chiếu lại

- https://engineering.case.edu/bearingdatacenter/12k-drive-end-bearing-fault-data — bảng 0.007 inch/3HP, href mapping kiểm tra trực tiếp bằng HTML parser.
- https://engineering.case.edu/bearingdatacenter/normal-baseline-data — Normal_3; không khẳng định page cung cấp native fs từng record.
- https://mb.uni-paderborn.de/en/kat/research/bearing-datacenter — CC BY-NC 4.0, commercial phải liên hệ.
- https://groups.uni-paderborn.de/kat/BearingDataCenter/ — archives hiện truy cập được, khoảng 150–178 MB/bearing. Không nói bị chặn kỹ thuật khi thật ra chưa chọn ingest.

Nghiên cứu DENSO/papers trước đây giữ trong `C:\Users\Ad\Downloads\DENSO\docs\research\NGHIEN_CUU_CONG_BO_DENSO_VA_PHUONG_AN.md`; lượt này ưu tiên triển khai/kiểm thử, không tự nhận đã tìm hết mọi công bố mới.

## 7. Kết luận sau khi completion worker kết thúc

Đã kiểm tra lại tiến trình và `C:\Users\Ad\Downloads\DENSO\generator_benchmark\completion_cpu_stdout.log`: worker hoàn tất final/report/acceptance, không cần khởi chạy lại develop/finalize. `C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_release_20261007\week_12.json` xác nhận **PASS_SOFTWARE_WITH_RESEARCH_GAPS**. Đây là hoàn tất mốc công việc trong phạm vi public-data MVP, không phải đã trôi qua 12 tuần hay đã có nghiệm thu DENSO.

- **Mốc 10 không đạt utility:** real-only chọn trước test; accuracy 99,72%, recall alarm 100%; FPR trung bình 4,52% nhưng seeds 11/29/47 tương ứng 6,78% / 5,08% / 1,69%. Hai trong ba seeds vượt 5%. Không dùng trung bình để che gate fail.
- **Augmentation chưa có lợi ích vận hành:** surrogate recall 100%, FPR 20,90%; DDPM accuracy 100%, recall alarm 100%, FPR 6,78%. Classification và alarm là hai endpoint khác nhau. Δrecall candidate chọn trước test so real/simple = 0,00 điểm %.
- **Mốc 11 đủ quota:** 1.000 inner +1.000 outer +1.000 ball, từ 3.002 attempts; hai rejected của ball được lưu hash/metadata/reason, không lén thay bằng copy. Correlation tối đa với neo của toàn thư viện là 0,97637; không đồng nghĩa có thêm 3.000 incidents độc lập.
- **Mốc 12:** 18 generator tests +14 MVP tests chạy lại đạt; tám CLI cases đã đạt trong release; stress lặp 3 seeds ×3 labels ×2 lần giống nhau. 484 files khớp manifest, mã Python gốc hiện tại khớp bản chụp delivery. Bốn tests an toàn mới cho validator bổ sung cũng đạt, tách khỏi con số 32 tests gốc.
- **Recovery thực tế:** seeds11/29 train CUDA; seed47 train đủ 1.500 bước trên CPU sau khi CUDA training/prefit bị dừng trước checkpoint. Sampling cả ba trên CPU; giữ archives GPU bị gián đoạn, không trộn batches. Cost không gồm đủ mọi interrupted attempts, không dùng kết luận compute-matched.

Không sửa artifacts/thresholds/checkpoints/report trong release đã khóa. Công cụ kiểm tra bổ sung `C:\Users\Ad\Downloads\DENSO\generator_benchmark\mvp_handoff_check.py` ghi kết quả vào thư mục mới bên ngoài release, kiểm tra DDPM reload cả ba seeds, metrics từ predictions, UI desktop/mobile và tính bất biến manifest. Evidence bàn giao: `C:\Users\Ad\Downloads\DENSO\generator_benchmark\handoff_validation_20261007\results.json`; chỉ đọc `status=PASS` khi tiến trình kết thúc, không suy từ sự tồn tại của thư mục.

**Đã xác nhận PASS sau kết thúc:** cả ba DDPM checkpoints tái tạo bitwise đúng batch128 inner/seed trên CPU; 24 metric rows và summary khớp; UI đổi ba labels/mở provenance hoạt động; manifest 484 files giữ nguyên. Kiểm tra iframe ở innerWidth390/1440 không tràn trang, bảng hẹp cuộn riêng. Ảnh Chrome cửa sổ hẹp trực tiếp bị crop không được dùng thay bằng chứng layout; log harness đầu tính nhầm scrollbar được giữ và sửa trong `C:\Users\Ad\Downloads\DENSO\generator_benchmark\handoff_validation_20261007\layout_verified.json`. Bản tổng hợp bàn giao: `C:\Users\Ad\Downloads\DENSO\docs\handover\BAN_GIAO_MVP_DENSO.md`.

**Bước tiếp theo không phải tối ưu lại final 3 HP:** cần xác nhận mã đề A1/A2 với DENSO, quyền/metadata/units, bearings hoặc components độc lập và healthy exposure dài. Đăng ký trước development/calibration/fresh-holdout mới; giữ ngân sách neo thật bằng nhau và tách unknown mechanism khỏi operating-context shift. Public-data MVP chưa chứng minh early failure, RUL, severity thật, downtime hoặc deployment readiness.
