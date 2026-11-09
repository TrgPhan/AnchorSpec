# Kiểm chứng dữ liệu sinh AnchorSpec, 04/11/2026

Đợt V tách riêng lợi ích của bộ sinh khỏi lợi ích đổi bộ phân loại. Kết quả dưới đây là nghiên cứu trên dữ liệu công khai; chưa xác nhận tại DENSO.
**Chưa đủ bằng chứng để tuyên bố dữ liệu sinh vượt trội toàn diện.** Các bảng bên dưới giữ cả kết quả tốt và kết quả giảm chất lượng.


## Phương pháp được thử

Chuyển mẫu lỗi theo nền rung khỏe: lấy mẫu lỗi đã đo của máy nguồn, ước lượng tỷ lệ phổ từ dữ liệu khỏe của hai máy, hiệu chỉnh tốc độ, rồi tạo biến thể trên nền máy đích. Không dùng mẫu lỗi của máy đích để sinh dữ liệu. Đây là giả thuyết thích nghi tín hiệu, chưa phải mô hình cơ học đã kiểm chứng.

Sáu đối chứng gồm mẫu thật, sao chép mẫu, surrogate cũ, trộn nền cùng máy, chuyển nền phổ, và chuyển nền phổ kết hợp trộn. Bộ phân loại giữ nguyên giữa các cách sinh trong từng phép so sánh. Tổng trọng số huấn luyện không tăng theo số mẫu sinh.

## UORED: cả lỗi đang phát triển và lỗi nặng

20 ổ bi, bốn loại lỗi, ba seed, ba ngân sách mẫu. Mỗi con số là macro recall theo ổ và loại lỗi, tính bằng phần trăm. Lỗi đang phát triển là trạng thái đã có lỗi; không phải cảnh báo trước khi hỏng.

| Số ổ nguồn mỗi loại | Phương pháp | Đang phát triển | Lỗi nặng | Trung bình |
|---|---|---:|---:|---:|
| 1 | Chỉ mẫu thật | 65.44 | 52.11 | 58.77 |
| 1 | Sao chép mẫu thật | 66.05 | 52.63 | 59.34 |
| 1 | Surrogate cũ | 59.30 | 48.33 | 53.82 |
| 1 | Trộn nền cùng máy | 54.74 | 41.75 | 48.25 |
| 1 | Chuyển nền phổ | 64.04 | 47.28 | 55.66 |
| 1 | Chuyển nền phổ và trộn | 57.63 | 44.39 | 51.01 |
| 1 | Chọn nguồn bằng validation | 65.44 | 52.11 | 58.77 |
| 2 | Chỉ mẫu thật | 59.91 | 59.74 | 59.82 |
| 2 | Sao chép mẫu thật | 61.32 | 58.51 | 59.91 |
| 2 | Surrogate cũ | 63.07 | 61.93 | 62.50 |
| 2 | Trộn nền cùng máy | 64.74 | 58.42 | 61.58 |
| 2 | Chuyển nền phổ | 67.72 | 59.82 | 63.77 |
| 2 | Chuyển nền phổ và trộn | 68.60 | 57.98 | 63.29 |
| 2 | Chọn nguồn bằng validation | 61.93 | 58.68 | 60.31 |
| 4 | Chỉ mẫu thật | 60.53 | 58.77 | 59.65 |
| 4 | Sao chép mẫu thật | 63.07 | 58.25 | 60.66 |
| 4 | Surrogate cũ | 62.02 | 56.75 | 59.39 |
| 4 | Trộn nền cùng máy | 62.89 | 58.77 | 60.83 |
| 4 | Chuyển nền phổ | 66.40 | 59.30 | 62.85 |
| 4 | Chuyển nền phổ và trộn | 67.81 | 54.47 | 61.14 |
| 4 | Chọn nguồn bằng validation | 58.95 | 56.14 | 57.54 |

### Chênh lệch của phương pháp chính so với chỉ mẫu thật

| Ngân sách | Chênh lệch trung bình hai trạng thái | Khoảng bootstrap 95% | Qua tiêu chí V |
|---|---:|---|---|
| 1 | -7.76 điểm | -13.86 đến -2.11 điểm | Không |
| 2 | +3.46 điểm | -6.93 đến +15.48 điểm | Không |
| 4 | +1.49 điểm | -11.32 đến +14.52 điểm | Không |

Khoảng bootstrap chỉ có tính thăm dò: các tập huấn luyện chồng nhau, UORED đã được dùng để phát triển nhiều phương án. Không coi cửa sổ hoặc seed là các phép thử độc lập.

