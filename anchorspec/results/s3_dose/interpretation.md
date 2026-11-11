# S3-Dose: đọc kết quả (11/11/2026)

264/264 lượt hoàn tất, không lỗi. Gồm UORED 15 ổ × 3 seed × 5 bộ sự cố, và XJTU 13 ổ × 3 seed. Thăm dò trên dữ liệu đã dùng nhiều lần; không phải xác nhận độc lập.

## Theo quy tắc khai báo trước

| Câu hỏi | Kết quả |
|---|---|
| Có liều sinh chung cho mọi bộ sự cố? | **Không.** Không nhánh nào vừa ≥ real ở mọi bộ, vừa sát nhánh tốt nhất trong vòng 2 điểm |
| Mẫu sinh có giá trị riêng, so ở cùng khối lượng? | **Có theo quy tắc, nhưng không nhất quán.** Có so sánh CI dương ở 5/6 bộ, nhưng mỗi bộ là một nhánh khác, và cùng nhánh có thể âm ở bộ khác. Khoảng 90 phép so sánh chưa hiệu chỉnh so sánh bội |
| Chọn được liều lúc lắp đặt? | **Không.** Bộ chọn dùng sự cố của chính máy kém real trung bình 0,29 điểm; ở bộ 1-1-1 không chọn được vì lớp nào cũng chỉ có 1 sự cố |

## Số sự cố thật quyết định nhiều hơn liều sinh

| Bộ sự cố (trong-cách-ngoài) | 1-1-1 | 1-2-5 | 5-2-1 | 2-2-2 | 4-4-4 | XJTU tự nhiên |
|---|---:|---:|---:|---:|---:|---:|
| Chỉ mẫu thật, macro | 41,5 | 42,9 | 52,6 | 55,7 | 67,0 | 68,3 |
| Dao động theo seed | 35,1–45,3 | 39,6–45,3 | 40,0–62,5 | 52,6–60,0 | 63,9–69,5 | 63,3–76,1 |

Đi từ 1 lên 2 rồi 4 sự cố mỗi loại tăng tổng cộng khoảng 25 điểm. Mọi liều sinh chỉ đổi khoảng −10 đến +7 điểm, và nhỏ hơn biên độ dao động do seed.

## Độ nhất quán của từng nhánh (chênh so với real, điểm)

| Nhánh | 5-2-1 | 1-2-5 | 2-2-2 | 1-1-1 | 4-4-4 | XJTU | TB | Số bộ ≥ real |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Trộn 25% Flow, 30 mẫu/loại** | +1,8 | +1,9 | +3,7 | +6,9 | +1,6 | +3,5 | **+3,2** | **6/6** |
| 10 mẫu/sự cố, thêm 25% (cách S3) | −2,5 | +0,2 | +1,1 | +4,7 | +1,7 | +4,0 | +1,5 | 5/6 |
| Trộn 25%, 90 mẫu/loại | −0,5 | −1,3 | +5,2 | +0,4 | +4,9 | −2,7 | +1,0 | 3/6 |
| Thêm 25%, 30 mẫu/loại | −4,1 | −2,3 | −1,6 | −0,3 | +0,9 | +4,4 | −0,5 | 2/6 |
| Bản sao, thêm 25% (chỉ dồn trọng số) | −3,4 | −0,8 | +1,3 | +0,6 | −4,2 | +4,3 | −0,4 | 3/6 |
| Bù cho bằng số dòng, không trọng số | −6,5 | +1,4 | −0,6 | −2,3 | +0,6 | +10,7 | +0,5 | 3/6 |
| Bộ chọn lúc lắp đặt | −2,3 | −0,5 | −2,9 | 0,0 | +0,7 | +3,3 | −0,3 | 3/6 |

**Trộn 25% Flow, 30 mẫu mỗi loại** là nhánh duy nhất không thua real ở cả 6 bộ. Cách trộn này giữ nguyên tổng trọng số mỗi lớp, nên không dồn trọng số về lớp lỗi. Nhưng đây là **nhận xét hậu nghiệm**: chọn ra 1 trong 14 nhánh sau khi xem điểm. Với 14 nhánh và 6 bộ, xác suất có ít nhất một nhánh dương ở cả 6 bộ chỉ do may là khoảng 20%. Cần khóa cấu hình này và kiểm tra trên dữ liệu mới. Nhánh này cũng **không cứu được lớp chỉ có 1 sự cố**: ở bộ 5-2-1, vòng ngoài vẫn 31,5% so với 31,6% của real.

## Tỉ lệ với dữ liệu khỏe

Pipeline đã cân bằng bằng trọng số: lớp khỏe và mỗi lớp lỗi có cùng tổng trọng số, không phụ thuộc số dòng hay số sự cố. Vì vậy tỉ lệ số mẫu kiểu "2 khỏe : 1 : 1 : 1" không phải là núm cần chỉnh.

- **Dồn trọng số về lớp lỗi** (nhánh bản sao) cho kết quả trái dấu giữa các bộ, từ −4,2 đến +4,3 điểm.
- **Cái giá của việc dồn trọng số không đo được ở đây:** tỉ lệ gán lỗi trên đoạn khỏe gần như luôn 0%, vì đoạn khỏe kiểm tra nằm cùng tệp với nền.
- **Bù cho bằng số dòng mà không dùng trọng số** không ổn định: −6,5 đến +10,7 điểm.

Đề xuất giữ tổng trọng số 1 : 1 : 1 : 1 giữa lớp khỏe và các lớp lỗi. Phần sinh chỉ chiếm một tỉ lệ cố định bên trong mỗi lớp lỗi.
