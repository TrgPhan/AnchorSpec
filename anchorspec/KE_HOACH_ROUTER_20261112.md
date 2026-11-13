# Kế hoạch: pipeline v3 có bộ định tuyến sinh dữ liệu lỗi, giữ Flow

Ghi ngày 12/11/2026. Đây là kế hoạch, **chưa có kết quả**. Mỗi thí nghiệm sẽ có giao thức riêng, ghi và băm (sha256) trước khi chạy.

## 1. Mục tiêu

1. Với **từng loại lỗi** của **từng máy**, tự chọn cách tạo dữ liệu lỗi phù hợp với thông tin đang có, thay vì để lớp đó bằng 0.
2. Giữ Flow trong pipeline, ở vị trí có lý do để hy vọng nó giúp, và có cổng an toàn để nó không kéo điểm xuống.
3. Không làm giảm kết quả của kiến trúc đã chốt (hai tầng + cấy lỗi neo) trên Paderborn và HUST.

## 2. Pipeline v3

```text
Cờ bất thường (DENSO)
  -> Kiểm tra tín hiệu + ước lượng tốc độ từ rung
       (bất thường do tốc độ -> báo "bất thường tốc độ", không đoán lỗi ổ bi)
  -> BỘ ĐỊNH TUYẾN SINH DỮ LIỆU, chạy riêng cho từng loại lỗi c:
       [A]  c có luật vật lý + biết mã ổ + tốc độ + có nền khỏe của máy này
              -> cấy lỗi neo thuần trên nền khỏe máy này
                 (+ Flow làm đa dạng mẫu cấy, F-neo)
       [B]  c có luật vật lý, nhưng KHÔNG có nền khỏe của máy này
              -> cấy lỗi trên nền mượn (máy cùng loại ổ, hoặc đoạn đầu đời của máy)
       [C]  c KHÔNG có luật vật lý, nhưng thư viện có sự cố thật của c ở máy khác
              -> chuyển lỗi sang nền khỏe máy này:
                 Flow-transport | transport | surrogate (chọn theo kết quả R2)
       [D]  c không có luật vật lý và không có sự cố nào
              -> không sinh; mô hình được phép trả lời "lỗi khác / chưa biết"
       [A1] máy này đã có sự cố thật của c
              -> dùng trực tiếp, và hiệu chỉnh tham số cấy lỗi theo sự cố đó
  -> Tầng 1 (sự cố thật + dữ liệu nhánh C): khỏe / nhóm vòng / bi / vòng cách / ...
  -> Tầng 2 (sự cố thật + dữ liệu nhánh A hoặc B): vòng trong hay vòng ngoài
  -> Cổng "chưa biết" -> giả thuyết lỗi -> kỹ sư xác nhận -> thêm vào thư viện, hiệu chỉnh
```

## 3. Bảng quy tắc định tuyến

| Điều kiện cho loại lỗi c | Nhánh | Cách tạo dữ liệu | Bằng chứng hiện có |
|---|---|---|---|
| Có luật + mã ổ + tốc độ + nền khỏe máy này | A | Cấy neo thuần (A0) | **Đã kiểm chứng** cho vòng trong / ngoài (Paderborn, HUST) |
| Có luật, không có nền khỏe máy này | B | Cấy trên nền mượn | Paderborn đã dùng nền của ổ khỏe khác cùng giàn và vẫn đạt. Chưa thử nền khác giàn |
| Không có luật, thư viện có sự cố thật | C | Chuyển lỗi sang nền máy này | Transport cũ: UORED +5,7 điểm, HUST không giữ được. Flow-transport: **chưa thử** |
| Không có gì | D | Không sinh, cho phép "chưa biết" | Chưa thử |
| Máy này đã có sự cố thật | A1 | Dùng thật + hiệu chỉnh cấy | Dùng thật: đã có (tầng 1). Hiệu chỉnh: chưa thử |

**Luật vật lý hiện có:**
- Vòng trong (BPFI), vòng ngoài (BPFO): đã kiểm chứng.
- Vòng cách: có trong code (`injection.py`), chưa kiểm chứng.
- Bi (nhịp 2 × BSF): chưa có, sẽ viết ở R1.
- Thiếu dầu, dị vật: có trong code, không có dữ liệu để kiểm chứng.

## 4. Đặt Flow ở đâu

