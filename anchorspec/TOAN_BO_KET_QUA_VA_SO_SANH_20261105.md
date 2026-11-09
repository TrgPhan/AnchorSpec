# Toàn bộ kết quả và đối chiếu phương pháp, 05/11/2026

Bản tổng hợp đọc kết quả đã lưu, không chạy lại hoặc chọn lại mô hình. Mỗi bảng có nguồn và điều kiện. Không xếp hạng chung bằng cách so điểm giữa các bộ dữ liệu hoặc các nhiệm vụ khác nhau.

## Đọc bảng như thế nào

- Trừ nơi ghi riêng, số trong bảng là phần trăm macro recall: trung bình recall của từng loại lỗi, không phải accuracy.
- Conditional giả định đầu vào đã xác nhận bất thường, chỉ chọn lớp lỗi. T selective xét cả lớp khỏe và từ chối; hai loại điểm không thay thế nhau.
- CWRU, KAIST, HUST, UORED và XJTU không có cùng số lớp, độ khó, đặc điểm hỏng hoặc đơn vị bằng chứng.
- Số seed, số cửa sổ và số cấu hình không phải số máy hoặc sự kiện lỗi độc lập.
- V và các đợt trước có trường hợp bản sao đổi dự đoán; từ U dùng classifier invariant để bản sao cho kết quả giống mẫu thật. Không quy toàn bộ gain cũ cho chất lượng mẫu sinh.
- Các đợt dùng lại dữ liệu là thăm dò. Bảng lưu cả kết quả âm; điểm cao nhất chưa đủ chứng minh thắng ổn định.

## Các phương pháp đã thử

| Nhóm | Ý nghĩa |
|---|---|
| Mẫu thật | Đối chứng không bổ sung dữ liệu tổng hợp. |
| Simple | Các biến đổi tín hiệu đơn giản trong release CWRU ban đầu. |
| Constrained surrogate | Tạo biến thể từ mẫu lỗi thật, ràng buộc phổ và phân bố biên độ. Không sinh cơ chế lỗi chưa có. |
| Physics không neo, có neo, hiệu chỉnh | Ba biến thể mô hình tín hiệu lỗi vật lý trong bản CWRU. |
| DDPM prototype | Mô hình sinh học sâu thử trên CWRU; không coi là tái lập đầy đủ một paper hoặc so compute ngang nhau. |
| Cấy lỗi vật lý | Thêm thành phần xung lỗi vào nền khỏe trong các nhánh AnchorSpec. |
| Surrogate giữ đường bao | Quay pha chung để giữ phổ và đường bao trước giới hạn cảm biến. |
| Trộn nền cùng ổ | Trộn mẫu lỗi và nền khỏe của chính ổ nguồn để tạo biến thể. |
| Chuyển nền phổ | Điều chỉnh tín hiệu nguồn bằng tương quan phổ khỏe nguồn và đích. |
| Chuyển nền và trộn | Chuyển phổ rồi trộn nền khỏe đích. |
| Quay pha chung hai trục | Giữ quan hệ giữa hai trục trước lượng tử hóa; có fallback khi vượt dải. |
| Selector, phân tầng, căn chỉnh nền | Thay đổi cách học, quyết định hoặc đặc trưng; không tự thân là bộ sinh mới. |

## 1. Bản CWRU ban đầu

Train tải 0 HP, development 1 HP, healthy calibration 2 HP và final tải 3 HP. Chưa xác nhận là các ổ vật lý khác nhau. Recall cảnh báo và accuracy phân loại là hai endpoint khác nhau.

| Phương pháp | Recall cảnh báo lỗi | FPR khỏe | Accuracy bốn lớp | Macro F1 |
|---|---:|---:|---:|---:|
| real_only | 100.00 | 4.52 | 99.72 | 99.72 |
| simple | 100.00 | 7.34 | 99.02 | 99.01 |
| constrained_surrogate | 100.00 | 20.90 | 99.86 | 99.86 |
| physics_unanchored | 100.00 | 23.16 | 99.58 | 99.58 |
| physics_anchored | 100.00 | 6.78 | 99.58 | 99.58 |
| physics_calibrated | 100.00 | 16.95 | 99.86 | 99.86 |
| ddpm_prototype | 100.00 | 6.78 | 100.00 | 100.00 |
| healthy_only | 98.31 | 23.73 | Không áp dụng | Không áp dụng |

Lựa chọn trước test là real_only. Surrogate không tăng recall cảnh báo và làm FPR tăng. DDPM đạt accuracy cao trong phép thử này nhưng không vượt cổng utility; không dùng 100% CWRU để khẳng định sẵn sàng tại DENSO.

[Báo cáo CWRU đầy đủ](../generator_benchmark/mvp_release_20261007/REPORT.md).

## 2. Y và W: cấy lỗi vật lý, surrogate và thay đổi mô hình

Các nhánh legacy, W và Y có cách học khác nhau. Chỉ đối chiếu tác dụng bộ sinh với real của chính nhánh đó. Bảng W dưới đây giữ mọi ngân sách và hai trạng thái; early là đang phát triển, late là lỗi nặng.

### W UORED, số sự kiện mỗi loại 1



Nguồn: [results/w/summary.json](results/w/summary.json). Cấu hình: budget=1; bộ phân loại: Theo tên nhánh.

| Phương pháp | early | late |
|---|---:|---:|
| legacy_real | 52.28 | 40.96 |
| legacy_physics | 39.04 | 32.98 |
| legacy_surrogate | 48.42 | 40.44 |
| Mẫu thật | 51.58 | 40.44 |
| surrogate_ring | 53.77 | 44.12 |
| physics | 45.61 | 38.77 |
| surrogate_all | 43.51 | 37.63 |
| select | 51.58 | 40.44 |

### W UORED, số sự kiện mỗi loại 2



Nguồn: [results/w/summary.json](results/w/summary.json). Cấu hình: budget=2; bộ phân loại: Theo tên nhánh.

| Phương pháp | early | late |
|---|---:|---:|
| legacy_real | 54.39 | 45.26 |
| legacy_physics | 40.35 | 34.91 |
| legacy_surrogate | 51.84 | 44.65 |
| Mẫu thật | 60.53 | 56.23 |
| surrogate_ring | 61.49 | 55.88 |
| physics | 48.25 | 52.72 |
| surrogate_all | 55.44 | 40.88 |
| select | 51.40 | 45.35 |

### W UORED, số sự kiện mỗi loại 4



Nguồn: [results/w/summary.json](results/w/summary.json). Cấu hình: budget=4; bộ phân loại: Theo tên nhánh.

| Phương pháp | early | late |
|---|---:|---:|
| legacy_real | 68.77 | 60.09 |
| legacy_physics | 49.39 | 42.37 |
| legacy_surrogate | 68.86 | 61.40 |
| Mẫu thật | 60.00 | 47.98 |
| surrogate_ring | 63.33 | 53.60 |
| physics | 54.12 | 51.49 |
| surrogate_all | 60.53 | 52.98 |
| select | 58.51 | 55.35 |

#### Bảng lịch sử từ [RESULTS_Y_LOCAL.md](RESULTS_Y_LOCAL.md)

**Kết quả cân bằng theo lớp**

| Sự kiện mỗi loại | Chỉ cấy lỗi | Chỉ lỗi thật, z | Ghép cố định, z | Phân tầng, z | Chỉ lỗi thật, có chọn biểu diễn | AnchorSpec-E thích nghi |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 20.9% | 31.8% | 33.0% | 34.6% | 31.8% | 35.2% |
| 2 | 20.9% | 42.3% | 34.9% | 41.7% | 52.1% | 44.1% |
| 4 | 20.9% | 59.9% | 42.4% | 59.2% | 57.6% | 49.1% |

**Sự kiện đến dần**

| Sự kiện tổng cộng | Chỉ cấy lỗi | Chỉ lỗi thật, z | Ghép cố định, z | Phân tầng, z | Chỉ lỗi thật, có chọn biểu diễn | AnchorSpec-E thích nghi |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 20.9% | 0.0% | 20.9% | 20.9% | 0.0% | 20.9% |
| 2 | 20.9% | 9.6% | 28.8% | 10.4% | 9.6% | 26.3% |
| 4 | 20.9% | 19.6% | 33.2% | 19.3% | 20.9% | 37.4% |
| 8 | 20.9% | 24.9% | 31.2% | 29.1% | 33.2% | 29.0% |
| 12 | 20.9% | 33.9% | 40.6% | 38.1% | 31.1% | 40.0% |

**Đối chứng biểu diễn cố định**

