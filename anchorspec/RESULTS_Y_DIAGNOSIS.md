# Đối chứng SVM và chẩn đoán sau cờ bất thường

Đọc cùng [báo cáo chính](RESULTS_Y_LOCAL.md). Các lượt dưới đây giữ nguyên kết quả âm tính trước đó và không thay đổi ý nghĩa chỉ số của báo cáo chính.

## Đối chứng SVM có kiểm tra theo sự kiện

| Sự kiện mỗi loại | Ghép RF cũ | SVM có chọn trọng số vật lý | SVM chỉ dùng lỗi thật |
|---|---:|---:|---:|
| 1 | 33.0% | 42.9% | 22.4% |
| 2 | 34.9% | 42.1% | 38.9% |
| 4 | 42.4% | 44.7% | 45.5% |

Đây vẫn là macro recall bốn lớp khi mô hình được phép chọn khỏe. Điểm SVM đã chuẩn hóa để gộp cửa sổ, chưa phải xác suất được hiệu chỉnh.

- 1 sự kiện mỗi loại, SVM ghép so với RF ghép: +9.9 điểm phần trăm; khoảng 95% từ -4.4 đến +23.5.
- 2 sự kiện mỗi loại, SVM ghép so với RF ghép: +7.2 điểm phần trăm; khoảng 95% từ -6.5 đến +21.1.
- 4 sự kiện mỗi loại, SVM ghép so với RF ghép: +2.4 điểm phần trăm; khoảng 95% từ -13.0 đến +18.2.

## Chẩn đoán khi đầu vào đã được xác nhận bất thường

Phép thử này giả định cờ bất thường phía trước đúng trên các bản ghi lỗi đã biết. Không đo được bỏ sót và báo nhầm của cờ đó. Không dùng điểm dưới đây làm điểm toàn pipeline. Mọi phương pháp trong cùng bảng đều được chọn loại lỗi theo cùng quy tắc loại lựa chọn khỏe; thư viện không có lớp lỗi nào trả về chưa có hỗ trợ.

Nhánh chẩn đoán mới chọn giữa RF và SVM, ba biểu diễn và ba trọng số tổng hợp bằng macro recall loại lỗi trên nguyên ổ donor giữ lại. Đối chứng chỉ lỗi thật có cùng tập lựa chọn bộ phân loại và biểu diễn.

### Đủ lớp từ đầu

| Số sự kiện mỗi loại | RF ghép cũ | Chọn theo nhiệm vụ chẩn đoán | Chỉ lỗi thật, cùng cách chọn |
|---|---:|---:|---:|
| 1 | 33.0% | 35.8% | 41.0% |
| 2 | 34.9% | 56.5% | 63.6% |
| 4 | 42.4% | 55.6% | 66.7% |

- 1 sự kiện: chẩn đoán mới so với ghép cũ: +2.8 điểm phần trăm; khoảng 95% từ -8.0 đến +13.5; so với chỉ lỗi thật: -5.2 điểm phần trăm; khoảng 95% từ -20.8 đến +9.5. Nhánh chỉ lỗi thật có chọn cấu hình so với ghép cũ: +8.0 điểm phần trăm; khoảng 95% từ -4.2 đến +19.7.
- 2 sự kiện: chẩn đoán mới so với ghép cũ: +21.6 điểm phần trăm; khoảng 95% từ +8.0 đến +35.9; so với chỉ lỗi thật: -7.1 điểm phần trăm; khoảng 95% từ -16.1 đến +1.6. Nhánh chỉ lỗi thật có chọn cấu hình so với ghép cũ: +28.7 điểm phần trăm; khoảng 95% từ +10.8 đến +47.3.
- 4 sự kiện: chẩn đoán mới so với ghép cũ: +13.2 điểm phần trăm; khoảng 95% từ -5.8 đến +32.2; so với chỉ lỗi thật: -11.1 điểm phần trăm; khoảng 95% từ -18.9 đến -4.1. Nhánh chỉ lỗi thật có chọn cấu hình so với ghép cũ: +24.3 điểm phần trăm; khoảng 95% từ +5.7 đến +43.2.

### Sự kiện đến dần

| Số sự kiện tổng cộng | RF ghép cũ | Chọn theo nhiệm vụ chẩn đoán | Chỉ lỗi thật, cùng cách chọn |
|---|---:|---:|---:|
| 0 | 21.0% | 21.0% | 0.0% |
| 2 | 29.0% | 24.0% | 31.2% |
| 4 | 33.2% | 29.1% | 25.8% |
| 8 | 31.2% | 34.2% | 45.3% |
| 12 | 40.6% | 45.7% | 40.4% |

