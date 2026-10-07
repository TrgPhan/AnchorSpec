# DENSO — chỉ mục dự án

Điểm bắt đầu nên đọc: [review kết quả lần chạy trước](docs/reviews/REVIEW_KET_QUA_LAN_CHAY_TRUOC.md). Kết luận ngắn: phần mềm và khả năng tái lập đã đạt; hiệu quả augmentation và khả năng triển khai tại DENSO chưa đạt.

## Cấu trúc thư mục

| Thư mục | Nội dung |
|---|---|
| `docs/handover/` | Bàn giao MVP, lệnh dùng và phạm vi cam kết |
| `docs/plans/` | Kế hoạch nghiên cứu tổng thể và kế hoạch 12 tuần |
| `docs/reviews/` | Biên bản rà soát, review implementation, review theo tuần và review mới nhất |
| `docs/results/` | Báo cáo kết quả thử nghiệm sinh dữ liệu |
| `docs/research/` | Tổng hợp nghiên cứu DENSO và các phương án |
| `inputs/a2/` | PDF đầu vào, bản text trích xuất và hình trang quan trọng |
| `research_evidence/` | Snapshot nguồn, manifest, kiểm chứng tài liệu và hình pipeline |
| `generator_benchmark/` | Mã nguồn, test, dữ liệu benchmark và toàn bộ artifacts của các lần chạy |

## Tài liệu chính

1. [Review kết quả lần chạy trước](docs/reviews/REVIEW_KET_QUA_LAN_CHAY_TRUOC.md)
2. [Bàn giao MVP](docs/handover/BAN_GIAO_MVP_DENSO.md)
3. [Hướng dẫn chạy MVP](generator_benchmark/MVP_README.md)
4. [Kế hoạch 12 tuần](docs/plans/KE_HOACH_NGHIEN_CUU_DENSO_A2_12_TUAN.md)
5. [Kết quả thử nghiệm sinh dữ liệu](docs/results/KET_QUA_THU_NGHIEM_SINH_DU_LIEU_A2.md)

## Kết quả chuẩn đang được bàn giao

- Release khóa: `generator_benchmark/mvp_release_20261007/`
- Kết quả cuối: `generator_benchmark/mvp_release_20261007/final/`
- Kiểm tra bàn giao độc lập: `generator_benchmark/handoff_validation_20261007/`
- Báo cáo HTML: `generator_benchmark/mvp_release_20261007/report.html`

Không sửa trực tiếp release đã khóa. Nếu chạy thử lại, dùng thư mục output mới để giữ nguyên bằng chứng lịch sử.

## Ghi chú về artifacts cũ

Các thư mục `results_*`, log và snapshot code bên trong `generator_benchmark/` là lịch sử thử nghiệm. Chúng được giữ nguyên tên và vị trí để không làm mất chuỗi bằng chứng hoặc phá các đường dẫn tái lập.