| Biểu diễn | Sự kiện mỗi loại | Chỉ lỗi thật | Ghép cố định | Phân tầng |
|---|---|---:|---:|---:|
| z | 1 | 31.8% | 33.0% | 34.6% |
| z | 2 | 42.3% | 34.9% | 41.7% |
| z | 4 | 59.9% | 42.4% | 59.2% |
| delta | 1 | 30.9% | 38.6% | 33.7% |
| delta | 2 | 40.8% | 39.0% | 38.6% |
| delta | 4 | 52.5% | 50.1% | 58.7% |
| raw | 1 | 36.6% | 42.7% | 25.5% |
| raw | 2 | 54.3% | 41.8% | 44.6% |
| raw | 4 | 64.9% | 56.7% | 63.1% |
| both | 1 | 30.4% | 38.9% | 35.7% |
| both | 2 | 55.4% | 44.7% | 39.1% |
| both | 4 | 54.5% | 57.0% | 57.5% |

**Giai đoạn sớm và báo nhầm khỏe**

| Sự kiện mỗi loại | Lỗi sớm, ghép cố định | Lỗi sớm, AnchorSpec-E | Báo nhầm khỏe, ghép cố định | Báo nhầm khỏe, AnchorSpec-E |
|---|---:|---:|---:|---:|
| 1 | 39.0% | 47.2% | 9.0% | 7.6% |
| 2 | 40.4% | 50.0% | 11.0% | 4.5% |
| 4 | 49.4% | 52.5% | 10.2% | 5.0% |

**Từng loại lỗi**

| Sự kiện mỗi loại | Phương pháp | Vòng trong | Vòng ngoài | Bi | Vòng cách |
|---|---|---:|---:|---:|---:|
| 1 | Ghép cố định, z | 75.4% | 56.5% | 0.0% | 0.0% |
| 1 | Chỉ lỗi thật, có chọn biểu diễn | 45.6% | 8.4% | 40.0% | 33.3% |
| 1 | AnchorSpec-E thích nghi | 75.8% | 51.6% | 0.0% | 13.3% |
| 2 | Ghép cố định, z | 75.1% | 50.2% | 14.4% | 0.0% |
| 2 | Chỉ lỗi thật, có chọn biểu diễn | 91.6% | 27.4% | 60.4% | 29.1% |
| 2 | AnchorSpec-E thích nghi | 89.1% | 30.9% | 33.0% | 23.5% |
| 4 | Ghép cố định, z | 69.5% | 68.4% | 24.9% | 6.7% |
| 4 | Chỉ lỗi thật, có chọn biểu diễn | 87.4% | 38.2% | 50.5% | 54.4% |
| 4 | AnchorSpec-E thích nghi | 66.7% | 50.2% | 48.4% | 31.2% |

**Kiểm tra nhãn sai**

| Phương pháp | Nhãn đúng | Nhãn bị hoán vị |
|---|---:|---:|
| Chỉ cấy lỗi | 20.9% | 20.9% |
| Chỉ lỗi thật, z | 31.8% | 13.3% |
| Ghép cố định, z | 33.0% | 27.3% |
| Phân tầng, z | 34.6% | 11.8% |
| Chỉ lỗi thật, có chọn biểu diễn | 31.8% | 13.3% |
| AnchorSpec-E thích nghi | 35.2% | 16.8% |

#### Bảng lịch sử từ [RESULTS_Y_DIAGNOSIS.md](RESULTS_Y_DIAGNOSIS.md)

**Đối chứng SVM có kiểm tra theo sự kiện**

| Sự kiện mỗi loại | Ghép RF cũ | SVM có chọn trọng số vật lý | SVM chỉ dùng lỗi thật |
|---|---:|---:|---:|
| 1 | 33.0% | 42.9% | 22.4% |
| 2 | 34.9% | 42.1% | 38.9% |
| 4 | 42.4% | 44.7% | 45.5% |

**Đủ lớp từ đầu**

| Số sự kiện mỗi loại | RF ghép cũ | Chọn theo nhiệm vụ chẩn đoán | Chỉ lỗi thật, cùng cách chọn |
|---|---:|---:|---:|
| 1 | 33.0% | 35.8% | 41.0% |
| 2 | 34.9% | 56.5% | 63.6% |
| 4 | 42.4% | 55.6% | 66.7% |

**Sự kiện đến dần**

| Số sự kiện tổng cộng | RF ghép cũ | Chọn theo nhiệm vụ chẩn đoán | Chỉ lỗi thật, cùng cách chọn |
|---|---:|---:|---:|
| 0 | 21.0% | 21.0% | 0.0% |
| 2 | 29.0% | 24.0% | 31.2% |
| 4 | 33.2% | 29.1% | 25.8% |
| 8 | 31.2% | 34.2% | 45.3% |
| 12 | 40.6% | 45.7% | 40.4% |

**Từng lớp ở nhánh chẩn đoán mới**

| Sự kiện mỗi loại | Vòng trong | Vòng ngoài | Bi | Vòng cách | Giai đoạn sớm, bốn lớp |
|---|---:|---:|---:|---:|---:|
| 1 | 82.8% | 60.4% | 0.0% | 0.0% | 41.2% |
| 2 | 82.5% | 62.1% | 53.3% | 28.1% | 61.3% |
| 4 | 74.4% | 69.1% | 56.5% | 22.5% | 58.0% |

#### Bảng lịch sử từ [KET_QUA_VA_DEMO_20261104.md](KET_QUA_VA_DEMO_20261104.md)

**UORED: cùng 20 ổ, cùng donor, bốn loại lỗi**

| Phương án | 1 sự kiện | 2 sự kiện | 4 sự kiện |
|---|---:|---:|---:|
| RF cũ, chỉ dữ liệu thật | 41.0% | 45.3% | 60.1% |
| RF cũ, thêm cấy lỗi | 33.0% | 34.9% | 42.4% |
| RF cũ, thêm surrogate | 40.4% | 44.6% | 61.4% |
| Chỉ dữ liệu thật W | 40.4% | 56.2% | 48.0% |
| Surrogate hai lớp vòng | 44.1% | 55.9% | 53.6% |
| Cấy lỗi vật lý W | 38.8% | 52.7% | 51.5% |
| Surrogate mọi lớp | 37.6% | 40.9% | 53.0% |
| Chọn nguồn W | 40.4% | 45.4% | 55.4% |
| Chỉ lỗi thật Y | 41.0% | 63.6% | 66.7% |
| Phổ cố định | 39.6% | 60.7% | 62.5% |
| Ghép đặc trưng cố định | 42.5% | 62.5% | 65.7% |
| Chọn biểu diễn phổ | 40.4% | 61.3% | 63.2% |
| Thêm biên độ vào Y | Không chạy | 55.9% | 57.5% |
| Thêm phổ và biên độ vào Y | Không chạy | 51.8% | 65.9% |
| Chọn view có biên độ | Không chạy | 57.1% | 66.2% |

**Phân tầng: kết quả hứa hẹn ở lỗi đang phát triển**

| Trạng thái UORED | Đối chứng Y | Phân tầng |
|---|---:|---:|
| Lỗi đang phát triển | 70.3% | 81.1% |
| Lỗi nặng | 66.7% | 62.8% |

**KAIST: nguồn mới cho chuyển tải và mức khuyết tật**

| Phương án | Macro recall |
|---|---:|
| Chỉ dữ liệu thật W | 99.14% |
| Surrogate hai lớp vòng | 99.92% |
| Cấy lỗi vật lý W | 95.06% |
| Surrogate mọi lớp | 99.92% |
| Chọn nguồn W | 99.14% |
| RF cũ, chỉ dữ liệu thật | 99.22% |
| RF cũ, thêm cấy lỗi | 94.88% |
| RF cũ, thêm surrogate | 98.20% |
| Chỉ dữ liệu thật Y | 99.22% |

## 3. V: chuyển nền, kiểm tra KAIST và HUST

Các điểm V còn chịu ảnh hưởng implementation mà bản sao có thể thay đổi classifier. HUST có hai giả định quy đổi đơn vị g và mks, không phải hai bộ dữ liệu độc lập. Khác tải có thể vẫn cùng specimen.

### kaist_transport.json metadata svm1



Nguồn: [results/v/kaist_transport.json](results/v/kaist_transport.json). Cấu hình: unit=metadata; bộ phân loại: svm1.

| Phương pháp | test |
|---|---:|
| Mẫu thật | 79.66 |
| Sao chép | 80.74 |
| Surrogate cũ | 79.77 |
| Trộn nền cùng ổ | 81.26 |
| Chuyển nền phổ | 80.99 |
| Chuyển nền và trộn | 80.34 |