### Đối chiếu mô hình tốt của đợt Y

- Ngân sách 1: Y chỉ mẫu thật đạt 52.28% ở lỗi đang phát triển và 40.96% ở lỗi nặng. Chênh lệch giữa Y và V có cả thay đổi quy trình chọn bộ phân loại; không quy hết cho dữ liệu sinh.
- Ngân sách 2: Y chỉ mẫu thật đạt 63.77% ở lỗi đang phát triển và 63.60% ở lỗi nặng. Chênh lệch giữa Y và V có cả thay đổi quy trình chọn bộ phân loại; không quy hết cho dữ liệu sinh.
- Ngân sách 4: Y chỉ mẫu thật đạt 70.26% ở lỗi đang phát triển và 66.67% ở lỗi nặng. Chênh lệch giữa Y và V có cả thay đổi quy trình chọn bộ phân loại; không quy hết cho dữ liệu sinh.

## Kiểm tra trên chính cấu hình Y đã cho kết quả tốt

Đã tái hiện chính xác số dự đoán từng lớp của đối chứng Y ở cả 180 cấu hình. Sau đó mới thêm mẫu sinh, giữ nguyên bộ phân loại và đặc trưng. Tỷ trọng mẫu sinh 0,25 là cấu hình chính đã định trước; 0,5 là kiểm tra độ nhạy.

Surrogate giữ đường bao dùng cùng một góc quay pha cho toàn bộ phổ tần số dương. Trước giới hạn cảm biến, phép biến đổi giữ độ lớn phổ và đường bao giải tích, ngoại trừ thành phần DC và Nyquist. Đây là tính chất toán học; chưa chứng minh mọi dạng sóng tương ứng một trạng thái hỏng thực tế.

| Ngân sách | Phương pháp và tỷ trọng | Đang phát triển | Lỗi nặng | Trung bình |
|---|---|---:|---:|---:|
| 1 | real | 52.28% | 40.96% | 46.62% |
| 1 | duplicate_0.25 | 46.49% | 40.79% | 43.64% |
| 1 | surrogate_0.25 | 48.42% | 40.53% | 44.47% |
| 1 | severity_0.25 | 52.37% | 43.95% | 48.16% |
| 1 | transport_0.25 | 58.60% | 46.14% | 52.37% |
| 1 | transport_mix_0.25 | 58.16% | 44.56% | 51.36% |
| 1 | envelope_0.25 | 52.37% | 45.26% | 48.82% |
| 1 | duplicate_0.5 | 50.53% | 40.96% | 45.75% |
| 1 | surrogate_0.5 | 47.89% | 43.51% | 45.70% |
| 1 | severity_0.5 | 50.70% | 37.54% | 44.12% |
| 1 | transport_0.5 | 58.95% | 42.54% | 50.75% |
| 1 | transport_mix_0.5 | 54.82% | 45.44% | 50.13% |
| 1 | envelope_0.5 | 52.63% | 45.18% | 48.90% |
| 2 | real | 63.77% | 63.60% | 63.68% |
| 2 | duplicate_0.25 | 64.56% | 61.49% | 63.03% |
| 2 | surrogate_0.25 | 60.61% | 55.26% | 57.94% |
| 2 | severity_0.25 | 62.72% | 55.61% | 59.17% |
| 2 | transport_0.25 | 61.23% | 56.67% | 58.95% |
| 2 | transport_mix_0.25 | 66.40% | 56.23% | 61.32% |
| 2 | envelope_0.25 | 61.93% | 59.12% | 60.53% |
| 2 | duplicate_0.5 | 62.63% | 58.42% | 60.53% |
| 2 | surrogate_0.5 | 62.28% | 57.63% | 59.96% |
| 2 | severity_0.5 | 63.42% | 55.44% | 59.43% |
| 2 | transport_0.5 | 63.86% | 54.21% | 59.04% |
| 2 | transport_mix_0.5 | 61.84% | 53.60% | 57.72% |
| 2 | envelope_0.5 | 60.96% | 57.28% | 59.12% |
| 4 | real | 70.26% | 66.67% | 68.46% |
| 4 | duplicate_0.25 | 68.95% | 66.49% | 67.72% |
| 4 | surrogate_0.25 | 69.65% | 68.60% | 69.12% |
| 4 | severity_0.25 | 68.33% | 66.32% | 67.32% |
| 4 | transport_0.25 | 70.53% | 68.68% | 69.61% |
| 4 | transport_mix_0.25 | 69.30% | 64.47% | 66.89% |
| 4 | envelope_0.25 | 71.23% | 67.46% | 69.34% |
| 4 | duplicate_0.5 | 66.14% | 67.19% | 66.67% |
| 4 | surrogate_0.5 | 72.63% | 68.60% | 70.61% |
| 4 | severity_0.5 | 66.40% | 65.88% | 66.14% |
| 4 | transport_0.5 | 67.46% | 66.23% | 66.84% |
| 4 | transport_mix_0.5 | 66.40% | 57.37% | 61.89% |
| 4 | envelope_0.5 | 66.49% | 67.89% | 67.19% |

