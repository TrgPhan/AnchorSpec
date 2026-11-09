# Kiểm chứng trên ổ hỏng tự nhiên, 05/11/2026

Đợt U bổ sung XJTU-SY và sửa đối chứng sao chép. Đợt U2 thử surrogate đồng bộ giữa hai trục rung, đồng thời kiểm tra độ nhạy với dải đo. Kết quả là chẩn đoán có điều kiện, giả định hệ thống đầu vào đã báo bất thường đúng.

Phép thử chính trên một trục: chuyển nền phổ tăng macro recall từ 57.64% lên 61.85%. Khoảng bootstrap chênh lệch là 1.11 đến 7.82 điểm. Đây là bằng chứng thuận chiều có phạm vi; cấu hình này vẫn không nhận ra lớp vòng cách.

## Thay đổi có ý nghĩa so với đợt V

Bộ phân loại mới gộp các dòng có cùng đặc trưng và nhãn, cộng trọng số rồi học. SVM dùng gamma cố định; RF dùng điều kiện trọng số tối thiểu ở lá. Sao chép dữ liệu với cùng tổng trọng số cho xác suất dự đoán giống hệt mẫu thật ở tất cả phép thử. Vì vậy mức tăng do mẫu sinh không còn bị lẫn với việc chỉ nhân số dòng.

Đây là thay đổi quy trình đánh giá. Điểm của mô hình mới không được so với mô hình cũ rồi quy toàn bộ chênh lệch cho bộ sinh. Mọi bảng dưới đây giữ cùng bộ phân loại, đặc trưng và trọng số giữa các phương pháp.

## Dữ liệu và cách chia

Dùng 13 ổ bi có một bộ phận hỏng được xác định khi tháo kiểm tra: ba vòng trong, tám vòng ngoài, hai vòng cách. Loại hai ổ hỏng nhiều bộ phận theo quy định trước khi chạy. Mỗi ổ lấy mười bản ghi đầu, mười bản ghi cuối và mười bản ghi liền trước đoạn cuối. Mỗi bản ghi dài 1,28 giây, cách nhau một phút.

Đoạn đầu được giả định là nền khỏe, chưa có nhãn kiểm tra sức khỏe cho từng bản ghi. Đoạn cuối dùng nhãn tháo kiểm tra theo ổ, chưa xác nhận riêng từng phút đều đã có lỗi. Đoạn liền trước không được gọi là thời điểm bắt đầu lỗi. Mỗi lần đánh giá giữ toàn bộ ổ đích ngoài tập lỗi dùng để học và sinh. Lấy trung bình ba seed trước khi tính theo ổ và loại lỗi.

390 tệp được tải từ bản sao ZIP của thư viện rul-datasets, đối chiếu CRC và kích thước thành viên, lưu SHA256 cục bộ. Số bản ghi khớp tài liệu tác giả. Không có xác nhận SHA256 toàn bộ kho từ tác giả; không gọi CRC của bản sao là checksum do tác giả công bố.

## U: một trục, cùng dải giả định 8g

