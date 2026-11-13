# Chọn độ mạnh Flow-within (UORED) rồi kiểm tra trên XJTU-SY

Ghi ngày 12/11/2026, **trước khi chạy độ mạnh 0,3** và trước khi chạy XJTU. Đã xem độ mạnh 0,25, 0,5, 1,0 và 0,1 trên UORED (0,1 vừa chạy xong, chưa tính chỉ số).

## Nhánh
`flow_within_s`: Flow (mô hình S3 của Trường) học từ cặp đoạn của cùng một sự cố, sinh quanh đoạn lỗi thật của **bi và vòng cách**, 20 mẫu mỗi sự cố, chiếm 25% khối lượng lớp, ở tầng 1. Vòng trong / ngoài vẫn chỉ dùng vật lý (tầng 2, như `hier`).

## Quy tắc chọn s (trên UORED, trung bình m = 1, 2)
- Ứng viên s ∈ {0,1; 0,25; 0,3; 0,5}.
- Loại ứng viên nếu recall của bất kỳ lớp nào (trong, ngoài, bi, cách) thấp hơn `hier` quá 2 điểm.
- Trong các ứng viên còn lại, chọn s có accuracy cao nhất. Nếu hai ứng viên chênh nhau ≤ 0,1 điểm, chọn s nhỏ hơn.

## Kiểm tra trên XJTU-SY (một lần, s đã chọn)
- 13 ổ, thư viện tự nhiên (mọi ổ khác), 8 seed.
- Nhánh: `real` (RF 500), `hier`, `flow_within_s`.
- Báo Avg Precision, Accuracy, Avg Recall, recall từng lớp, kèm CI bootstrap theo ổ.

**Lưu ý:** XJTU đã dùng ở các vòng phát triển trước (M-Dev, HIER), nên không hoàn toàn độc lập. Vòng cách chỉ có 2 ổ.
