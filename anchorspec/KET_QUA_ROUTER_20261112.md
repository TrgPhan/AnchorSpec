# Kết quả pipeline v3 (bộ định tuyến sinh dữ liệu lỗi), 12/11/2026

Làm theo `PLAN.md` (gốc repo). Giao thức: `PROTOCOL_ROUTER_DEV.md`, `PROTOCOL_ROUTER_VAL.md`, cả hai có hash trước khi chạy. Kết quả đầy đủ: `results/router_dev/summary.md`, `results/router_val/summary.md`.

## Kết luận

**Router v3 không qua kiểm chứng. Giữ kiến trúc chốt (hai tầng + cấy lỗi neo).** Flow chỉ còn ở vị trí F-neo, đóng góp ≈ 0.

| Tiêu chí (PROTOCOL_ROUTER_VAL.md) | Kết quả |
|---|---|
| 1. Không làm hại (trong + ngoài ≥ −1 điểm mọi mức) | **Không đạt, sát nút:** Paderborn 1 sự cố −1,1 [−2,7; +0,4]; các mức khác từ −0,5 đến +0,9 |
| 2. Tăng lớp bi trên HUST | Không đạt: router không thêm gì cho bi (không bộ sinh nào được khóa) |
| 3. Không có sự cố bi: luật bi hoặc cổng "chưa biết" | Không đạt: cổng chỉ bắt 0,7% cửa sổ bi |
| 4. Flow có đóng góp | Không đạt: router − router_noflow từ −1,1 đến +0,9 |

## Lượt phát triển trên UORED: vì sao không gì được khóa

**Nhánh C** (bi và vòng cách coi như không có luật; trung bình hai mức sự cố):

| Bộ sinh | Recall bi + vòng cách | Macro 4 lớp |
|---|---:|---:|
| Không sinh (`hier`) | 42,3 | 48,9 |
| Photocopy | 42,3 | 48,9 |
| Surrogate | 42,3 | 47,8 |
| Transport | 47,7 | 46,0 |
| Transport + Flow | 46,3 | 45,2 |
| **Flow-gain** | **51,7** (+10,7 và +8,2, CI > 0) | 44,8 |

- **Flow-gain là bộ duy nhất tăng chắc chắn lớp không có luật vật lý,** hơn cả photocopy và transport. Đây là kết quả tích cực đầu tiên của Flow khi được neo vào nền khỏe của máy đích.
- **Nhưng nó kéo tụt vòng trong và vòng ngoài** (ví dụ m = 2: vòng trong 64,7 → 49,2; vòng ngoài 55,9 → 33,0), nên macro giảm 4 điểm và không qua điều kiện "macro ≥ hier − 1".

**Luật lỗi bi** (không có sự cố bi nào): recall bi tăng từ 0 lên 98–100%, **nhưng** vòng trong + vòng ngoài giảm khoảng 47 điểm. Gần như mọi lỗi có xung va đập đều bị gán thành "bi". Không đạt.

**Cổng "chưa biết":** ở mức chỉ báo nhầm 5,5% lớp đã biết, cổng chỉ bắt được 0,1% cửa sổ bi. Cửa sổ lỗi bi không nằm xa các lớp đã biết trong không gian đặc trưng.

## Điều rút ra (để thiết kế vòng sau)

1. **Mẫu sinh của một lớp "hút" cửa sổ của các lớp khác.** Hiện tượng này đã thấy với cấy phẳng (vòng cách sụp), và giờ lặp lại với luật bi và Flow-gain. Thứ tạo ra tín hiệu "có lỗi" thì dễ; thứ khó là **làm cho các lớp sinh ra phân biệt được với nhau**.
2. **Hướng sửa có cơ sở:** chỉ cho mẫu sinh của lớp c ảnh hưởng tới quyết định khi cửa sổ thật sự có dấu hiệu ở **tần số đặc trưng của c**, ví dụ đỉnh phổ đường bao ở 2 × BSF cho bi. Có thể làm bằng một bước kiểm tra vật lý trước khi tin mẫu sinh, hoặc một tầng riêng "bi hay không phải bi" có hiệu chỉnh ngưỡng. Hướng này **chưa thử** và cần giao thức mới; tiến hành trên UORED trước.
3. **Flow-gain đáng giữ để nghiên cứu tiếp,** vì là bộ duy nhất tăng chắc chắn lớp không có luật. Nhưng chỉ được dùng sau khi có bước kiểm tra ở ý 2.

## Giới hạn

- Thử luật bi với 4 cấu hình, Flow-gain với 1 cấu hình; không dò thêm để tránh chọn sau khi thấy kết quả.
- Lượt phát triển thấy kết quả thử của ổ 12, seed 11 trước khi chạy (đã ghi trong giao thức).
- Kiểm chứng S2 không có vòng cách (HUST không có lớp này).
