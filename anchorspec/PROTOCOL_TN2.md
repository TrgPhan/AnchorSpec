# Giao thức TN2 — ghi trước khi đọc bất kỳ ổ test nào

**Câu hỏi:** chỉ với dữ liệu bình thường của máy cộng thông số ổ bi, lỗi cấy có phân loại được hỏng thật không, so với dữ liệu nhân tạo và dữ liệu máy khác?

**Giả thuyết (handoff):** A ≥ C và gần B. **Cổng G1:** A không thua C. Chỉ tiêu tham khảo: đúng loại lỗi ≥ 80%.

## Dữ liệu

Paderborn, điều kiện `N15_M07_F10` (1500 rpm, 0,7 Nm, 1000 N), 20 bản ghi 4 s mỗi ổ. Thông số 6203 lấy từ bảng factsheet của Lessmeier et al. 2016: n=8, d=6,75 mm, D=28,55 mm, góc 0°. Tất cả qua giả lập cảm biến rẻ: hạ 4 kHz, lọc 1 kHz, 25 µg/√Hz, ±8 g, 20 bit. Cửa sổ 1 s không chồng lấn.

**Chia theo ổ bi, không theo cửa sổ. Ổ test chọn trước khi xem tín hiệu.**

| Vai trò | Ổ bi |
|---|---|
| Nền và huấn luyện bình thường | K001, K002, K003 |
| Dev bình thường | K004 |
| Test bình thường | K005, K006 |
| Nhánh B, hỏng nhân tạo | KA01, KA03, KA05, KA06, KA07, KA08, KA09; KI01, KI03, KI05, KI07, KI08 |
| Dev hỏng thật, dùng để hiệu chỉnh | KA22 (ngoài), KI21 (trong) |
| **Test hỏng thật** | KA04, KA15, KA16, KA30 (ngoài); KI04, KI14, KI16, KI17, KI18 (trong) |

KA22 và KI21 được chọn vì là loại phổ biến nhất trong bảng tư liệu: mỏi rỗ, một vết, mức 1. KB23, KB24, KB27 bị loại vì hỏng cả hai vòng.

## Các nhánh huấn luyện

Mô hình giống nhau: RF 200 cây, `bootstrap=False`, `max_features='sqrt'`, cân bằng lớp, seed 11/29/47. Chuẩn hóa theo thống kê bình thường của máy nguồn.

- **A:** K001–K003 + 400 mẫu cấy mỗi lớp, tham số đã hiệu chỉnh ABC trên KA22/KI21. **Nhánh chính.**
- **A0:** như A nhưng dùng tiên nghiệm rộng, không chạm lỗi thật. Đo giá trị của bước hiệu chỉnh.
- **B:** K001–K003 + các ổ hỏng nhân tạo.
- **C:** CWRU nguyên khối: bình thường, vòng trong, vòng ngoài @6h; đường kính 0,007/0,014/0,021"; 0–3 HP. Chuẩn hóa bằng bình thường CWRU, kiểm tra bằng bình thường Paderborn.
- **C2:** lỗi CWRU + bình thường K001–K003. C2 cho dữ liệu máy khác lợi thế nhất, nên G1 phải được đọc so với **cả C và C2**.

## Chỉ số

**Chính:** trung bình 2 lớp lỗi của độ đúng loại theo từng ổ test, trung bình 3 seed. **Phụ:** số ổ bỏ phiếu đa số đúng, độ đúng bình thường, AUC lỗi–bình thường. **Bất định:** CI 95% bootstrap theo **ổ bi** trong từng lớp cho từng hiệu. Với 9 ổ lỗi, CI rộng là đúng bản chất, không phải khuyết điểm.

## Quy trình

`prepare` → `dev` (hiệu chỉnh, kiểm tra trên K004/KA22/KI21) → `freeze` (ghi hash mã, hiệu chỉnh và giao thức) → `test` (một lần; hàm đọc dữ liệu chặn ổ ngoài danh sách của từng giai đoạn; từ chối chạy lại).

Dev được phép dẫn tới sửa mã **trước** `freeze`, và mọi lần sửa được ghi ở mục cuối. Kết quả dev không được dùng làm kết quả báo cáo.

## Giả định và giới hạn đã biết

- Trường `Unit` của kênh rung Paderborn rỗng. Giả định m/s²: 1 đơn vị = 1/9,81 g. Đây là ca bất lợi hơn với nhiễu cảm biến. Độ nhạy khi coi là g được kiểm tra trên dev.
- Mọi ổ Paderborn dùng chung một giàn thử, nên B và A không phải là chuyển máy thật. Paderborn chỉ một trục, nên chưa kiểm được góc nhìn giữa các trục.
- Dev lỗi thật chỉ 2 ổ, cùng giàn thử với test, nên hiệu chỉnh có thể lạc quan so với máy DENSO.
- Công thức vòng cách, dị vật, hết dầu **không** được kiểm chứng ở TN2 vì Paderborn không có nhãn đó.
- Cảm biến kiểu ADXL355 chưa được DENSO xác nhận. Vẫn là kết quả sơ bộ trên dữ liệu công khai.

## Nhật ký sửa đổi trước freeze

- Bộ ước lượng tốc độ từ phổ (`bearing.estimate_rpm`), kiểm trên K001–K003 so với kênh `speed`: sai số trung vị 2,0–5,0%, lớn nhất ~10%. **Không đạt cổng 1%.** Sai số này lớn hơn dung sai bậc lỗi nên TN2 dùng tốc độ danh định 1500 rpm cho mọi nhánh. Bước ước lượng tốc độ của kế hoạch v1.4 vì vậy **chưa được kiểm chứng**.
- Dev vòng 1 (48 đặc trưng): K004 chỉ đúng 3,7–7,9% ở A/A0/B. Chẩn đoán trên K001–K004, KA22, KI21: log RMS giữa các ổ bình thường lệch từ −5,0 đến −6,09 (~3 lần), trong khi KI21 hỏng thật là −6,0, tức biên độ tuyệt đối không phân biệt được lỗi mức 1 và không chuyển giao giữa các ổ. **Sửa:** bỏ log RMS, log đỉnh, log đỉnh-đỉnh khỏi mọi nhánh (còn 45 đặc trưng). Quy định: **tối đa 2 vòng dev**, vòng 2 là vòng cuối, kết quả thế nào cũng freeze để tránh khớp quá với 3 ổ dev. Kết quả vòng 1: A 0,740; A0 0,329; B 0,656; C 0,206; C2 0,002.
- Dev vòng 2 (45 đặc trưng, 3 seed): A 0,892; A0 0,433; B 0,496; C 0,231; C2 0,021. Độ đúng bình thường K004: A 1,7%; B 10%; C 87,9%; C2 100%. Số của A là **trong mẫu** vì KA22/KI21 đã dùng để hiệu chỉnh. Coi kênh rung là g (dev): A 0,910; B 0,419; C 0,225, tức thứ tự các nhánh không đổi. Freeze theo quy định dù K004 vẫn gần như bị coi là lỗi.
- Trước freeze, không dựa trên kết quả test, thêm hai phân tích **phụ**: (1) `type_given_fault`: so xác suất inner với outer trên ổ lỗi, bỏ qua lớp bình thường, ứng với việc phân loại chạy sau autoencoder DENSO; (2) E6: nhánh B với tín hiệu gốc 64 kHz so với B cảm biến rẻ. Chỉ số chính và cổng G1 không đổi.