| Bộ phân loại | Phương pháp | Đoạn trước cuối | Đoạn cuối | Vòng trong | Vòng ngoài | Vòng cách |
|---|---|---:|---:|---:|---:|---:|
| svm1 | Chỉ mẫu thật | 47.64% | 57.64% | 76.67% | 96.25% | 0.00% |
| svm1 | Sao chép mẫu | 47.64% | 57.64% | 76.67% | 96.25% | 0.00% |
| svm1 | Surrogate cũ | 48.56% | 57.64% | 76.67% | 96.25% | 0.00% |
| svm1 | Giữ đường bao | 49.58% | 58.75% | 80.00% | 96.25% | 0.00% |
| svm1 | Trộn nền cùng ổ | 51.25% | 57.73% | 77.78% | 95.42% | 0.00% |
| svm1 | Chuyển nền phổ | 53.70% | 61.85% | 85.56% | 100.00% | 0.00% |
| svm1 | Chuyển nền và trộn | 51.25% | 60.00% | 80.00% | 100.00% | 0.00% |
| svm10 | Chỉ mẫu thật | 47.64% | 57.64% | 76.67% | 96.25% | 0.00% |
| svm10 | Sao chép mẫu | 47.64% | 57.64% | 76.67% | 96.25% | 0.00% |
| svm10 | Surrogate cũ | 50.93% | 60.09% | 84.44% | 95.83% | 0.00% |
| svm10 | Giữ đường bao | 58.61% | 62.08% | 90.00% | 96.25% | 0.00% |
| svm10 | Trộn nền cùng ổ | 60.79% | 60.28% | 83.33% | 97.50% | 0.00% |
| svm10 | Chuyển nền phổ | 53.52% | 63.70% | 91.11% | 100.00% | 0.00% |
| svm10 | Chuyển nền và trộn | 51.94% | 61.48% | 84.44% | 100.00% | 0.00% |
| rf | Chỉ mẫu thật | 63.70% | 70.93% | 94.44% | 100.00% | 18.33% |
| rf | Sao chép mẫu | 63.70% | 70.93% | 94.44% | 100.00% | 18.33% |
| rf | Surrogate cũ | 75.79% | 76.67% | 93.33% | 100.00% | 36.67% |
| rf | Giữ đường bao | 70.74% | 71.71% | 92.22% | 99.58% | 23.33% |
| rf | Trộn nền cùng ổ | 76.25% | 79.44% | 90.00% | 100.00% | 48.33% |
| rf | Chuyển nền phổ | 65.51% | 68.52% | 88.89% | 100.00% | 16.67% |
| rf | Chuyển nền và trộn | 67.69% | 71.30% | 82.22% | 100.00% | 31.67% |

SVM C1 và chuyển nền phổ là cấu hình chính đặt trước. RF và SVM C10 là kiểm tra độ nhạy. RF trộn nền cùng ổ có điểm cao hơn trong bảng này, nhưng không thay nó vào vị trí cấu hình chính sau khi xem điểm.

## U2: surrogate quay pha chung giữa các trục

Tên làm việc: Joint Envelope-Preserving Surrogate, viết tắt JEPS. Cùng một góc pha được áp dụng cho hai trục của một mẫu lỗi thật. Trước giới hạn cảm biến, phép biến đổi giữ phổ và đường bao giải tích của từng trục, đồng thời giữ phổ chéo giữa các trục, ngoại trừ thành phần DC và Nyquist không quay. Đây là tính chất của phép biến đổi tín hiệu, chưa chứng minh mọi mẫu sinh là một trạng thái cơ học độc lập.

Đối chứng quay pha riêng từng trục giữ các tính chất từng kênh nhưng làm thay đổi quan hệ pha giữa kênh. Cả hai dùng cùng chỉ số mẫu nguồn, cùng số biến thể và cùng tỷ trọng 0,25. Mẫu dự kiến vượt dải được thay bằng mẫu đo gốc, không dùng nhãn tập kiểm tra để chọn mẫu.

Mọi phương pháp U2 cùng dùng 96 đặc trưng: 45 trên mỗi trục và sáu đặc trưng quan hệ giữa hai trục. Không quy lợi ích của trục thứ hai cho bộ sinh. Cấu hình chính U2 là RF tại 8g. Các dải 16g, 64g là giả định để phân tích, chưa gắn với thiết bị giá rẻ đã chọn.