### kaist_transport.json metadata svm10



Nguồn: [results/v/kaist_transport.json](results/v/kaist_transport.json). Cấu hình: unit=metadata; bộ phân loại: svm10.

| Phương pháp | test |
|---|---:|
| Mẫu thật | 80.08 |
| Sao chép | 81.54 |
| Surrogate cũ | 82.11 |
| Trộn nền cùng ổ | 82.00 |
| Chuyển nền phổ | 81.29 |
| Chuyển nền và trộn | 80.43 |

### kaist_transport.json metadata rf



Nguồn: [results/v/kaist_transport.json](results/v/kaist_transport.json). Cấu hình: unit=metadata; bộ phân loại: rf.

| Phương pháp | test |
|---|---:|
| Mẫu thật | 98.79 |
| Sao chép | 100.00 |
| Surrogate cũ | 100.00 |
| Trộn nền cùng ổ | 98.82 |
| Chuyển nền phổ | 100.00 |
| Chuyển nền và trộn | 99.95 |

### hust_transport.json g svm1



Nguồn: [results/v/hust_transport.json](results/v/hust_transport.json). Cấu hình: unit=g; bộ phân loại: svm1.

| Phương pháp | test |
|---|---:|
| Mẫu thật | 88.73 |
| Sao chép | 89.51 |
| Surrogate cũ | 91.26 |
| Trộn nền cùng ổ | 90.43 |
| Chuyển nền phổ | 91.39 |
| Chuyển nền và trộn | 92.19 |

### hust_transport.json g svm10



Nguồn: [results/v/hust_transport.json](results/v/hust_transport.json). Cấu hình: unit=g; bộ phân loại: svm10.

| Phương pháp | test |
|---|---:|
| Mẫu thật | 88.73 |
| Sao chép | 89.51 |
| Surrogate cũ | 89.50 |
| Trộn nền cùng ổ | 91.80 |
| Chuyển nền phổ | 92.84 |
| Chuyển nền và trộn | 93.50 |

### hust_transport.json g rf



Nguồn: [results/v/hust_transport.json](results/v/hust_transport.json). Cấu hình: unit=g; bộ phân loại: rf.

| Phương pháp | test |
|---|---:|
| Mẫu thật | 93.16 |
| Sao chép | 93.09 |
| Surrogate cũ | 93.29 |
| Trộn nền cùng ổ | 90.13 |
| Chuyển nền phổ | 93.40 |
| Chuyển nền và trộn | 91.93 |

### hust_transport.json mks svm1



Nguồn: [results/v/hust_transport.json](results/v/hust_transport.json). Cấu hình: unit=mks; bộ phân loại: svm1.

| Phương pháp | test |
|---|---:|
| Mẫu thật | 79.48 |
| Sao chép | 79.94 |
| Surrogate cũ | 81.07 |
| Trộn nền cùng ổ | 80.59 |
| Chuyển nền phổ | 84.72 |
| Chuyển nền và trộn | 83.27 |

### hust_transport.json mks svm10



Nguồn: [results/v/hust_transport.json](results/v/hust_transport.json). Cấu hình: unit=mks; bộ phân loại: svm10.

| Phương pháp | test |
|---|---:|
| Mẫu thật | 80.40 |
| Sao chép | 80.86 |
| Surrogate cũ | 85.65 |
| Trộn nền cùng ổ | 86.26 |
| Chuyển nền phổ | 86.83 |
| Chuyển nền và trộn | 85.78 |

### hust_transport.json mks rf



Nguồn: [results/v/hust_transport.json](results/v/hust_transport.json). Cấu hình: unit=mks; bộ phân loại: rf.

| Phương pháp | test |
|---|---:|
| Mẫu thật | 83.43 |
| Sao chép | 82.13 |
| Surrogate cũ | 82.77 |
| Trộn nền cùng ổ | 82.51 |
| Chuyển nền phổ | 84.72 |
| Chuyển nền và trộn | 83.28 |

### holdout6204.json g svm1



Nguồn: [results/v/holdout6204.json](results/v/holdout6204.json). Cấu hình: unit=g; bộ phân loại: svm1.

| Phương pháp | test |
|---|---:|
| Mẫu thật | 82.41 |
| Sao chép | 82.41 |
| Surrogate cũ | 82.41 |
| Trộn nền cùng ổ | 81.48 |
| Chuyển nền phổ | 81.48 |
| Chuyển nền và trộn | 80.56 |

### holdout6204.json g svm10



Nguồn: [results/v/holdout6204.json](results/v/holdout6204.json). Cấu hình: unit=g; bộ phân loại: svm10.

| Phương pháp | test |
|---|---:|
| Mẫu thật | 82.41 |
| Sao chép | 82.41 |
| Surrogate cũ | 81.48 |
| Trộn nền cùng ổ | 84.26 |
| Chuyển nền phổ | 82.10 |
| Chuyển nền và trộn | 82.10 |

### holdout6204.json g rf



Nguồn: [results/v/holdout6204.json](results/v/holdout6204.json). Cấu hình: unit=g; bộ phân loại: rf.

| Phương pháp | test |
|---|---:|
| Mẫu thật | 98.77 |
| Sao chép | 94.14 |
| Surrogate cũ | 95.37 |
| Trộn nền cùng ổ | 94.75 |
| Chuyển nền phổ | 98.15 |
| Chuyển nền và trộn | 99.38 |

### holdout6204.json mks svm1



Nguồn: [results/v/holdout6204.json](results/v/holdout6204.json). Cấu hình: unit=mks; bộ phân loại: svm1.

| Phương pháp | test |
|---|---:|
| Mẫu thật | 83.33 |
| Sao chép | 83.33 |
| Surrogate cũ | 76.54 |
| Trộn nền cùng ổ | 87.35 |
| Chuyển nền phổ | 70.68 |
| Chuyển nền và trộn | 76.54 |

### holdout6204.json mks svm10



Nguồn: [results/v/holdout6204.json](results/v/holdout6204.json). Cấu hình: unit=mks; bộ phân loại: svm10.

| Phương pháp | test |
|---|---:|
| Mẫu thật | 83.33 |
| Sao chép | 83.33 |
| Surrogate cũ | 84.57 |
| Trộn nền cùng ổ | 93.52 |
| Chuyển nền phổ | 80.86 |
| Chuyển nền và trộn | 85.49 |

### holdout6204.json mks rf



Nguồn: [results/v/holdout6204.json](results/v/holdout6204.json). Cấu hình: unit=mks; bộ phân loại: rf.

| Phương pháp | test |
|---|---:|
| Mẫu thật | 94.75 |
| Sao chép | 89.20 |
| Surrogate cũ | 96.91 |
| Trộn nền cùng ổ | 91.67 |
| Chuyển nền phổ | 99.38 |
| Chuyển nền và trộn | 95.68 |

### V trên cấu hình Y, budget 1



Nguồn: [results/v/champion_augmentation.json](results/v/champion_augmentation.json). Cấu hình: budget=1; bộ phân loại: Diagnostic Y.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 52.28 | 40.96 |
| duplicate_0.25 | 46.49 | 40.79 |
| surrogate_0.25 | 48.42 | 40.53 |
| severity_0.25 | 52.37 | 43.95 |
| transport_0.25 | 58.60 | 46.14 |
| transport_mix_0.25 | 58.16 | 44.56 |
| envelope_0.25 | 52.37 | 45.26 |
| duplicate_0.5 | 50.53 | 40.96 |
| surrogate_0.5 | 47.89 | 43.51 |
| severity_0.5 | 50.70 | 37.54 |
| transport_0.5 | 58.95 | 42.54 |
| transport_mix_0.5 | 54.82 | 45.44 |
| envelope_0.5 | 52.63 | 45.18 |

### V trên cấu hình Y, budget 2



Nguồn: [results/v/champion_augmentation.json](results/v/champion_augmentation.json). Cấu hình: budget=2; bộ phân loại: Diagnostic Y.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 63.77 | 63.60 |
| duplicate_0.25 | 64.56 | 61.49 |
| surrogate_0.25 | 60.61 | 55.26 |
| severity_0.25 | 62.72 | 55.61 |
| transport_0.25 | 61.23 | 56.67 |
| transport_mix_0.25 | 66.40 | 56.23 |
| envelope_0.25 | 61.93 | 59.12 |
| duplicate_0.5 | 62.63 | 58.42 |
| surrogate_0.5 | 62.28 | 57.63 |
| severity_0.5 | 63.42 | 55.44 |
| transport_0.5 | 63.86 | 54.21 |
| transport_mix_0.5 | 61.84 | 53.60 |
| envelope_0.5 | 60.96 | 57.28 |

