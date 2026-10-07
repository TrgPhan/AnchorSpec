# Review kết quả lần chạy trước — 07/10/2026

## Kết luận quyết định

**Khả thi ở mức MVP phần mềm và demo nghiên cứu trên CWRU; chưa khả thi để pilot hoặc tuyên bố hiệu quả tại DENSO.**

| Phạm vi | Quyết định | Lý do chính |
|---|---|---|
| Chạy phần mềm, sinh dữ liệu, audit và replay | **GO** | Unit/integration test, CLI acceptance, checksum, replay và handoff validation đều đạt |
| Demo offline trên dữ liệu công khai CWRU | **GO có điều kiện** | Kết quả tái lập được nhưng chỉ đại diện đúng phạm vi dữ liệu đã thử |
| Dùng dữ liệu sinh để cải thiện detector | **NO-GO hiện tại** | Không tăng recall so với real-only/simple; FPR của các nhánh augmentation không đạt gate |
| Pilot trên máy DENSO | **NO-GO hiện tại** | Chưa có dữ liệu DENSO, chưa có kiểm định độc lập theo bearing/máy/thời gian và chưa đạt gate FPR mọi seed |

## Lần chạy trước thực sự cho kết quả gì?

Trạng thái release là `PASS_SOFTWARE_WITH_RESEARCH_GAPS`, không phải “PASS triển khai DENSO”.

- Release tạo **3.000 waveform accepted**: 1.000 mẫu cho mỗi lỗi `inner`, `outer`, `ball`; tổng 3.002 attempts, có 2 mẫu bị từ chối.
- Hai bộ test gốc đạt **32/32**: `test_generators.py` 18 test và `test_mvp.py` 14 test.
- Handoff validation đạt `PASS`: kiểm tra hash 484 file trước/sau, tính lại 24 dòng metric, reload ba DDPM checkpoint cho kết quả bitwise-identical, 8/8 CLI acceptance case đạt và UI/browser check đạt trong phạm vi đã ghi.
- Mô hình được chọn trước khi mở final test là **real-only**, không phải mô hình dùng dữ liệu sinh.

### Kết quả downstream chính

| Phương pháp | Accuracy | Recall lỗi | FPR trung bình | FPR seed xấu nhất | Nhận xét |
|---|---:|---:|---:|---:|---|
| real-only | 99,72% | 100% | 4,52% | 6,78% | Tốt nhất để giữ làm baseline; vẫn trượt gate FPR mọi seed |
| simple augmentation | 99,02% | 100% | 7,34% | 11,86% | Không cải thiện recall, FPR xấu hơn |
| constrained surrogate | 99,86% | 100% | 20,90% | 25,42% | Sinh dữ liệu ổn định nhưng utility downstream không đạt |
| physics anchored | 99,58% | 100% | 6,78% | 8,47% | Không đạt gate FPR |
| DDPM prototype | 100% | 100% | 6,78% | 10,17% | Accuracy đẹp nhưng alarm FPR vẫn không đạt |

Với `real-only`, FPR theo seed 11/29/47 lần lượt là **6,78% / 5,08% / 1,69%**. Hai trong ba seed vượt ngưỡng bắt buộc `≤5%`. Mức tăng recall của phương án được chọn so với real-only và simple đều là **0,00 điểm phần trăm**; vì vậy utility gate chính thức là `false`.

Mỗi seed chỉ có 59 cửa sổ healthy trong final test, nên một cảnh báo sai làm FPR đổi khoảng 1,69 điểm phần trăm. Seed 29 có 3/59 cảnh báo sai nên ra 5,08%; để đạt gate phải còn tối đa 2/59. Kích thước nhỏ và các cửa sổ tương quan khiến con số này chỉ có giá trị mô tả, chưa đủ để suy ra FPR ngoài hiện trường.

## Vì sao accuracy gần 100% vẫn chưa đủ?

Accuracy/F1 là bài toán phân loại bốn lớp, còn FPR là endpoint cảnh báo nhị phân theo threshold. Một phương án có thể phân loại rất tốt nhưng vẫn phát cảnh báo giả quá nhiều. DDPM là ví dụ rõ nhất: accuracy 100% nhưng FPR trung bình 6,78%, seed xấu nhất 10,17%.

Ngoài ra, tập thử gồm các cửa sổ có tương quan từ số recording hạn chế. Ba seed huấn luyện không phải ba bearing độc lập. Vì vậy không được coi 99–100% accuracy là ước lượng đáng tin cậy cho máy DENSO ngoài hiện trường.

## Điểm đã làm tốt

- Release có khóa hash, audit nguồn/provenance và từ chối overwrite, RPM hoặc sampling rate ngoài miền hỗ trợ.
- Có tách development/final và ghi lại quy tắc chọn trước test.
- Có giữ lại failed attempts, interrupted runs và giới hạn claim thay vì xóa dấu vết.
- Bộ sinh constrained surrogate tạo được dữ liệu hữu hạn, unique và qua quality/copy gate trong phạm vi CWRU đã thử.

## Khoảng trống quyết định tính khả thi

1. Không có dữ liệu rung từ DENSO và chưa xác nhận mã bài toán A1/A2 với mentor/BTC.
2. Chưa có split độc lập theo bearing/máy và thời gian; hiện chỉ biết các recording khác tải, không chứng minh là bearing khác nhau.
3. Chưa kiểm tra fault severity thực, unknown fault, drift, nhiễu nhà máy hoặc thay đổi cảm biến.
4. Synthetic augmentation chưa chứng minh đem lại lợi ích vận hành; một số nhánh làm FPR tăng mạnh.
5. Chưa có shadow test và xác nhận của kỹ sư hiện trường.

## Điều kiện để chuyển sang “khả thi pilot”

1. Xác nhận đề bài chính thức và quyền dùng dữ liệu DENSO.
2. Thiết kế split khóa theo asset/bearing và thời gian; tuyệt đối không chia các cửa sổ từ cùng recording sang train và test.
3. Chạy lại `real-only` làm baseline trên fresh locked test DENSO.
4. Chỉ giữ augmentation nếu đạt đồng thời: recall tăng ít nhất 2 điểm phần trăm so với real-only và simple, đồng thời FPR `≤5%` ở mọi seed theo protocol đã khóa.
5. Chạy shadow/offline trước; chưa nối vào điều khiển thiết bị. Kỹ sư DENSO xác nhận false alarm và incident thật trước khi đề xuất pilot.

## Bằng chứng gốc đã dùng

- `generator_benchmark/mvp_release_20261007/final/summary.json`
- `generator_benchmark/mvp_release_20261007/final/metrics.json`
- `generator_benchmark/mvp_release_20261007/validation/tests.json`
- `generator_benchmark/mvp_release_20261007/week_12.json`
- `generator_benchmark/mvp_release_20261007/acceptance/results.json`
- `generator_benchmark/handoff_validation_20261007/results.json`

Review này không chạy lại final experiment và không thay đổi release đã khóa; nó đối chiếu artifacts đã có, test logs và kết quả handoff validation.
