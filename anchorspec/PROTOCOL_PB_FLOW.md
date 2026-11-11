# PB-Flow: kiểm chứng Flow S3 trên Paderborn hỏng thật

Ghi ngày 12/11/2026 lúc 00:40, **trước khi chạy và trước khi đọc bất kỳ kết quả Flow nào trên Paderborn**.

Cấu hình được khóa từ phân tích kiểm tra lại trên XJTU và UORED (`KET_QUA_S3_LIEU_SINH_20261111.md`, mục 11.5). Paderborn đã dùng ở TN2 và X3 với lỗi cấy, nhưng **chưa từng chạy Flow**, và **không dùng để chọn cấu hình này**.

## Dữ liệu

- Paderborn, điều kiện N15_M07_F10, cache `data/paderborn/cache` (20 bản ghi × 4 s, 64 kHz). Cảm biến giả lập như TN2: `CheapSensor()` 4 kHz, 1 kHz, ±8 g; đơn vị giả định m/s² rồi chia 9,81; tốc độ danh định 25 Hz; cửa sổ 1 s không chồng lấn (80 cửa sổ mỗi ổ). Nhiễu cảm biến có hạt giống cố định theo mã ổ, nên dữ liệu không đổi theo seed thí nghiệm.
- Hỏng thật: vòng trong KI04, KI14, KI16, KI17, KI18, KI21 (6 ổ); vòng ngoài KA04, KA15, KA16, KA22, KA30 (5 ổ).
- Ổ khỏe K001–K006 đóng vai nền khỏe của máy (cùng giàn thử). Với mỗi (ổ đích, seed), nền là ổ K00h, h = (chỉ số ổ đích + seed) mod 6. Dùng 10 cửa sổ (cửa sổ đầu của bản ghi 1–10) để học, các bản ghi 11–20 làm đoạn khỏe kiểm tra.
- Sự cố của ổ nguồn: 10 cửa sổ (cửa sổ đầu của bản ghi 1–10). Ổ đích: kiểm tra trên cả 80 cửa sổ. Lỗi của ổ đích không bao giờ vào huấn luyện hay sinh.

## Thiết kế

- Số sự cố mỗi loại m = 1, 2, 4. Ổ nguồn chọn theo hoán vị cố định cho từng (seed, lớp), lồng nhau giữa các m, bỏ ổ đích.
- 11 ổ đích × 3 seed (11, 29, 47) × 3 mức = 99 lượt.

## Các nhánh (khóa)

Bộ phân loại là `InvariantClassifier('rf')`, nhưng thay **500 cây** cho 50 cây (các tham số khác giữ nguyên), kèm `causal_average`.

| Nhánh | Nội dung |
|---|---|
| `real` | Chỉ mẫu thật, `training()` cân bằng trọng số mặc định |
| `dup_add_0.25` | Bản sao mẫu thật, dồn thêm 0,25 trọng số cho mỗi lớp lỗi |
| `flow_mix_0.25_30` | 30 mẫu Flow S3 mỗi lớp lỗi, chiếm 25% trọng số lớp; tổng trọng số lớp không đổi |

Flow giữ cấu hình S3: 2.000 bước, 16 bước lấy mẫu, mức 0,5. Mạng học một lần mỗi lượt, chỉ từ cửa sổ của các ổ nguồn đã chọn. Điều kiện = one-hot lớp, tốc độ, log RMS khỏe của giàn (trung bình K001–K006). Lấy trung bình 3 hạt giống lấy mẫu (offset 20261106, 1, 2).

## Chỉ số

- **Chính:** macro recall 2 lớp lỗi theo cách chấm **chỉ chọn loại lỗi** (`fault_labels`) trên 80 cửa sổ của ổ đích. Tính theo ổ (trung bình seed và hạt giống lấy mẫu), rồi theo lớp.
- **Phụ:** cách chấm có lựa chọn khỏe (`selective(p, 0)`); số lượt (ổ đích × seed) có hơn một nửa cửa sổ đúng loại lỗi; tỉ lệ gán lỗi trên đoạn khỏe kiểm tra.
- CI 95% bootstrap theo ổ, phân tầng theo lớp, 5.000 lần.

## Tiêu chí (khai báo trước)

Flow **có giá trị** khi đạt đủ cả ba:
1. Ở ít nhất một mức m: `flow_mix − real` ≥ +3 điểm và CI 95% không chứa 0.
2. Không mức nào có `flow_mix − real` < −1 điểm.
3. Ở mọi mức đạt tiêu chí 1: `flow_mix − dup_add` > 0.

Không đạt thì kết luận Flow không có giá trị kiểm chứng trên Paderborn. Báo mọi mức và mọi nhánh, kể cả cách chấm phụ.