### V trên cấu hình Y, budget 4



Nguồn: [results/v/champion_augmentation.json](results/v/champion_augmentation.json). Cấu hình: budget=4; bộ phân loại: Diagnostic Y.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 70.26 | 66.67 |
| duplicate_0.25 | 68.95 | 66.49 |
| surrogate_0.25 | 69.65 | 68.60 |
| severity_0.25 | 68.33 | 66.32 |
| transport_0.25 | 70.53 | 68.68 |
| transport_mix_0.25 | 69.30 | 64.47 |
| envelope_0.25 | 71.23 | 67.46 |
| duplicate_0.5 | 66.14 | 67.19 |
| surrogate_0.5 | 72.63 | 68.60 |
| severity_0.5 | 66.40 | 65.88 |
| transport_0.5 | 67.46 | 66.23 |
| transport_mix_0.5 | 66.40 | 57.37 |
| envelope_0.5 | 66.49 | 67.89 |

Bảng V transport UORED với mọi budget và CI: [báo cáo V](KIEM_CHUNG_DU_LIEU_SINH_20261104.md). Các giá trị gốc cũng nằm trong archive_metrics.csv.

## 4. U: đối chứng sao chép đã sửa, lỗi tự nhiên XJTU

Một trục, dải giả định8g, healthy10snapshot làm tham chiếu,13ổ. early là đoạn trước cuối; late là đoạn cuối, không đồng nghĩa early onset. Chẩn đoán conditional. Primary SVM1 transport; RF và SVM10 là sensitivity.

### XJTU svm1



Nguồn: [results/u/natural.json](results/u/natural.json). Cấu hình: single axis, 8g, healthy10; bộ phân loại: svm1.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 47.64 | 57.64 |
| Sao chép | 47.64 | 57.64 |
| Surrogate cũ | 48.56 | 57.64 |
| Surrogate giữ đường bao | 49.58 | 58.75 |
| Trộn nền cùng ổ | 51.25 | 57.73 |
| Chuyển nền phổ | 53.70 | 61.85 |
| Chuyển nền và trộn | 51.25 | 60.00 |

### XJTU svm10



Nguồn: [results/u/natural.json](results/u/natural.json). Cấu hình: single axis, 8g, healthy10; bộ phân loại: svm10.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 47.64 | 57.64 |
| Sao chép | 47.64 | 57.64 |
| Surrogate cũ | 50.93 | 60.09 |
| Surrogate giữ đường bao | 58.61 | 62.08 |
| Trộn nền cùng ổ | 60.79 | 60.28 |
| Chuyển nền phổ | 53.52 | 63.70 |
| Chuyển nền và trộn | 51.94 | 61.48 |

### XJTU rf



Nguồn: [results/u/natural.json](results/u/natural.json). Cấu hình: single axis, 8g, healthy10; bộ phân loại: rf.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 63.70 | 70.93 |
| Sao chép | 63.70 | 70.93 |
| Surrogate cũ | 75.79 | 76.67 |
| Surrogate giữ đường bao | 70.74 | 71.71 |
| Trộn nền cùng ổ | 76.25 | 79.44 |
| Chuyển nền phổ | 65.51 | 68.52 |
| Chuyển nền và trộn | 67.69 | 71.30 |

## 5. U: kiểm tra lại UORED, mọi ngân sách và classifier

Bốn loại lỗi; ngân sách là số ổ nguồn mỗi loại. early là đang phát triển, late là lỗi nặng. Dữ liệu này đã dùng phát triển nhiều lần.

### UORED budget 1 svm1



Nguồn: [results/u/retrospective.json](results/u/retrospective.json). Cấu hình: budget=1; bộ phân loại: svm1.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 65.00 | 51.32 |
| Sao chép | 65.00 | 51.32 |
| Surrogate cũ | 59.56 | 47.63 |
| Surrogate giữ đường bao | 66.05 | 53.25 |
| Trộn nền cùng ổ | 56.93 | 49.21 |
| Chuyển nền phổ | 64.30 | 47.46 |
| Chuyển nền và trộn | 57.63 | 43.42 |

### UORED budget 1 svm10



Nguồn: [results/u/retrospective.json](results/u/retrospective.json). Cấu hình: budget=1; bộ phân loại: svm10.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 65.18 | 51.58 |
| Sao chép | 65.18 | 51.58 |
| Surrogate cũ | 60.88 | 50.79 |
| Surrogate giữ đường bao | 64.21 | 52.72 |
| Trộn nền cùng ổ | 53.07 | 39.39 |
| Chuyển nền phổ | 67.11 | 48.51 |
| Chuyển nền và trộn | 59.82 | 42.37 |

### UORED budget 1 rf



Nguồn: [results/u/retrospective.json](results/u/retrospective.json). Cấu hình: budget=1; bộ phân loại: rf.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 51.49 | 52.46 |
| Sao chép | 51.49 | 52.46 |
| Surrogate cũ | 47.54 | 45.00 |
| Surrogate giữ đường bao | 50.61 | 47.81 |
| Trộn nền cùng ổ | 48.95 | 43.07 |
| Chuyển nền phổ | 55.35 | 45.00 |
| Chuyển nền và trộn | 53.86 | 47.02 |

### UORED budget 2 svm1



Nguồn: [results/u/retrospective.json](results/u/retrospective.json). Cấu hình: budget=2; bộ phân loại: svm1.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 63.77 | 48.95 |
| Sao chép | 63.77 | 48.95 |
| Surrogate cũ | 64.47 | 51.75 |
| Surrogate giữ đường bao | 63.77 | 48.33 |
| Trộn nền cùng ổ | 65.09 | 51.67 |
| Chuyển nền phổ | 66.49 | 54.65 |
| Chuyển nền và trộn | 65.61 | 49.04 |

### UORED budget 2 svm10



Nguồn: [results/u/retrospective.json](results/u/retrospective.json). Cấu hình: budget=2; bộ phân loại: svm10.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 63.77 | 50.35 |
| Sao chép | 63.77 | 50.35 |
| Surrogate cũ | 66.05 | 54.04 |
| Surrogate giữ đường bao | 65.88 | 54.04 |
| Trộn nền cùng ổ | 67.54 | 53.95 |
| Chuyển nền phổ | 68.60 | 53.60 |
| Chuyển nền và trộn | 65.88 | 50.70 |

### UORED budget 2 rf



Nguồn: [results/u/retrospective.json](results/u/retrospective.json). Cấu hình: budget=2; bộ phân loại: rf.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 61.23 | 60.00 |
| Sao chép | 61.23 | 60.00 |
| Surrogate cũ | 60.09 | 57.46 |
| Surrogate giữ đường bao | 58.16 | 57.46 |
| Trộn nền cùng ổ | 64.30 | 57.46 |
| Chuyển nền phổ | 55.70 | 50.44 |
| Chuyển nền và trộn | 63.16 | 51.23 |

### UORED budget 4 svm1



Nguồn: [results/u/retrospective.json](results/u/retrospective.json). Cấu hình: budget=4; bộ phân loại: svm1.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 68.68 | 59.65 |
| Sao chép | 68.68 | 59.65 |
| Surrogate cũ | 69.21 | 57.46 |
| Surrogate giữ đường bao | 68.68 | 64.04 |
| Trộn nền cùng ổ | 70.18 | 58.07 |
| Chuyển nền phổ | 69.47 | 58.68 |
| Chuyển nền và trộn | 72.54 | 57.54 |

### UORED budget 4 svm10



Nguồn: [results/u/retrospective.json](results/u/retrospective.json). Cấu hình: budget=4; bộ phân loại: svm10.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 68.42 | 57.89 |
| Sao chép | 68.42 | 57.89 |
| Surrogate cũ | 68.07 | 55.61 |
| Surrogate giữ đường bao | 65.26 | 60.88 |
| Trộn nền cùng ổ | 70.26 | 57.89 |
| Chuyển nền phổ | 71.14 | 58.68 |
| Chuyển nền và trộn | 72.98 | 54.21 |

### UORED budget 4 rf



Nguồn: [results/u/retrospective.json](results/u/retrospective.json). Cấu hình: budget=4; bộ phân loại: rf.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 64.82 | 63.77 |
| Sao chép | 64.82 | 63.77 |
| Surrogate cũ | 67.28 | 67.72 |
| Surrogate giữ đường bao | 69.47 | 69.74 |
| Trộn nền cùng ổ | 62.46 | 66.75 |
| Chuyển nền phổ | 65.09 | 59.12 |
| Chuyển nền và trộn | 71.05 | 63.07 |