| Vị trí | Vai trò | Lý do có thể giúp | Bằng chứng | Cổng an toàn |
|---|---|---|---|---|
| **Nhánh A (F-neo)** | Sinh biến thể quanh mẫu cấy trên nền máy này | Đa dạng hóa mẫu vật lý | FUSION: giữ được (±0,7 điểm), đóng góp ≈ 0 | Đã qua tiêu chí "không làm hại". Giữ |
| **Nhánh C (Flow-transport)**, vị trí mới chính | Học **phần lỗi so với nền khỏe** (phổ lỗi trừ phổ khỏe của cùng máy nguồn), chuẩn hóa theo tần số đặc trưng, rồi **áp lên nền khỏe máy này** | Đây là chỗ duy nhất Flow mang được thông tin mà cả vật lý lẫn nền khỏe đều không có: hình dạng lỗi của bi, vòng cách học từ sự cố thật | Chưa thử | Chỉ bật nếu thắng transport và surrogate trên bộ phát triển, và không thua trên bộ kiểm chứng |
| ~~Song song với mô hình S3~~ | | | FUSION: −4 đến −13 điểm | **Loại** |

**Flow-transport khác Flow cũ ở hai điểm:**
- Flow cũ học chênh lệch giữa hai cửa sổ **lỗi** của cùng một ổ. Flow-transport học chênh lệch giữa **lỗi và khỏe** của cùng một máy, tức "cái lỗi thêm vào".
- Flow cũ áp lên cửa sổ lỗi của máy cũ. Flow-transport áp lên **nền khỏe máy mới**, sau khi dịch tần số theo tỉ lệ tần số đặc trưng (ví dụ BSF của ổ mới chia BSF của ổ cũ).

## 5. Các thí nghiệm

Nguyên tắc chung:
- Phát triển trên **UORED** (và XJTU nếu cần), khóa cấu hình theo quy tắc ghi trước, rồi kiểm chứng **một lần** trên **HUST** (và Paderborn nếu áp dụng được).
- Mọi bộ sinh đều có **đối chứng photocopy** cùng số dòng, cùng trọng số.
- 8 seed; chỉ số "chọn đúng loại lỗi" + recall từng lớp; bootstrap theo ổ.
- Mỗi thí nghiệm **chỉ một phép so sánh chính**; các phép so khác chỉ báo cáo kèm.

### R0. Hạ tầng (khoảng 2 giờ)
- `router.py`: nhận cấu hình máy (mã ổ, tốc độ, có nền khỏe không, thư viện sự cố) và trả về nhánh + bộ sinh cho từng loại lỗi; ghi lại quyết định.
- Kiểm thử: kiến trúc chốt phải tái tạo đúng từng dự đoán của PB-HIER và HUST HIER khi router chỉ bật nhánh A.

### R1. Luật vật lý cho lỗi bi (khoảng 3 giờ)
- **Mô phỏng:** xung va ở nhịp 2 × BSF; độ mạnh điều biến theo FTF (vòng cách); có những đoạn vết nứt không chạm (xác suất chạm rút ngẫu nhiên); cộng hưởng như vòng trong / ngoài.
- **Phát triển:** UORED, 5 ổ bi. Chỉ chỉnh khoảng tham số, chọn bằng "giữ lại một ổ" trên UORED.
- **Kiểm chứng:** HUST, 4 ổ bi (B5–B8), một lần.
- **Phép so chính:** chỉ cấy lỗi (trong + ngoài + bi) so với chỉ cấy lỗi (trong + ngoài), xét recall lớp bi.
- **Đạt nếu:** recall bi ≥ 30% với khoảng tin cậy > 0, và recall trong / ngoài không giảm quá 3 điểm.
- **Nếu đạt:** bi chuyển từ nhánh C sang nhánh A.

### R2. Nhánh C: lớp không có luật vật lý (khoảng 4 giờ)
- **Lớp thử:** bi (giả định chưa có luật, để R2 độc lập với R1) và vòng cách.
- **Tình huống:** máy đích không có sự cố của lớp đó; thư viện có 1 hoặc 2 sự cố của máy khác.
- **Nhánh so sánh:**
  1. Không sinh: lớp đó chỉ học từ sự cố thật ở tầng 1 (kiến trúc chốt hiện tại).
  2. Photocopy (đối chứng).
  3. Surrogate (code cũ).
  4. Transport (code cũ, `measured_transport.py`).
  5. **Flow-transport** (mới).
- **Phát triển:** UORED (bi + vòng cách). **Kiểm chứng:** HUST (bi). Vòng cách chỉ kiểm thêm được trên XJTU (2 ổ), nên chỉ coi là tham khảo.
- **Phép so chính:** bộ sinh được khóa so với "không sinh", xét recall của lớp không có luật.
- **Đạt nếu:** +5 điểm với khoảng tin cậy > 0 cho lớp đó, macro không giảm quá 1 điểm, và hơn photocopy.
- **Quy tắc khóa trên UORED:** chọn bộ sinh có recall lớp không luật cao nhất trong các bộ hơn photocopy. Nếu Flow-transport hòa transport trong khoảng 1 điểm, ưu tiên Flow-transport.