Ở bốn ổ nguồn mỗi loại, surrogate cũ với tỷ trọng 0,5 tăng trung bình từ 68,46% lên 70,61%, nhưng khoảng bootstrap chênh lệch còn chứa 0. Ở hai ổ nguồn mỗi loại, các bộ sinh được thử đều giảm so với Y chỉ dùng mẫu thật. Không chọn riêng ngân sách hoặc tỷ trọng có lợi để kết luận chung.

Surrogate giữ đường bao với tỷ trọng 0,25 tăng ở ngân sách một và bốn ổ nguồn, nhưng giảm ở ngân sách hai. Tính đúng của phép biến đổi tín hiệu không tự động bảo đảm cải thiện chẩn đoán.

## KAIST: công bố mọi cấu hình

| Quy đổi đơn vị | Bộ phân loại | Phương pháp | Macro recall | Theo từng lớp |
|---|---|---|---:|---|
| metadata | svm1 | Chỉ mẫu thật | 79.66% | 1: 60.9%, 2: 98.4% |
| metadata | svm1 | Sao chép mẫu thật | 80.74% | 1: 62.6%, 2: 98.9% |
| metadata | svm1 | Surrogate cũ | 79.77% | 1: 59.7%, 2: 99.8% |
| metadata | svm1 | Trộn nền cùng máy | 81.26% | 1: 62.5%, 2: 100.0% |
| metadata | svm1 | Chuyển nền phổ | 80.99% | 1: 62.0%, 2: 100.0% |
| metadata | svm1 | Chuyển nền phổ và trộn | 80.34% | 1: 60.7%, 2: 99.9% |
| metadata | svm10 | Chỉ mẫu thật | 80.08% | 1: 61.8%, 2: 98.4% |
| metadata | svm10 | Sao chép mẫu thật | 81.54% | 1: 64.2%, 2: 98.9% |
| metadata | svm10 | Surrogate cũ | 82.11% | 1: 64.3%, 2: 99.9% |
| metadata | svm10 | Trộn nền cùng máy | 82.00% | 1: 64.0%, 2: 100.0% |
| metadata | svm10 | Chuyển nền phổ | 81.29% | 1: 62.6%, 2: 100.0% |
| metadata | svm10 | Chuyển nền phổ và trộn | 80.43% | 1: 60.9%, 2: 100.0% |
| metadata | rf | Chỉ mẫu thật | 98.79% | 1: 98.3%, 2: 99.2% |
| metadata | rf | Sao chép mẫu thật | 100.00% | 1: 100.0%, 2: 100.0% |
| metadata | rf | Surrogate cũ | 100.00% | 1: 100.0%, 2: 100.0% |
| metadata | rf | Trộn nền cùng máy | 98.82% | 1: 97.6%, 2: 100.0% |
| metadata | rf | Chuyển nền phổ | 100.00% | 1: 100.0%, 2: 100.0% |
| metadata | rf | Chuyển nền phổ và trộn | 99.95% | 1: 99.9%, 2: 100.0% |

## HUST6205 đến 6208: công bố mọi cấu hình