## 6. U: surrogate hai trục và dải đo

Cùng96features trong mỗi phép so; không so trực tiếp với45features một trục để quy gain cho generator.8g,16g,64g là giả định, chưa chọn phần cứng thực.

### Hai trục 8g rf



Nguồn: [results/u/joint.json](results/u/joint.json). Cấu hình: range=8g; bộ phân loại: rf.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 65.51 | 62.22 |
| Sao chép | 65.51 | 62.22 |
| Surrogate cũ | 61.20 | 63.33 |
| Quay pha riêng hai trục | 64.91 | 63.70 |
| Quay pha chung hai trục | 63.24 | 63.33 |

### Hai trục 8g svm1



Nguồn: [results/u/joint.json](results/u/joint.json). Cấu hình: range=8g; bộ phân loại: svm1.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 36.67 | 51.11 |
| Sao chép | 36.67 | 51.11 |
| Surrogate cũ | 36.67 | 49.26 |
| Quay pha riêng hai trục | 35.56 | 51.11 |
| Quay pha chung hai trục | 35.93 | 49.63 |

### Hai trục 8g svm10



Nguồn: [results/u/joint.json](results/u/joint.json). Cấu hình: range=8g; bộ phân loại: svm10.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 36.67 | 51.11 |
| Sao chép | 36.67 | 51.11 |
| Surrogate cũ | 37.59 | 53.33 |
| Quay pha riêng hai trục | 35.56 | 50.74 |
| Quay pha chung hai trục | 35.93 | 49.63 |

### Hai trục 16g rf



Nguồn: [results/u/joint.json](results/u/joint.json). Cấu hình: range=16g; bộ phân loại: rf.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 60.00 | 59.44 |
| Sao chép | 60.00 | 59.44 |
| Surrogate cũ | 64.91 | 61.11 |
| Quay pha riêng hai trục | 62.31 | 64.44 |
| Quay pha chung hai trục | 65.97 | 63.52 |

### Hai trục 16g svm1



Nguồn: [results/u/joint.json](results/u/joint.json). Cấu hình: range=16g; bộ phân loại: svm1.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 45.14 | 45.56 |
| Sao chép | 45.14 | 45.56 |
| Surrogate cũ | 45.14 | 45.19 |
| Quay pha riêng hai trục | 45.88 | 45.56 |
| Quay pha chung hai trục | 46.25 | 45.56 |

### Hai trục 16g svm10



Nguồn: [results/u/joint.json](results/u/joint.json). Cấu hình: range=16g; bộ phân loại: svm10.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 45.14 | 45.56 |
| Sao chép | 45.14 | 45.56 |
| Surrogate cũ | 48.38 | 45.56 |
| Quay pha riêng hai trục | 46.25 | 45.56 |
| Quay pha chung hai trục | 47.13 | 45.56 |

### Hai trục 64g rf



Nguồn: [results/u/joint.json](results/u/joint.json). Cấu hình: range=64g; bộ phân loại: rf.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 68.98 | 58.15 |
| Sao chép | 68.98 | 58.15 |
| Surrogate cũ | 66.81 | 53.52 |
| Quay pha riêng hai trục | 69.07 | 56.30 |
| Quay pha chung hai trục | 69.44 | 55.93 |

### Hai trục 64g svm1



Nguồn: [results/u/joint.json](results/u/joint.json). Cấu hình: range=64g; bộ phân loại: svm1.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 46.67 | 43.33 |
| Sao chép | 46.67 | 43.33 |
| Surrogate cũ | 48.61 | 44.07 |
| Quay pha riêng hai trục | 46.67 | 44.44 |
| Quay pha chung hai trục | 46.67 | 44.44 |

### Hai trục 64g svm10



Nguồn: [results/u/joint.json](results/u/joint.json). Cấu hình: range=64g; bộ phân loại: svm10.

| Phương pháp | early | late |
|---|---:|---:|
| Mẫu thật | 46.67 | 43.33 |
| Sao chép | 46.67 | 43.33 |
| Surrogate cũ | 50.23 | 44.44 |
| Quay pha riêng hai trục | 47.41 | 44.81 |
| Quay pha chung hai trục | 46.67 | 44.44 |

## 7. T: cảnh báo giả, từ chối và lỗi chưa học

Healthy1–5 dùng train,6–10 chỉ test. Cảnh báo upstream được ép true để stress module. Healthy chỉ là giả định, nên healthy_fault_claim không phải FPR của hệ thống nhà máy. Hai stage lỗi giữ nguyên U, nhưng ngân sách healthy và chính sách quyết định thay đổi.

### Thư viện closed

| Classifier | Phương pháp | Chính sách | Trước cuối | Cuối | Vòng cách cuối | Gán lỗi trên healthy | Gán lỗi đã biết cho cage chưa học |
|---|---|---|---:|---:|---:|---:|---:|
| rf | Mẫu thật | conditional | 69.58 | 76.11 | 35.00 | 100.00 | Không áp dụng |
| rf | Mẫu thật | selective_0 | 58.75 | 68.33 | 11.67 | 0.00 | Không áp dụng |
| rf | Mẫu thật | selective_0.5 | 43.29 | 58.84 | 0.00 | 0.00 | Không áp dụng |
| rf | Mẫu thật | selective_0.7 | 26.53 | 32.04 | 0.00 | 0.00 | Không áp dụng |
| rf | Mẫu thật | selective_0.9 | 6.53 | 9.58 | 0.00 | 0.00 | Không áp dụng |
| rf | Sao chép | conditional | 69.58 | 76.11 | 35.00 | 100.00 | Không áp dụng |
| rf | Sao chép | selective_0 | 58.75 | 68.33 | 11.67 | 0.00 | Không áp dụng |
| rf | Sao chép | selective_0.5 | 43.29 | 58.84 | 0.00 | 0.00 | Không áp dụng |
| rf | Sao chép | selective_0.7 | 26.53 | 32.04 | 0.00 | 0.00 | Không áp dụng |
| rf | Sao chép | selective_0.9 | 6.53 | 9.58 | 0.00 | 0.00 | Không áp dụng |
| rf | Surrogate cũ | conditional | 74.63 | 74.44 | 33.33 | 99.49 | Không áp dụng |
| rf | Surrogate cũ | selective_0 | 56.71 | 63.33 | 0.00 | 0.00 | Không áp dụng |
| rf | Surrogate cũ | selective_0.5 | 47.69 | 59.58 | 0.00 | 0.00 | Không áp dụng |
| rf | Surrogate cũ | selective_0.7 | 28.19 | 34.21 | 0.00 | 0.00 | Không áp dụng |
| rf | Surrogate cũ | selective_0.9 | 6.94 | 9.03 | 0.00 | 0.00 | Không áp dụng |
| rf | Trộn nền cùng ổ | conditional | 73.06 | 77.96 | 41.67 | 100.00 | Không áp dụng |
| rf | Trộn nền cùng ổ | selective_0 | 60.56 | 66.30 | 6.67 | 1.03 | Không áp dụng |
| rf | Trộn nền cùng ổ | selective_0.5 | 50.00 | 55.14 | 0.00 | 0.00 | Không áp dụng |
| rf | Trộn nền cùng ổ | selective_0.7 | 26.85 | 33.15 | 0.00 | 0.00 | Không áp dụng |
| rf | Trộn nền cùng ổ | selective_0.9 | 7.50 | 10.97 | 0.00 | 0.00 | Không áp dụng |
| rf | Chuyển nền phổ | conditional | 75.56 | 78.89 | 43.33 | 100.00 | Không áp dụng |
| rf | Chuyển nền phổ | selective_0 | 71.94 | 77.78 | 40.00 | 0.00 | Không áp dụng |
| rf | Chuyển nền phổ | selective_0.5 | 54.35 | 58.89 | 0.00 | 0.00 | Không áp dụng |
| rf | Chuyển nền phổ | selective_0.7 | 29.44 | 32.82 | 0.00 | 0.00 | Không áp dụng |
| rf | Chuyển nền phổ | selective_0.9 | 7.08 | 9.68 | 0.00 | 0.00 | Không áp dụng |
| svm1 | Mẫu thật | conditional | 47.64 | 57.64 | 0.00 | 100.00 | Không áp dụng |
| svm1 | Mẫu thật | selective_0 | 44.72 | 57.64 | 0.00 | 3.08 | Không áp dụng |
| svm1 | Mẫu thật | selective_0.5 | 41.39 | 50.97 | 0.00 | 0.00 | Không áp dụng |
| svm1 | Mẫu thật | selective_0.7 | 11.25 | 12.08 | 0.00 | 0.00 | Không áp dụng |
| svm1 | Mẫu thật | selective_0.9 | 0.00 | 0.00 | 0.00 | 0.00 | Không áp dụng |
| svm1 | Sao chép | conditional | 47.64 | 57.64 | 0.00 | 100.00 | Không áp dụng |
| svm1 | Sao chép | selective_0 | 44.72 | 57.64 | 0.00 | 3.08 | Không áp dụng |
| svm1 | Sao chép | selective_0.5 | 41.39 | 50.97 | 0.00 | 0.00 | Không áp dụng |
| svm1 | Sao chép | selective_0.7 | 11.25 | 12.08 | 0.00 | 0.00 | Không áp dụng |
| svm1 | Sao chép | selective_0.9 | 0.00 | 0.00 | 0.00 | 0.00 | Không áp dụng |
| svm1 | Surrogate cũ | conditional | 49.12 | 57.64 | 0.00 | 100.00 | Không áp dụng |
| svm1 | Surrogate cũ | selective_0 | 46.20 | 57.64 | 0.00 | 3.08 | Không áp dụng |
| svm1 | Surrogate cũ | selective_0.5 | 43.24 | 50.97 | 0.00 | 0.00 | Không áp dụng |
| svm1 | Surrogate cũ | selective_0.7 | 11.25 | 12.36 | 0.00 | 0.00 | Không áp dụng |
| svm1 | Surrogate cũ | selective_0.9 | 0.00 | 0.00 | 0.00 | 0.00 | Không áp dụng |
| svm1 | Trộn nền cùng ổ | conditional | 49.07 | 57.73 | 0.00 | 100.00 | Không áp dụng |
| svm1 | Trộn nền cùng ổ | selective_0 | 47.69 | 57.73 | 0.00 | 3.08 | Không áp dụng |
| svm1 | Trộn nền cùng ổ | selective_0.5 | 43.24 | 54.86 | 0.00 | 0.00 | Không áp dụng |
| svm1 | Trộn nền cùng ổ | selective_0.7 | 11.39 | 12.92 | 0.00 | 0.00 | Không áp dụng |
| svm1 | Trộn nền cùng ổ | selective_0.9 | 0.00 | 0.00 | 0.00 | 0.00 | Không áp dụng |
| svm1 | Chuyển nền phổ | conditional | 52.45 | 62.96 | 0.00 | 100.00 | Không áp dụng |
| svm1 | Chuyển nền phổ | selective_0 | 50.65 | 62.96 | 0.00 | 1.54 | Không áp dụng |
| svm1 | Chuyển nền phổ | selective_0.5 | 43.98 | 60.00 | 0.00 | 0.00 | Không áp dụng |
| svm1 | Chuyển nền phổ | selective_0.7 | 9.44 | 6.67 | 0.00 | 0.00 | Không áp dụng |
| svm1 | Chuyển nền phổ | selective_0.9 | 0.00 | 0.00 | 0.00 | 0.00 | Không áp dụng |