| Dải giả định | Bộ phân loại | Phương pháp | Đoạn trước cuối | Đoạn cuối | Vòng cách đoạn cuối |
|---|---|---|---:|---:|---:|
| 8g | rf | Chỉ mẫu thật | 65.51% | 62.22% | 0.00% |
| 8g | rf | Sao chép mẫu | 65.51% | 62.22% | 0.00% |
| 8g | rf | Surrogate cũ | 61.20% | 63.33% | 0.00% |
| 8g | rf | Quay pha riêng từng trục | 64.91% | 63.70% | 0.00% |
| 8g | rf | Quay pha chung các trục | 63.24% | 63.33% | 0.00% |
| 8g | svm1 | Chỉ mẫu thật | 36.67% | 51.11% | 0.00% |
| 8g | svm1 | Sao chép mẫu | 36.67% | 51.11% | 0.00% |
| 8g | svm1 | Surrogate cũ | 36.67% | 49.26% | 0.00% |
| 8g | svm1 | Quay pha riêng từng trục | 35.56% | 51.11% | 0.00% |
| 8g | svm1 | Quay pha chung các trục | 35.93% | 49.63% | 0.00% |
| 8g | svm10 | Chỉ mẫu thật | 36.67% | 51.11% | 0.00% |
| 8g | svm10 | Sao chép mẫu | 36.67% | 51.11% | 0.00% |
| 8g | svm10 | Surrogate cũ | 37.59% | 53.33% | 0.00% |
| 8g | svm10 | Quay pha riêng từng trục | 35.56% | 50.74% | 0.00% |
| 8g | svm10 | Quay pha chung các trục | 35.93% | 49.63% | 0.00% |
| 16g | rf | Chỉ mẫu thật | 60.00% | 59.44% | 15.00% |
| 16g | rf | Sao chép mẫu | 60.00% | 59.44% | 15.00% |
| 16g | rf | Surrogate cũ | 64.91% | 61.11% | 16.67% |
| 16g | rf | Quay pha riêng từng trục | 62.31% | 64.44% | 23.33% |
| 16g | rf | Quay pha chung các trục | 65.97% | 63.52% | 21.67% |
| 16g | svm1 | Chỉ mẫu thật | 45.14% | 45.56% | 0.00% |
| 16g | svm1 | Sao chép mẫu | 45.14% | 45.56% | 0.00% |
| 16g | svm1 | Surrogate cũ | 45.14% | 45.19% | 0.00% |
| 16g | svm1 | Quay pha riêng từng trục | 45.88% | 45.56% | 0.00% |
| 16g | svm1 | Quay pha chung các trục | 46.25% | 45.56% | 0.00% |
| 16g | svm10 | Chỉ mẫu thật | 45.14% | 45.56% | 0.00% |
| 16g | svm10 | Sao chép mẫu | 45.14% | 45.56% | 0.00% |
| 16g | svm10 | Surrogate cũ | 48.38% | 45.56% | 0.00% |
| 16g | svm10 | Quay pha riêng từng trục | 46.25% | 45.56% | 0.00% |
| 16g | svm10 | Quay pha chung các trục | 47.13% | 45.56% | 0.00% |
| 64g | rf | Chỉ mẫu thật | 68.98% | 58.15% | 30.00% |
| 64g | rf | Sao chép mẫu | 68.98% | 58.15% | 30.00% |
| 64g | rf | Surrogate cũ | 66.81% | 53.52% | 21.67% |
| 64g | rf | Quay pha riêng từng trục | 69.07% | 56.30% | 26.67% |
| 64g | rf | Quay pha chung các trục | 69.44% | 55.93% | 30.00% |
| 64g | svm1 | Chỉ mẫu thật | 46.67% | 43.33% | 0.00% |
| 64g | svm1 | Sao chép mẫu | 46.67% | 43.33% | 0.00% |
| 64g | svm1 | Surrogate cũ | 48.61% | 44.07% | 0.00% |
| 64g | svm1 | Quay pha riêng từng trục | 46.67% | 44.44% | 0.00% |
| 64g | svm1 | Quay pha chung các trục | 46.67% | 44.44% | 0.00% |
| 64g | svm10 | Chỉ mẫu thật | 46.67% | 43.33% | 0.00% |
| 64g | svm10 | Sao chép mẫu | 46.67% | 43.33% | 0.00% |
| 64g | svm10 | Surrogate cũ | 50.23% | 44.44% | 0.00% |
| 64g | svm10 | Quay pha riêng từng trục | 47.41% | 44.81% | 0.00% |
| 64g | svm10 | Quay pha chung các trục | 46.67% | 44.44% | 0.00% |

U2 được thiết kế sau khi đã xem U trên cùng dữ liệu. Đây là nghiên cứu tiếp, không phải xác nhận độc lập.

## Ảnh hưởng của dải đo

| Dải | Ngang, trung bình theo ổ | Ngang, ổ cao nhất | Dọc, trung bình theo ổ | Dọc, ổ cao nhất |
|---|---:|---:|---:|---:|
| 8g | 11.51% | 35.57% | 20.79% | 61.34% |
| 16g | 1.20% | 6.45% | 4.40% | 28.31% |
| 64g | 0.00% | 0.00% | 0.00% | 0.00% |