| Quy đổi đơn vị | Bộ phân loại | Phương pháp | Macro recall | Theo từng lớp |
|---|---|---|---:|---|
| g | svm1 | Chỉ mẫu thật | 88.73% | 1: 85.6%, 2: 87.5%, 3: 93.1% |
| g | svm1 | Sao chép mẫu thật | 89.51% | 1: 85.6%, 2: 87.5%, 3: 95.4% |
| g | svm1 | Surrogate cũ | 91.26% | 1: 88.9%, 2: 90.1%, 3: 94.8% |
| g | svm1 | Trộn nền cùng máy | 90.43% | 1: 88.6%, 2: 89.4%, 3: 93.4% |
| g | svm1 | Chuyển nền phổ | 91.39% | 1: 86.7%, 2: 89.4%, 3: 98.1% |
| g | svm1 | Chuyển nền phổ và trộn | 92.19% | 1: 88.6%, 2: 92.3%, 3: 95.7% |
| g | svm10 | Chỉ mẫu thật | 88.73% | 1: 85.6%, 2: 87.5%, 3: 93.1% |
| g | svm10 | Sao chép mẫu thật | 89.51% | 1: 85.6%, 2: 87.5%, 3: 95.4% |
| g | svm10 | Surrogate cũ | 89.50% | 1: 86.1%, 2: 95.1%, 3: 87.3% |
| g | svm10 | Trộn nền cùng máy | 91.80% | 1: 92.3%, 2: 91.7%, 3: 91.5% |
| g | svm10 | Chuyển nền phổ | 92.84% | 1: 88.6%, 2: 93.7%, 3: 96.3% |
| g | svm10 | Chuyển nền phổ và trộn | 93.50% | 1: 91.7%, 2: 93.5%, 3: 95.3% |
| g | rf | Chỉ mẫu thật | 93.16% | 1: 95.5%, 2: 90.1%, 3: 93.8% |
| g | rf | Sao chép mẫu thật | 93.09% | 1: 95.8%, 2: 89.4%, 3: 94.1% |
| g | rf | Surrogate cũ | 93.29% | 1: 95.1%, 2: 91.0%, 3: 93.8% |
| g | rf | Trộn nền cùng máy | 90.13% | 1: 88.6%, 2: 87.8%, 3: 94.0% |
| g | rf | Chuyển nền phổ | 93.40% | 1: 96.9%, 2: 89.4%, 3: 93.9% |
| g | rf | Chuyển nền phổ và trộn | 91.93% | 1: 93.8%, 2: 87.2%, 3: 94.8% |
| mks | svm1 | Chỉ mẫu thật | 79.48% | 1: 74.5%, 2: 86.6%, 3: 77.3% |
| mks | svm1 | Sao chép mẫu thật | 79.94% | 1: 75.9%, 2: 86.6%, 3: 77.3% |
| mks | svm1 | Surrogate cũ | 81.07% | 1: 79.8%, 2: 86.1%, 3: 77.3% |
| mks | svm1 | Trộn nền cùng máy | 80.59% | 1: 77.0%, 2: 86.9%, 3: 77.9% |
| mks | svm1 | Chuyển nền phổ | 84.72% | 1: 81.5%, 2: 90.0%, 3: 82.7% |
| mks | svm1 | Chuyển nền phổ và trộn | 83.27% | 1: 79.8%, 2: 88.9%, 3: 81.1% |
| mks | svm10 | Chỉ mẫu thật | 80.40% | 1: 77.3%, 2: 86.6%, 3: 77.3% |
| mks | svm10 | Sao chép mẫu thật | 80.86% | 1: 78.7%, 2: 86.6%, 3: 77.3% |
| mks | svm10 | Surrogate cũ | 85.65% | 1: 89.2%, 2: 90.6%, 3: 77.2% |
| mks | svm10 | Trộn nền cùng máy | 86.26% | 1: 83.3%, 2: 94.6%, 3: 80.8% |
| mks | svm10 | Chuyển nền phổ | 86.83% | 1: 84.9%, 2: 92.0%, 3: 83.6% |
| mks | svm10 | Chuyển nền phổ và trộn | 85.78% | 1: 79.3%, 2: 95.8%, 3: 82.2% |
| mks | rf | Chỉ mẫu thật | 83.43% | 1: 86.0%, 2: 83.0%, 3: 81.3% |
| mks | rf | Sao chép mẫu thật | 82.13% | 1: 82.6%, 2: 81.9%, 3: 81.9% |
| mks | rf | Surrogate cũ | 82.77% | 1: 84.6%, 2: 84.1%, 3: 79.6% |
| mks | rf | Trộn nền cùng máy | 82.51% | 1: 85.6%, 2: 74.1%, 3: 87.8% |
| mks | rf | Chuyển nền phổ | 84.72% | 1: 87.5%, 2: 80.6%, 3: 86.1% |
| mks | rf | Chuyển nền phổ và trộn | 83.28% | 1: 82.6%, 2: 78.9%, 3: 88.4% |

## HUST6204: kiểm tra bổ sung sau khi khóa phương án: công bố mọi cấu hình