### Thư viện missing_cage

| Classifier | Phương pháp | Chính sách | Trước cuối | Cuối | Vòng cách cuối | Gán lỗi trên healthy | Gán lỗi đã biết cho cage chưa học |
|---|---|---|---:|---:|---:|---:|---:|
| rf | Mẫu thật | conditional | 62.59 | 64.44 | 0.00 | 99.49 | 100.00 |
| rf | Mẫu thật | selective_0 | 58.70 | 64.44 | 0.00 | 0.51 | 100.00 |
| rf | Mẫu thật | selective_0.5 | 58.06 | 64.44 | 0.00 | 0.00 | 75.00 |
| rf | Mẫu thật | selective_0.7 | 42.73 | 41.76 | 0.00 | 0.00 | 48.33 |
| rf | Mẫu thật | selective_0.9 | 16.39 | 18.43 | 0.00 | 0.00 | 31.67 |
| rf | Sao chép | conditional | 62.59 | 64.44 | 0.00 | 99.49 | 100.00 |
| rf | Sao chép | selective_0 | 58.70 | 64.44 | 0.00 | 0.51 | 100.00 |
| rf | Sao chép | selective_0.5 | 58.06 | 64.44 | 0.00 | 0.00 | 75.00 |
| rf | Sao chép | selective_0.7 | 42.73 | 41.76 | 0.00 | 0.00 | 48.33 |
| rf | Sao chép | selective_0.9 | 16.39 | 18.43 | 0.00 | 0.00 | 31.67 |
| rf | Surrogate cũ | conditional | 60.74 | 62.59 | 0.00 | 99.49 | 100.00 |
| rf | Surrogate cũ | selective_0 | 56.71 | 62.59 | 0.00 | 2.05 | 75.00 |
| rf | Surrogate cũ | selective_0.5 | 56.57 | 62.59 | 0.00 | 1.54 | 50.00 |
| rf | Surrogate cũ | selective_0.7 | 41.34 | 39.81 | 0.00 | 0.00 | 50.00 |
| rf | Surrogate cũ | selective_0.9 | 17.73 | 20.93 | 0.00 | 0.00 | 18.33 |
| rf | Trộn nền cùng ổ | conditional | 61.44 | 61.85 | 0.00 | 99.49 | 100.00 |
| rf | Trộn nền cùng ổ | selective_0 | 57.96 | 61.85 | 0.00 | 2.56 | 76.67 |
| rf | Trộn nền cùng ổ | selective_0.5 | 56.94 | 61.85 | 0.00 | 2.56 | 51.67 |
| rf | Trộn nền cùng ổ | selective_0.7 | 39.54 | 42.59 | 0.00 | 0.00 | 48.33 |
| rf | Trộn nền cùng ổ | selective_0.9 | 15.56 | 18.29 | 0.00 | 0.00 | 31.67 |
| rf | Chuyển nền phổ | conditional | 61.85 | 64.07 | 0.00 | 99.49 | 100.00 |
| rf | Chuyển nền phổ | selective_0 | 58.10 | 64.07 | 0.00 | 2.56 | 85.00 |
| rf | Chuyển nền phổ | selective_0.5 | 57.31 | 64.07 | 0.00 | 2.05 | 56.67 |
| rf | Chuyển nền phổ | selective_0.7 | 39.49 | 45.00 | 0.00 | 0.00 | 50.00 |
| rf | Chuyển nền phổ | selective_0.9 | 17.73 | 22.59 | 0.00 | 0.00 | 36.67 |
| svm1 | Mẫu thật | conditional | 55.56 | 60.00 | 0.00 | 100.00 | 100.00 |
| svm1 | Mẫu thật | selective_0 | 52.64 | 60.00 | 0.00 | 7.69 | 100.00 |
| svm1 | Mẫu thật | selective_0.5 | 51.81 | 58.89 | 0.00 | 7.69 | 100.00 |
| svm1 | Mẫu thật | selective_0.7 | 28.75 | 35.69 | 0.00 | 6.15 | 80.00 |
| svm1 | Mẫu thật | selective_0.9 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| svm1 | Sao chép | conditional | 55.56 | 60.00 | 0.00 | 100.00 | 100.00 |
| svm1 | Sao chép | selective_0 | 52.64 | 60.00 | 0.00 | 7.69 | 100.00 |
| svm1 | Sao chép | selective_0.5 | 51.81 | 58.89 | 0.00 | 7.69 | 100.00 |
| svm1 | Sao chép | selective_0.7 | 28.75 | 35.69 | 0.00 | 6.15 | 80.00 |
| svm1 | Sao chép | selective_0.9 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| svm1 | Surrogate cũ | conditional | 54.07 | 60.00 | 0.00 | 100.00 | 100.00 |
| svm1 | Surrogate cũ | selective_0 | 51.16 | 60.00 | 0.00 | 7.69 | 100.00 |
| svm1 | Surrogate cũ | selective_0.5 | 50.32 | 58.89 | 0.00 | 7.69 | 100.00 |
| svm1 | Surrogate cũ | selective_0.7 | 28.75 | 36.81 | 0.00 | 6.15 | 80.00 |
| svm1 | Surrogate cũ | selective_0.9 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| svm1 | Trộn nền cùng ổ | conditional | 54.81 | 60.00 | 0.00 | 100.00 | 100.00 |
| svm1 | Trộn nền cùng ổ | selective_0 | 51.90 | 60.00 | 0.00 | 7.69 | 100.00 |
| svm1 | Trộn nền cùng ổ | selective_0.5 | 51.06 | 59.63 | 0.00 | 7.69 | 96.67 |
| svm1 | Trộn nền cùng ổ | selective_0.7 | 39.03 | 36.44 | 0.00 | 6.15 | 70.00 |
| svm1 | Trộn nền cùng ổ | selective_0.9 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| svm1 | Chuyển nền phổ | conditional | 52.96 | 60.00 | 0.00 | 100.00 | 100.00 |
| svm1 | Chuyển nền phổ | selective_0 | 50.05 | 60.00 | 0.00 | 7.69 | 100.00 |
| svm1 | Chuyển nền phổ | selective_0.5 | 49.21 | 59.63 | 0.00 | 7.69 | 95.00 |
| svm1 | Chuyển nền phổ | selective_0.7 | 24.44 | 33.66 | 0.00 | 6.15 | 68.33 |
| svm1 | Chuyển nền phổ | selective_0.9 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