### R3. Nhánh B: không có nền khỏe của máy (khoảng 2 giờ)
- **Nhánh so sánh:**
  - Nền của chính máy (mốc).
  - Nền mượn từ máy khác cùng giàn: HUST lấy cỡ ổ khác; Paderborn lấy ổ khỏe khác (đang dùng sẵn).
  - Nền "đầu đời": các đoạn đầu khi máy mới chạy, như XJTU giai đoạn khỏe. Đây là tình huống DENSO lúc mới lắp.
- **Chỉ số:** recall trong / ngoài.
- **Đạt nếu:** nền mượn kém nền chính máy không quá 5 điểm, và vẫn hơn "chỉ dữ liệu gốc".

### R4. Nhánh D: lớp "chưa biết" (khoảng 3 giờ)
- **Tình huống:** bỏ hẳn lớp bi khỏi thư viện và không có luật cho bi.
- **Cách làm:** cổng lạ dựa trên khoảng cách tới các lớp đã biết hoặc độ tin cậy của mô hình. Ngưỡng chỉnh trên bộ phát triển bằng cách giữ lại một lớp đã biết.
- **Chỉ số:**
  - Tỉ lệ cửa sổ bi được báo "chưa biết", thay vì 0% như hiện nay.
  - Tỉ lệ cửa sổ trong / ngoài / khỏe bị báo nhầm là "chưa biết".
- **Đạt nếu:** ≥ 50% cửa sổ bi được báo "chưa biết", và ≤ 10% cửa sổ đã biết bị báo nhầm.

### R5. Ghép đầu-cuối (khoảng 2 giờ)
- **Router đầy đủ** (theo kết quả R1–R4) so với **kiến trúc chốt**, trên Paderborn + HUST, 8 seed.
- **Đạt nếu:** không mức nào kém quá 1 điểm ở vòng trong / ngoài; lớp bi trên HUST tăng.
- **Báo riêng đóng góp của Flow:** router có Flow so với router không có Flow (thay Flow-transport bằng bộ sinh tốt thứ hai, bỏ F-neo).

### R6. Hiệu chỉnh từ sự cố đầu tiên của chính máy, A1 (tùy thời gian, khoảng 3 giờ)
- **Dữ liệu:** HUST. Dùng sự cố của chính ổ đích ở tải 0 để hiệu chỉnh dải cộng hưởng, độ tắt và độ mạnh của mô phỏng; kiểm tra trên tải 2 và 4.
- **Phép so chính:** cấy có hiệu chỉnh so với cấy không hiệu chỉnh.
- Đây cũng là chỗ thử Flow học "lỗi so với khỏe" ngay trên chính máy đích.

### R7. DENSO (khi có tần số lấy mẫu và mã ổ bi)
- Cấu hình router cho máy DENSO.
- Đo báo nhầm trên log 400.
- Kiểm tra cổng tốc độ trên log 300 và 500.

## 6. Lịch dự kiến

| Ngày | Việc |
|---|---|
| 12/11 tối | R0, viết giao thức R1 và R2 |
| 13/11 | R1 (lỗi bi), R2 (nhánh C, có Flow-transport) |
| 14/11 | R3, R4, R5 (ghép đầu-cuối) |
| 15/11 | R6 nếu kịp; báo cáo, cập nhật slide cho vòng 16/11 |

## 7. Rủi ro và giới hạn cần nói trước

- **Dữ liệu đã dùng:** HUST và Paderborn đã được nhìn nhiều lần. UORED là bộ phát triển. Không có bộ dữ liệu thứ ba còn mới hoàn toàn cho lỗi bi và vòng cách.
- **Ít ổ:** lỗi bi có 5 ổ UORED và 4 ổ HUST; vòng cách có 5 ổ UORED và 2 ổ XJTU. Khoảng tin cậy sẽ rộng.
- **Flow-transport có thể không thắng transport cũ.** Nếu vậy, Flow chỉ còn ở nhánh A (F-neo, trung tính), và báo cáo phải nói đúng như vậy.
- **Luật lỗi bi có thể không đạt.** Lỗi bi vốn chập chờn và khó phát hiện kể cả với dữ liệu thật.
- **Không được nói "Flow tiết kiệm dữ liệu"** trừ khi R2 và R5 cho thấy Flow-transport hơn cả photocopy lẫn transport trên bộ kiểm chứng.

## 8. Cách kết quả quyết định cấu hình cuối

| Kết quả | Cấu hình |
|---|---|
| R1 đạt | Bi vào nhánh A |
| R1 không đạt, R2 đạt | Bi vào nhánh C với bộ sinh đã khóa |
| Cả hai không đạt | Bi học từ sự cố thật (như hiện nay); nếu không có sự cố, dùng nhánh D |
| Flow-transport được khóa ở R2 và R5 đạt | Flow có hai vai trò: F-neo (A) và Flow-transport (C), có số liệu đóng góp |
| Flow-transport không được khóa | Flow chỉ ở F-neo (A): giữ trong pipeline, nói rõ đóng góp ≈ 0 |
