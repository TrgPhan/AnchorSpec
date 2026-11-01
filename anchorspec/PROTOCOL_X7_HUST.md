# Giao thức X7 — xác nhận thứ hai trên HUST, ghi trước khi đọc tín hiệu lỗi

**Câu hỏi:** thiết kế đã freeze ở E8 cho kết quả ra sao trên bộ dữ liệu chưa dùng, lỗi nhân tạo rất nhỏ?

[HUST bearing](https://data.mendeley.com/datasets/cbv7jyx4p9/3), CC BY 4.0, 99 tệp 10 s, 51,2 kHz, gia tốc đứng. Cỡ ổ 6204–6208, 3 mức tải, vết nứt 0,2 mm cắt dây. Tài liệu không ghi đơn vị và đường kính vòng chia: **lấy D = (trong + ngoài)/2, góc 0°** (giả định). Tốc độ lấy từ biến `fs` trong tệp bình thường.

Mỗi tổ hợp cỡ ổ và tải coi là một "máy" (15 máy). Nền: 6 s đầu tệp N, kiểm tra bình thường: 4 s cuối. Cấy vào nền, không dùng lỗi thật. Giữ nguyên `funnel.py`, RF 50 cây, cảm biến 1 kHz, 3 seed, không đổi cấu hình theo kết quả. Dữ liệu được coi là m/s² nếu RMS file bình thường quá lớn so với g; quyết định dựa trên chỉ tệp N.

**Chỉ tiêu như E8:** M1 đúng khi trả lời ≥ 0,85; trả lời ≥ 0,60; bình thường bị gọi lỗi ≤ 0,10; AUROC chưa biết (B, IB, OB so với I, O, tức bi và lỗi kết hợp có bi) ≥ 0,85. Báo cáo thêm HI z ≥ 10 trên N (4 s cuối), I, O, và IO. **Không chia thành ổ vật lý độc lập được:** có khả năng cùng ổ dùng cho nhiều tải, nên CI không tính theo máy như độc lập; chỉ báo khoảng theo cỡ ổ.

## Đính chính sau khi chạy

Bản báo cáo đầu tính "đúng khi trả lời" gộp theo cửa sổ (0,865) và ghi là đạt. Chỉ tiêu ở trên lấy theo E8, tính theo ổ rồi macro theo lớp, cho 0,727: **không đạt**. X7 đạt 1/4 chỉ tiêu. Tính lại bằng `x_recheck.py`. Không đổi chỉ tiêu, không chạy lại.
