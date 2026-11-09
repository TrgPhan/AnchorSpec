# Dữ liệu mở và kết quả tiếp tục ngày 03/11/2026

Đã chuyển sang kiểm chứng bằng dữ liệu công khai, không chờ dữ liệu nhà máy. Đã tải ba nguồn mới, kiểm tra tính toàn vẹn và chạy hai phép thử. Kết quả dưới đây không được gộp với điểm UORED vì khác loại ổ, đầu vào và nhiệm vụ.

## Nguồn đã có trong workspace

| Nguồn | Dữ liệu sử dụng | Tình trạng | Giấy phép của nguồn |
|---|---|---|---|
| [6204, các mức mỡ](https://zenodo.org/records/7589904) | 8.569 hàng chỉ số cảm biến | Đã tải, kiểm tra MD5 và chạy phân loại | CC BY 4.0 |
| [DLR, ổ kim dao động](https://zenodo.org/records/20742913) | Bốn lần chạy không bôi trơn, 24 tệp cảm biến chọn lọc | Đã tải, kiểm tra CRC, chạy theo dõi tín hiệu | CC BY 4.0 |
| [SoliDAIR, ổ trượt](https://zenodo.org/records/17530066) | 126.640 hàng, 26 đầu vào và nhãn | Đã tải, kiểm tra MD5, đọc tài liệu và schema | CC BY-SA 4.0 |
| [NLN-EMP](https://doi.org/10.4121/2b61183e-c14f-4131-829b-cc4822c369d0.v4) | Nhiễm bẩn mỡ bằng mạt sắt | Đã xác minh tài liệu; host gốc chưa kết nối được | CC0 1.0 |

UORED vẫn dùng cho vòng trong, vòng ngoài, bi và vòng cách. Ba nguồn tải mới không thay thế lẫn nhau: dữ liệu ổ trượt không được đổi nhãn thành ổ bi, và dữ liệu mỡ không được gọi là dữ liệu dị vật.

## Phép thử phân biệt trạng thái mỡ

Nguồn do Karapalidou, Efraimidis, Vologiannidis và Antoniou công bố. Nhãn gồm lượng mỡ khuyến nghị với nắp kín, không mỡ khi bỏ nắp kín, và thừa mỡ khi bỏ nắp kín. Tín hiệu đã được cảm biến tổng hợp; không có dạng sóng để cấy lỗi hoặc mô phỏng lại cảm biến 4 kHz.

Dùng 5,140 hàng đầu để học, bỏ 1,713 hàng ở giữa làm khoảng cách, kiểm tra trên 1,716 hàng cuối, thực hiện riêng trong từng lớp. Không xáo trộn hàng. CSV không có timestamp hoặc mã lần chạy nên đây là chia theo thứ tự hàng, chưa phải kiểm tra khác phiên hay khác ổ. Không có hàng kiểm tra nào trùng chính xác bốn đặc trưng với tập học.

| Cấu hình cố định | Macro recall ba lớp |
|---|---:|
| RF 50 cây, bốn chỉ số rung | 85.3% |
| RF 50 cây, thêm nhiệt độ | 83.9% |
| Luôn chọn lớp phổ biến nhất | 33.3% |

| Trạng thái theo nhãn nguồn | Recall với bốn chỉ số rung |
|---|---:|
| Mỡ khuyến nghị và có nắp kín | 100.0% |
| Không mỡ và bỏ nắp kín | 72.0% |
| Thừa mỡ và bỏ nắp kín | 83.9% |

Ma trận nhầm lẫn được lưu trong JSON. Không dùng nhiệt độ cho kết quả chính. Vì thay đổi nắp kín đi cùng thay đổi nhãn, chưa thể quy toàn bộ điểm số cho lượng mỡ. Có đúng ba khối nhãn liên tục và không có mã sự kiện; không coi hàng nghìn hàng là hàng nghìn lần hỏng độc lập. Không đưa khoảng tin cậy giả định các hàng độc lập.

## Theo dõi bốn chuỗi DLR không bôi trơn

Nguồn do Seferli, Windelberg và Bierig tại DLR công bố. Đã chọn hai kênh gia tốc, góc dao động và ba kênh nhiệt độ cho mỗi lần chạy. Bốn lần chạy có 172, 94, 19 và 205 thời điểm đo, tổng 490 thời điểm; hai vị trí cảm biến tạo 980 bản ghi gia tốc. Đơn vị độc lập vẫn là bốn lần chạy.

Đóng băng phép thử trước khi đọc giá trị đặc trưng: năm thời điểm đầu làm nền, năm tiếp theo đặt ngưỡng, phần còn lại chạy về phía trước. So RMS với độ lệch nhiều đặc trưng. Báo khi ba thời điểm liên tiếp vượt mức lớn nhất của đoạn hiệu chuẩn. Đặc trưng dùng một cửa sổ mỗi giây, bỏ giây đầu để giảm quá độ, rồi lấy trung vị trong từng lần đo.

Chạy cả tín hiệu gốc 10 kHz và giả lập cảm biến 4 kHz, băng thông 1 kHz, dải ±8 g. Nhiệt độ và góc không đi vào bộ tính điểm. Các băng phổ của bộ đặc trưng phủ miền Nyquist của từng chế độ, nên đối chứng này so cả pipeline cảm biến và biểu diễn, không cô lập riêng ảnh hưởng của bộ lọc.

| Lần chạy | Kênh | Giờ báo của RMS, giả lập | Giờ báo nhiều đặc trưng, giả lập | Tỷ lệ mẫu vượt ±8 g lớn nhất trong một lần đo |
|---|---|---:|---:|---:|
| 4 | 1 | 5.11 | 3.07 | 84.7% |
| 4 | 2 | 6.39 | 7.16 | 8.2% |
| 6 | 1 | Không báo | 21.98 | 4.7% |
| 6 | 2 | 3.07 | Không báo | 2.9% |
| 7 | 1 | Không báo | Không báo | 1.1% |
| 7 | 2 | Không báo | 3.79 | 0.7% |
| 8 | 1 | 3.58 | 11.76 | 12.0% |
| 8 | 2 | Không báo | 12.27 | 2.4% |

Các thời điểm báo chỉ mô tả quy tắc trên chuỗi đo; không phải thời điểm khởi phát lỗi đã xác nhận, độ chính xác phát hiện hay dự báo giờ hỏng. Các lần chạy đều không bôi trơn ngay từ đầu, vì vậy không được gọi đoạn nền là trạng thái bôi trơn bình thường. Hai kênh trong cùng lần chạy không phải hai thí nghiệm độc lập.

Kết quả đáng chú ý: ở lần chạy 4, kênh 1, một đoạn có khoảng 84,7% mẫu gốc vượt dải ±8 g. Giả lập bị mất thông tin tại đầu vào; điểm lệch nền cao không tự chứng minh mô hình chẩn đoán tốt hơn. Có kênh bộ nhiều đặc trưng báo, có kênh không báo; chưa có một bộ tính điểm thắng mọi trường hợp.

Tài liệu bài báo ghi tải lần chạy 6 là 18,7 kN nhưng tên tệp ghi 18,4 kN. Đã giữ nguyên tên nguồn và ghi lại khác biệt; phép thử hiện tại không dùng tải làm đầu vào nên không tự chọn một giá trị để huấn luyện.

## SoliDAIR và nhiễm bẩn

SoliDAIR cung cấp nhãn bôi trơn hỗn hợp trên ổ trượt. Tài liệu đính kèm cho biết nhãn được suy ra từ đo tiếp xúc, còn đầu vào chứa tải, tốc độ, nhiệt độ và các đại lượng liên quan. Chưa chạy phân loại vì cần xác định nhóm điều kiện và lần thử hợp lệ; số hàng không được coi là số thí nghiệm độc lập. Nguồn này phù hợp cho nhánh theo dõi bôi trơn ổ trượt, không xác nhận nhánh rung ổ bi.

Bài báo NLN-EMP mô tả thêm mạt sắt vào mỡ ổ bi. Kết nối đến host gốc bị timeout; bản phân phối lại tìm thấy chỉ chọn lỗi vòng ngoài và các yếu tố gây nhiễu, không có lớp nhiễm bẩn cần dùng. Vì vậy chưa tải bản đó để thay thế nhãn nhiễm bẩn. [Tài liệu tác giả NLN-EMP](https://pmc.ncbi.nlm.nih.gov/articles/PMC10751838/).

## Điều chỉnh hướng phát triển

Có thể phát triển tiếp bằng dữ liệu mở. Tách ba nhánh nghiên cứu: chẩn đoán lỗi ổ bi từ UORED; phân biệt trạng thái mỡ từ chỉ số cảm biến 6204; theo dõi thay đổi theo thời gian từ DLR. Lớp nhiễm bẩn vẫn cần bản dữ liệu có đúng nhãn. Không ghép điểm ba nhánh thành một độ chính xác tổng.

Cần thêm bước kiểm tra chất lượng tín hiệu trước khi diễn giải chẩn đoán. Trường hợp dữ liệu vượt dải cảm biến phải được đánh dấu để kiểm tra cấu hình đo. Không dùng một công thức BPFO hay BPFI cho cả ổ bi quay liên tục, ổ kim dao động và ổ trượt.

## Vị trí và tái lập

Dữ liệu gốc nằm trong `data/open_sources`, được Git bỏ qua. Các tệp CSV và tài liệu nhỏ đã so MD5 với nguồn. Tệp cảm biến DLR được tải chọn lọc trong ZIP, xác nhận CRC và lưu SHA256; không tuyên bố đã xác nhận MD5 toàn bộ ZIP chưa tải. Metadata, lựa chọn thành viên và hash đều được giữ.

```powershell
python anchorspec/z_open_data.py lubrication_tables
python anchorspec/z_open_data.py dlr
python anchorspec/z_screen.py tables
python anchorspec/z_screen.py dlr
python anchorspec/z_report.py
python -m pytest -q anchorspec
```

Biểu đồ: `results/z/grease_states.png` và `results/z/dlr_replay.png`. Kết quả và giao thức không thay thế các báo cáo Y trước đó.