Bảng là tỷ lệ mẫu tín hiệu gốc ở đoạn cuối vượt dải giả định, trước hạ mẫu và lọc. Bão hòa đầu vào có thể làm mất thông tin; tăng số mẫu sinh không phục hồi được thông tin đã mất. Chưa kết luận một dải đo phù hợp chỉ dựa trên điểm phân loại.

| Dải | JEPS dùng lại mẫu gốc, trung bình | Trường hợp cao nhất |
|---|---:|---:|
| 8g | 82.41% | 100.00% |
| 16g | 33.01% | 100.00% |
| 64g | 0.00% | 0.00% |

## Kiểm tra lại UORED sau khi sửa đối chứng

| Số ổ nguồn mỗi loại | Bộ phân loại | Chỉ mẫu thật, lỗi nặng | Surrogate cũ, lỗi nặng | Giữ đường bao, lỗi nặng | Chuyển nền phổ, lỗi nặng |
|---|---|---:|---:|---:|---:|
| 1 | svm1 | 51.32% | 47.63% | 53.25% | 47.46% |
| 1 | svm10 | 51.58% | 50.79% | 52.72% | 48.51% |
| 1 | rf | 52.46% | 45.00% | 47.81% | 45.00% |
| 2 | svm1 | 48.95% | 51.75% | 48.33% | 54.65% |
| 2 | svm10 | 50.35% | 54.04% | 54.04% | 53.60% |
| 2 | rf | 60.00% | 57.46% | 57.46% | 50.44% |
| 4 | svm1 | 59.65% | 57.46% | 64.04% | 58.68% |
| 4 | svm10 | 57.89% | 55.61% | 60.88% | 58.68% |
| 4 | rf | 63.77% | 67.72% | 69.74% | 59.12% |

Toàn bộ kết quả từng trạng thái, lớp và cấu hình nằm trong JSON. UORED đã được dùng nhiều lần nên kết quả này là kiểm tra lại, không phải xác nhận ngoài tập phát triển.

## Tiêu chí đã đặt trước và giới hạn

- U một trục, primary transport SVM C1: chưa qua đầy đủ tiêu chí.
- U2 hai trục, primary JEPS RF tại 8g: chưa qua đầy đủ tiêu chí.
- Đối chứng sao chép: dự đoán giống hệt mẫu thật trong cả ba đợt kiểm tra.
- Chỉ có hai ổ vòng cách; sai số và khả năng tổng quát của lớp này chưa đủ chắc chắn.
- Bootstrap theo ổ chỉ có tính thăm dò vì các tập huấn luyện chồng nhau; không coi seed hoặc cửa sổ là thử nghiệm độc lập.
- Trung bình nhân quả năm bản ghi tương ứng khoảng năm phút trong dữ liệu này, không phải năm giây.
- Chưa xác nhận cảm biến DENSO, thiếu bôi trơn, tạp chất, báo nhầm dài ngày hoặc dự báo giờ hỏng.

## Tái lập

```powershell
python anchorspec/u_download.py
python anchorspec/u_natural.py prepare
python anchorspec/u_natural.py run
python anchorspec/u_retrospective.py
python anchorspec/u_joint.py prepare
python anchorspec/u_joint.py run
python anchorspec/u_report.py
```

Các nguồn UORED và cache V cần có trước khi chạy kiểm tra lại. Mọi source hash lưu trong kết quả; dữ liệu gốc và cache nằm trong data, không đưa vào Git.

- [Nguồn XJTU-SY của tác giả](https://github.com/WangBiaoXJTU/xjtu-sy-bearing-datasets).
- [Bài báo XJTU-SY](https://doi.org/10.1109/TR.2018.2882682).
- [Mã thư viện công bố đường dẫn bản sao dữ liệu](https://github.com/tilman151/rul-datasets/blob/master/rul_datasets/reader/xjtu_sy.py).
- [Protocol U](PROTOCOL_U_NATURAL.md).
- [Protocol U2](PROTOCOL_U_JOINT.md).