### Chọn phương pháp bằng inner folds

Healthy recall chỉ tính lựa chọn healthy là đúng; từ chối không tính đúng. 13 ổ và ba seed, không phải39ổ.

Nguồn: [results/t/nested.json](results/t/nested.json). Cấu hình: nested, selective_0; bộ phân loại: RF.

| Phương pháp | healthy | preterminal | terminal |
|---|---:|---:|---:|
| Mẫu thật | 100.00 | 58.75 | 68.33 |
| Surrogate cũ | 100.00 | 56.71 | 63.33 |
| Trộn nền cùng ổ | 98.97 | 60.56 | 66.30 |
| Chuyển nền phổ | 100.00 | 71.94 | 77.78 |
| Chọn bằng ổ nguồn | 100.00 | 61.76 | 67.96 |

### Thư viện và căn chỉnh xjtu:raw



Nguồn: [results/t/external.json](results/t/external.json). Cấu hình: xjtu:raw; bộ phân loại: RF.

| Phương pháp | healthy | preterminal | terminal |
|---|---:|---:|---:|
| Mẫu thật | 100.00 | 58.75 | 68.33 |
| Sao chép | 100.00 | 58.75 | 68.33 |
| Surrogate cũ | 100.00 | 56.71 | 63.33 |
| Trộn nền cùng ổ | 98.97 | 60.56 | 66.30 |

### Thư viện và căn chỉnh combined:raw



Nguồn: [results/t/external.json](results/t/external.json). Cấu hình: combined:raw; bộ phân loại: RF.

| Phương pháp | healthy | preterminal | terminal |
|---|---:|---:|---:|
| Mẫu thật | 100.00 | 65.65 | 54.81 |
| Sao chép | 100.00 | 65.65 | 54.81 |
| Surrogate cũ | 99.49 | 67.22 | 53.70 |
| Trộn nền cùng ổ | 100.00 | 65.93 | 51.85 |

### Thư viện và căn chỉnh xjtu:delta



Nguồn: [results/t/external.json](results/t/external.json). Cấu hình: xjtu:delta; bộ phân loại: RF.

| Phương pháp | healthy | preterminal | terminal |
|---|---:|---:|---:|
| Mẫu thật | 96.92 | 70.83 | 77.73 |
| Sao chép | 96.92 | 70.83 | 77.73 |
| Surrogate cũ | 96.92 | 66.67 | 74.03 |
| Trộn nền cùng ổ | 96.92 | 65.42 | 73.66 |

### Thư viện và căn chỉnh combined:delta



Nguồn: [results/t/external.json](results/t/external.json). Cấu hình: combined:delta; bộ phân loại: RF.

| Phương pháp | healthy | preterminal | terminal |
|---|---:|---:|---:|
| Mẫu thật | 87.18 | 49.77 | 47.36 |
| Sao chép | 87.18 | 49.77 | 47.36 |
| Surrogate cũ | 85.13 | 47.22 | 41.67 |
| Trộn nền cùng ổ | 82.05 | 49.21 | 48.56 |

## 8. Các phép thử nền tảng, nguồn bôi trơn và toàn bộ hồ sơ lưu

TN1–TN7, E1–E8 và X1–X9 gồm mô phỏng cảm biến, anomaly detection, thời gian chạy, thay đổi chế độ, baseline và các kiểm tra chẩn đoán. Không gộp AUC, FPR, accuracy, recall có điều kiện hoặc thời gian phát hiện thành một cột điểm chung.

Z và T kiểm tra nguồn bôi trơn: bảng grease có confounding tình trạng phớt, DLR thiếu nhiều lần chạy có dầu và không dầu cùng chế độ. Không coi các pilot này là benchmark chẩn đoán thiếu bôi trơn đã được xác nhận.

Danh mục dưới đây bao gồm mọi JSON cấp đầu trong từng thư mục kết quả AnchorSpec và toàn bộ JSON trong release CWRU cùng handoff validation. Checkpoint trong thư mục tasks không lặp lại ở danh mục; prediction theo mẫu vẫn ở file kết quả gốc. Các CSV giữ tên trường gốc, không tự quy mọi giá trị thành phần trăm.

[CSV so sánh các bảng trên](results/overview/benchmark_comparisons.csv). [CSV chỉ số gốc của toàn bộ hồ sơ](results/overview/archive_metrics.csv).