- 0 sự kiện: chẩn đoán mới so với ghép cũ: +0.0 điểm phần trăm; khoảng 95% từ +0.0 đến +0.0; so với chỉ lỗi thật: +21.0 điểm phần trăm; khoảng 95% từ +11.1 đến +32.0. Nhánh chỉ lỗi thật có chọn cấu hình so với ghép cũ: -21.0 điểm phần trăm; khoảng 95% từ -32.0 đến -11.1.
- 2 sự kiện: chẩn đoán mới so với ghép cũ: -5.0 điểm phần trăm; khoảng 95% từ -13.9 đến +2.8; so với chỉ lỗi thật: -7.2 điểm phần trăm; khoảng 95% từ -16.1 đến +2.5. Nhánh chỉ lỗi thật có chọn cấu hình so với ghép cũ: +2.2 điểm phần trăm; khoảng 95% từ -6.5 đến +10.5.
- 4 sự kiện: chẩn đoán mới so với ghép cũ: -4.1 điểm phần trăm; khoảng 95% từ -14.5 đến +5.1; so với chỉ lỗi thật: +3.3 điểm phần trăm; khoảng 95% từ -10.1 đến +16.1. Nhánh chỉ lỗi thật có chọn cấu hình so với ghép cũ: -7.5 điểm phần trăm; khoảng 95% từ -23.8 đến +8.5.
- 8 sự kiện: chẩn đoán mới so với ghép cũ: +3.0 điểm phần trăm; khoảng 95% từ -7.3 đến +13.3; so với chỉ lỗi thật: -11.1 điểm phần trăm; khoảng 95% từ -20.3 đến -2.0. Nhánh chỉ lỗi thật có chọn cấu hình so với ghép cũ: +14.0 điểm phần trăm; khoảng 95% từ -0.3 đến +28.5.
- 12 sự kiện: chẩn đoán mới so với ghép cũ: +5.1 điểm phần trăm; khoảng 95% từ -8.0 đến +17.6; so với chỉ lỗi thật: +5.3 điểm phần trăm; khoảng 95% từ -3.4 đến +14.1. Nhánh chỉ lỗi thật có chọn cấu hình so với ghép cũ: -0.2 điểm phần trăm; khoảng 95% từ -14.0 đến +14.8.

## Từng lớp ở nhánh chẩn đoán mới

| Sự kiện mỗi loại | Vòng trong | Vòng ngoài | Bi | Vòng cách | Giai đoạn sớm, bốn lớp |
|---|---:|---:|---:|---:|---:|
| 1 | 82.8% | 60.4% | 0.0% | 0.0% | 41.2% |
| 2 | 82.5% | 62.1% | 53.3% | 28.1% | 61.3% |
| 4 | 74.4% | 69.1% | 56.5% | 22.5% | 58.0% |

## Cách diễn giải

Một phương pháp chỉ đáng chọn nếu cải thiện có ý nghĩa so với cả đối chứng ghép cũ và đối chứng chỉ lỗi thật có cùng quyền chọn cấu hình, đồng thời không bỏ qua lớp cần quan tâm. Các khoảng bootstrap ở đây chưa hiệu chỉnh việc thử nhiều hướng trên cùng dữ liệu.

Chọn loại lỗi sau cờ bất thường là cách tổ chức pipeline. Nó không tự tạo thêm thông tin ngoài băng cảm biến, không xác nhận nhãn sửa chữa và không biến lỗi chưa có dữ liệu thành lớp đã học. Cần đo với đầu ra bộ phát hiện thật trước khi báo cáo hiệu quả tích hợp.

Đã dựng lại 480 cấu hình theo hàng kết quả với tám phương pháp và kiểm tra số dự đoán gốc khớp trước khi tính chỉ số điều kiện. Đây là kiểm tra tái lập, không phải 480 ổ độc lập.

Chạy lại phần bổ sung:

```powershell
python anchorspec/y_kernel_run.py
python anchorspec/y_kernel_run.py --mode stream
python anchorspec/y_diagnostic_route.py
python anchorspec/y_diagnostic_run.py
python anchorspec/y_diagnostic_run.py --mode stream
python anchorspec/y_report_extensions.py
```