| Quy đổi đơn vị | Bộ phân loại | Phương pháp | Macro recall | Theo từng lớp |
|---|---|---|---:|---|
| g | svm1 | Chỉ mẫu thật | 82.41% | 1: 64.8%, 2: 100.0% |
| g | svm1 | Sao chép mẫu thật | 82.41% | 1: 64.8%, 2: 100.0% |
| g | svm1 | Surrogate cũ | 82.41% | 1: 64.8%, 2: 100.0% |
| g | svm1 | Trộn nền cùng máy | 81.48% | 1: 63.0%, 2: 100.0% |
| g | svm1 | Chuyển nền phổ | 81.48% | 1: 63.0%, 2: 100.0% |
| g | svm1 | Chuyển nền phổ và trộn | 80.56% | 1: 63.0%, 2: 98.1% |
| g | svm10 | Chỉ mẫu thật | 82.41% | 1: 64.8%, 2: 100.0% |
| g | svm10 | Sao chép mẫu thật | 82.41% | 1: 64.8%, 2: 100.0% |
| g | svm10 | Surrogate cũ | 81.48% | 1: 63.0%, 2: 100.0% |
| g | svm10 | Trộn nền cùng máy | 84.26% | 1: 68.5%, 2: 100.0% |
| g | svm10 | Chuyển nền phổ | 82.10% | 1: 64.2%, 2: 100.0% |
| g | svm10 | Chuyển nền phổ và trộn | 82.10% | 1: 66.7%, 2: 97.5% |
| g | rf | Chỉ mẫu thật | 98.77% | 1: 97.5%, 2: 100.0% |
| g | rf | Sao chép mẫu thật | 94.14% | 1: 88.3%, 2: 100.0% |
| g | rf | Surrogate cũ | 95.37% | 1: 100.0%, 2: 90.7% |
| g | rf | Trộn nền cùng máy | 94.75% | 1: 90.1%, 2: 99.4% |
| g | rf | Chuyển nền phổ | 98.15% | 1: 100.0%, 2: 96.3% |
| g | rf | Chuyển nền phổ và trộn | 99.38% | 1: 100.0%, 2: 98.8% |
| mks | svm1 | Chỉ mẫu thật | 83.33% | 1: 66.7%, 2: 100.0% |
| mks | svm1 | Sao chép mẫu thật | 83.33% | 1: 66.7%, 2: 100.0% |
| mks | svm1 | Surrogate cũ | 76.54% | 1: 66.7%, 2: 86.4% |
| mks | svm1 | Trộn nền cùng máy | 87.35% | 1: 77.8%, 2: 96.9% |
| mks | svm1 | Chuyển nền phổ | 70.68% | 1: 68.5%, 2: 72.8% |
| mks | svm1 | Chuyển nền phổ và trộn | 76.54% | 1: 66.7%, 2: 86.4% |
| mks | svm10 | Chỉ mẫu thật | 83.33% | 1: 66.7%, 2: 100.0% |
| mks | svm10 | Sao chép mẫu thật | 83.33% | 1: 66.7%, 2: 100.0% |
| mks | svm10 | Surrogate cũ | 84.57% | 1: 100.0%, 2: 69.1% |
| mks | svm10 | Trộn nền cùng máy | 93.52% | 1: 87.0%, 2: 100.0% |
| mks | svm10 | Chuyển nền phổ | 80.86% | 1: 78.4%, 2: 83.3% |
| mks | svm10 | Chuyển nền phổ và trộn | 85.49% | 1: 77.8%, 2: 93.2% |
| mks | rf | Chỉ mẫu thật | 94.75% | 1: 94.4%, 2: 95.1% |
| mks | rf | Sao chép mẫu thật | 89.20% | 1: 84.0%, 2: 94.4% |
| mks | rf | Surrogate cũ | 96.91% | 1: 93.8%, 2: 100.0% |
| mks | rf | Trộn nền cùng máy | 91.67% | 1: 83.3%, 2: 100.0% |
| mks | rf | Chuyển nền phổ | 99.38% | 1: 100.0%, 2: 98.8% |
| mks | rf | Chuyển nền phổ và trộn | 95.68% | 1: 100.0%, 2: 91.4% |

Bộ phân loại chính của kiểm tra ngoài UORED là SVM C1 đã khóa trước khi xem điểm. RF và SVM C10 là kiểm tra độ nhạy. Lớp 1 là vòng trong, lớp 2 là vòng ngoài, lớp 3 là bi.