| Nhóm | File kết quả gốc | Số giá trị được trích |
|---|---|---:|
| e1 | [e1.json](results/e1/e1.json) | 234 |
| e2 | [e2.json](results/e2/e2.json) | 464 |
| e3 | [e3.json](results/e3/e3.json) | 75 |
| e4 | [e4.json](results/e4/e4.json) | 1443 |
| e5 | [e5.json](results/e5/e5.json) | 85 |
| e6 | [e6.json](results/e6/e6.json) | 36 |
| e7 | [e7.json](results/e7/e7.json) | 66 |
| e8 | [FROZEN.json](results/e8/FROZEN.json) | 0 |
| e8 | [summary.json](results/e8/summary.json) | 128 |
| e8 | [test.json](results/e8/test.json) | 7098 |
| t | [external.json](results/t/external.json) | 1394 |
| t | [external_prerun.json](results/t/external_prerun.json) | 0 |
| t | [lubrication_design.json](results/t/lubrication_design.json) | 61 |
| t | [manifest.json](results/t/manifest.json) | 0 |
| t | [nested.json](results/t/nested.json) | 304 |
| t | [nested_prerun.json](results/t/nested_prerun.json) | 0 |
| t | [nested_selection.json](results/t/nested_selection.json) | 19266 |
| t | [prerun.json](results/t/prerun.json) | 1 |
| t | [readiness.json](results/t/readiness.json) | 3993 |
| t | [representation_gain.json](results/t/representation_gain.json) | 10 |
| t | [validation.json](results/t/validation.json) | 19 |
| tn1 | [metrics.json](results/tn1/metrics.json) | 3060 |
| tn1 | [multiload.json](results/tn1/multiload.json) | 60 |
| tn1 | [summary.json](results/tn1/summary.json) | 182 |
| tn2 | [calibration.json](results/tn2/calibration.json) | 54 |
| tn2 | [calibration_unit_g.json](results/tn2/calibration_unit_g.json) | 54 |
| tn2 | [dev.json](results/tn2/dev.json) | 98 |
| tn2 | [dev_unit_g.json](results/tn2/dev_unit_g.json) | 98 |
| tn2 | [FROZEN.json](results/tn2/FROZEN.json) | 0 |
| tn2 | [test.json](results/tn2/test.json) | 135 |
| tn2b | [FROZEN.json](results/tn2b/FROZEN.json) | 0 |
| tn2b | [test.json](results/tn2b/test.json) | 670 |
| tn2c | [test.json](results/tn2c/test.json) | 51 |
| tn3 | [summary.json](results/tn3/summary.json) | 1578 |
| tn3b | [pipeline_cusum.json](results/tn3b/pipeline_cusum.json) | 283 |
| tn3b | [pipeline_nguong.json](results/tn3b/pipeline_nguong.json) | 265 |
| tn3b | [trend.json](results/tn3b/trend.json) | 2536 |
| tn5 | [stage_unknown_init.json](results/tn5/stage_unknown_init.json) | 874 |
| tn6 | [retrain_cage_gate.json](results/tn6/retrain_cage_gate.json) | 1069 |
| tn7 | [minirocket.json](results/tn7/minirocket.json) | 217 |
| u | [joint.json](results/u/joint.json) | 2798 |
| u | [manifest.json](results/u/manifest.json) | 0 |
| u | [natural.json](results/u/natural.json) | 933 |
| u | [retrospective.json](results/u/retrospective.json) | 1893 |
| u | [retrospective_frozen.json](results/u/retrospective_frozen.json) | 0 |
| u | [validation.json](results/u/validation.json) | 124 |
| v | [champion_augmentation.json](results/v/champion_augmentation.json) | 1756 |
| v | [holdout6204.json](results/v/holdout6204.json) | 113 |
| v | [hust_transport.json](results/v/hust_transport.json) | 626 |
| v | [kaist_transport.json](results/v/kaist_transport.json) | 56 |
| v | [manifest.json](results/v/manifest.json) | 0 |
| v | [transport.json](results/v/transport.json) | 6120 |
| v | [transport_summary.json](results/v/transport_summary.json) | 872 |
| v | [validation.json](results/v/validation.json) | 29 |
| w | [amplitude.json](results/w/amplitude.json) | 1322 |
| w | [comparison.json](results/w/comparison.json) | 6960 |
| w | [delivery_manifest.json](results/w/delivery_manifest.json) | 21 |
| w | [delivery_summary.json](results/w/delivery_summary.json) | 349 |
| w | [hierarchy.json](results/w/hierarchy.json) | 541 |
| w | [kaist.json](results/w/kaist.json) | 57 |
| w | [runtime_replay.json](results/w/runtime_replay.json) | 2621 |
| w | [spectral.json](results/w/spectral.json) | 3901 |
| w | [summary.json](results/w/summary.json) | 489 |
| w | [validation.json](results/w/validation.json) | 8 |
| x | [x1.json](results/x/x1.json) | 3951 |
| x | [x2.json](results/x/x2.json) | 40 |
| x | [x3.json](results/x/x3.json) | 504 |
| x | [x4.json](results/x/x4.json) | 40 |
| x | [x5.json](results/x/x5.json) | 366 |
| x | [x6.json](results/x/x6.json) | 231 |
| x | [x7.json](results/x/x7.json) | 2808 |
| x | [x8.json](results/x/x8.json) | 5508 |
| x | [x9.json](results/x/x9.json) | 2142 |
| y | [adaptive_balanced.json](results/y/adaptive_balanced.json) | 9840 |
| y | [adaptive_stream.json](results/y/adaptive_stream.json) | 10740 |
| y | [balanced.json](results/y/balanced.json) | 5523 |
| y | [balanced_both.json](results/y/balanced_both.json) | 5523 |
| y | [balanced_both_summary.json](results/y/balanced_both_summary.json) | 431 |
| y | [balanced_delta.json](results/y/balanced_delta.json) | 5523 |
| y | [balanced_delta_summary.json](results/y/balanced_delta_summary.json) | 431 |
| y | [balanced_raw.json](results/y/balanced_raw.json) | 5523 |
| y | [balanced_raw_summary.json](results/y/balanced_raw_summary.json) | 431 |
| y | [balanced_summary.json](results/y/balanced_summary.json) | 431 |
| y | [comparison.json](results/y/comparison.json) | 410 |
| y | [conditional_diagnosis.json](results/y/conditional_diagnosis.json) | 146 |
| y | [diagnostic_balanced.json](results/y/diagnostic_balanced.json) | 21841 |
| y | [diagnostic_comparison.json](results/y/diagnostic_comparison.json) | 306 |
| y | [diagnostic_stream.json](results/y/diagnostic_stream.json) | 24181 |
| y | [kernel_balanced.json](results/y/kernel_balanced.json) | 21840 |
| y | [kernel_stream.json](results/y/kernel_stream.json) | 25020 |
| y | [stream.json](results/y/stream.json) | 6063 |
| y | [stream_summary.json](results/y/stream_summary.json) | 691 |
| z | [dlr_monitoring_pilot.json](results/z/dlr_monitoring_pilot.json) | 8001 |
| z | [grease_states_pilot.json](results/z/grease_states_pilot.json) | 8639 |
| z | [public_sources.json](results/z/public_sources.json) | 7 |
| acceptance | [results.json](../generator_benchmark/mvp_release_20261007/acceptance/results.json) | 24 |
| development | [costs.json](../generator_benchmark/mvp_release_20261007/development/costs.json) | 72 |
| development | [metrics.json](../generator_benchmark/mvp_release_20261007/development/metrics.json) | 3114 |
| development | [selection.json](../generator_benchmark/mvp_release_20261007/development/selection.json) | 60 |
| mvp_release_20261007 | [environment.json](../generator_benchmark/mvp_release_20261007/environment.json) | 0 |
| final | [metrics.json](../generator_benchmark/mvp_release_20261007/final/metrics.json) | 1224 |
| final | [prediction_indices.json](../generator_benchmark/mvp_release_20261007/final/prediction_indices.json) | 474 |
| final | [summary.json](../generator_benchmark/mvp_release_20261007/final/summary.json) | 69 |
| final | [thresholds.json](../generator_benchmark/mvp_release_20261007/final/thresholds.json) | 120 |
| mvp_release_20261007 | [FROZEN.json](../generator_benchmark/mvp_release_20261007/FROZEN.json) | 2 |
| mvp_release_20261007 | [integrity.json](../generator_benchmark/mvp_release_20261007/integrity.json) | 1 |
| mvp_release_20261007 | [library_audit.json](../generator_benchmark/mvp_release_20261007/library_audit.json) | 18 |
| mvp_release_20261007 | [protocol.json](../generator_benchmark/mvp_release_20261007/protocol.json) | 23 |
| mvp_release_20261007 | [records.json](../generator_benchmark/mvp_release_20261007/records.json) | 69 |
| mvp_release_20261007 | [split_audit.json](../generator_benchmark/mvp_release_20261007/split_audit.json) | 4 |
| mvp_release_20261007 | [train_inventory.json](../generator_benchmark/mvp_release_20261007/train_inventory.json) | 35 |
| validation | [stress.json](../generator_benchmark/mvp_release_20261007/validation/stress.json) | 27 |
| validation | [tests.json](../generator_benchmark/mvp_release_20261007/validation/tests.json) | 26 |
| mvp_release_20261007 | [week_01.json](../generator_benchmark/mvp_release_20261007/week_01.json) | 1 |
| mvp_release_20261007 | [week_02.json](../generator_benchmark/mvp_release_20261007/week_02.json) | 1 |
| mvp_release_20261007 | [week_03.json](../generator_benchmark/mvp_release_20261007/week_03.json) | 1 |
| mvp_release_20261007 | [week_04.json](../generator_benchmark/mvp_release_20261007/week_04.json) | 1 |
| mvp_release_20261007 | [week_05.json](../generator_benchmark/mvp_release_20261007/week_05.json) | 1 |
| mvp_release_20261007 | [week_06.json](../generator_benchmark/mvp_release_20261007/week_06.json) | 1 |
| mvp_release_20261007 | [week_07.json](../generator_benchmark/mvp_release_20261007/week_07.json) | 1 |
| mvp_release_20261007 | [week_08.json](../generator_benchmark/mvp_release_20261007/week_08.json) | 1 |
| mvp_release_20261007 | [week_09.json](../generator_benchmark/mvp_release_20261007/week_09.json) | 1 |
| mvp_release_20261007 | [week_10.json](../generator_benchmark/mvp_release_20261007/week_10.json) | 1 |
| mvp_release_20261007 | [week_11.json](../generator_benchmark/mvp_release_20261007/week_11.json) | 1 |
| mvp_release_20261007 | [week_12.json](../generator_benchmark/mvp_release_20261007/week_12.json) | 1 |
| handoff_validation_20261007 | [layout_verified.json](../generator_benchmark/handoff_validation_20261007/layout_verified.json) | 0 |
| handoff_validation_20261007 | [results.json](../generator_benchmark/handoff_validation_20261007/results.json) | 69 |

## Kết luận có thể rút ra

Surrogate cũ là đối chứng đáng giữ: có phép thử tốt hơn mẫu thật, có phép thử kém hơn. Không có bằng chứng mọi biến thể mới đều tốt hơn surrogate.

Giữ đường bao có lợi trên một cấu hình UORED; trộn nền cùng ổ có điểm tốt ở RF XJTU conditional; chuyển nền có lợi trên một số HUST và SVM XJTU. Lợi ích đổi theo classifier, budget và dữ liệu. Các cổng xác nhận chính chưa chứng minh ưu thế toàn diện.

Trong phép thử T mới, căn chỉnh theo nền khỏe giúp mẫu thật tăng điểm. Đây là lợi ích feature; thêm UORED hoặc augmentation không tự động giúp thêm. Chưa xác nhận trên nhà máy, lỗi chưa học và hai loại thiếu bôi trơn, dị vật.

Tổng hợp 127 file JSON, 987 dòng so sánh và 260124 giá trị gốc. Mỗi file có SHA256 trong inventory.json. Không dùng số này làm số thí nghiệm độc lập.