6204 chưa nằm trong tập phát triển V. Bộ này chỉ có vòng trong và vòng ngoài, nên không so trực tiếp điểm hai lớp với điểm ba lớp của 6205 đến 6208. Phương án chuyển nền phổ không trộn được chọn trước khi xem điểm 6204 vì đã tăng ở cả sáu cấu hình trên tập phát triển HUST. Kết quả 6204 không qua tiêu chí xác nhận: SVM C1 giảm từ 82,41% xuống 81,48% khi giả định g và từ 83,33% xuống 70,68% khi giả định MKS. Không nâng phương án này thành mặc định của MVP.

KAIST gồm 18 cách chia khác tải và giữ riêng mức độ lỗi. HUST gồm 24 hướng chuyển tải trong bốn loại ổ bi; hai giả định đơn vị và ba seed không phải các bộ dữ liệu độc lập. Cùng mẫu hỏng có thể xuất hiện ở nhiều tải, vì vậy các phép thử này không chứng minh khả năng tổng quát sang ổ hỏng độc lập.

HUST có năm tệp ngắn hơn thời lượng công bố. Giữ nguyên các tệp đã khớp SHA256, dùng mọi cửa sổ đủ độ dài, không lặp hoặc đệm dữ liệu. Đơn vị native-as-g và native-as-m/s² đều là giả định; phải xác nhận đơn vị trước khi kết luận về cảm biến.

### Tỷ lệ tín hiệu gốc vượt dải giả định

- HUST g: lớn nhất 3.6375% ở I600.
- HUST mks: lớn nhất 0.0000% ở B500.

## Kiểm tra mẫu sinh và giới hạn

- Trộn nền cùng máy: tỷ lệ clipping lớn nhất trong các cặp UORED là 0.0066%.
- Chuyển nền phổ: tỷ lệ clipping lớn nhất trong các cặp UORED là 1.9723%.
- Chuyển nền phổ và trộn: tỷ lệ clipping lớn nhất trong các cặp UORED là 0.8895%.

Đối chứng sao chép đặc biệt quan trọng: RF có điều kiện tối thiểu số dòng ở lá, SVM dùng gamma phụ thuộc phân bố các dòng. Vì vậy ngay cả sao chép cũng có thể thay đổi mô hình dù tổng trọng số được giữ nguyên. Chỉ thắng mẫu thật mà không thắng sao chép chưa đủ chứng minh giá trị của bộ sinh.

Các đường sóng và phổ minh họa chỉ chứng minh tín hiệu được tạo và có thể kiểm tra, không chứng minh nhãn lỗi hoặc mức độ hỏng luôn đúng. Chưa có xác nhận chuyên gia cơ khí cho mọi mẫu sinh.

Chưa chứng minh lỗi thiếu bôi trơn, tạp chất và thời gian còn lại tới hỏng trong nhà máy. Không dùng kết quả này để công bố đã giải quyết đủ yêu cầu DENSO. Mô hình chạy thật vẫn cần kiểm thử cảnh báo đầu vào, cảm biến thực và chu kỳ bảo trì.

## Nguồn dữ liệu và cách chạy lại

- [UORED, Mendeley V5](https://data.mendeley.com/datasets/y2px5tg92h/5).
- [KAIST, Mendeley V6](https://data.mendeley.com/datasets/ztmf3m7h5x/6).
- [HUST, Mendeley V3](https://data.mendeley.com/datasets/cbv7jyx4p9/3).
- [Bài báo HUST](https://pmc.ncbi.nlm.nih.gov/articles/PMC10327369/).
- [FDA, nguồn tham khảo về thích nghi phổ](https://openaccess.thecvf.com/content_CVPR_2020/html/Yang_FDA_Fourier_Domain_Adaptation_for_Semantic_Segmentation_CVPR_2020_paper.html).

```powershell
python anchorspec/v_transport_run.py prepare
python anchorspec/v_transport_run.py run
python anchorspec/v_external.py kaist
python anchorspec/v_hust_data.py
python anchorspec/v_hust_eval.py hust
python anchorspec/v_champion.py prepare
python anchorspec/v_champion.py run
python anchorspec/v_holdout6204.py download
python anchorspec/v_holdout6204.py run
python anchorspec/v_report.py
```

Dữ liệu gốc, cache và checkpoint ở thư mục data được gitignore. Cần dữ liệu Y và W trước khi chạy V; các script tải và chuẩn bị nằm trong báo cáo W. Mã nguồn đã được băm trước khi chạy; kết quả chứa dấu vết cấu hình và nguồn từng mẫu.
