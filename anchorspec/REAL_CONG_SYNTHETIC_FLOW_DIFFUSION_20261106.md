# Giữ mẫu thật và bổ sung mẫu sinh: surrogate, flow matching, diffusion

Ngày 06/11/2026. Thử nghiệm S trả lời việc số lượng và trọng số train ảnh hưởng kết quả như thế nào. Đây là nghiên cứu tiếp trên XJTU đã dùng trước đó, chưa phải xác nhận trên dữ liệu mới hoặc nhà máy.

## Trả lời câu hỏi về các thử nghiệm trước

**Các đợt U và T đã dùng mẫu thật cộng mẫu sinh, không thay mẫu thật bằng mẫu sinh và không ép tổng số dòng train bằng nhau.**

| Trường hợp | Mẫu thật giữ lại | Mẫu sinh thêm | Tổng dòng train |
|---|---:|---:|---:|
| U, chỉ mẫu thật | 130 | 0 | 130 |
| U, giữ lại một ổ vòng ngoài để test | 130 | 190 | 320 |
| U, giữ lại một ổ vòng cách để test | 130 | 191 | 321 |
| U, giữ lại một ổ vòng trong để test | 130 | 192 | 322 |
| T, chỉ mẫu thật | 125 | 0 | 125 |
| T, thêm mẫu sinh tùy lớp ổ giữ lại | 125 | 190 đến 192 | 315 đến 317 |

U dùng10healthy và120faultwindows. T dùng5healthy và120faultwindows, giữ5healthy còn lại để test. Số lượng là cửa sổ tín hiệu; không phải số sự kiện hỏng độc lập.

Điểm khác nằm ở trọng số: U/T trước đó phân bổ75% tổng trọng số fault cho mẫu thật và25% cho mẫu sinh. Healthy có trọng số riêng. Cân bằng tổng trọng số không đồng nghĩa cân bằng số lượng train. Cách cũ giữ mẫu thật nhưng giảm ảnh hưởng tương đối của nó.

## Phép thử mới giữ nguyên cả trọng số mẫu thật

| Tỷ lệ mẫu sinh so với120faultwindows | Mẫu thật | Mẫu sinh | Tổng train |
|---|---:|---:|---:|
| 0 | 125 | 0 | 125 |
| 0.5 | 125 | 60 | 185 |
| 1 | 125 | 120 | 245 |
| 2 | 125 | 240 | 365 |

Mọi dòng và sample weight của125mẫu thật giữ nguyên. Mỗi mẫu sinh nhận0.25 hoặc1 lần trọng số một faultwindow thật thuộc cùng donor. Các phương pháp có cùng số mẫu sinh và cùng weight ở mỗi phép so.

Khi thêm faultwindows nhưng không thêm healthy, tổng trọng số healthy và fault thay đổi. Đối chứng thêm bản sao đo hiệu ứng này. Vì vậy duplicate mới có thể đổi dự đoán mà không mâu thuẫn với đối chứng cố định phân bố của U/T.

## Diffusion và flow matching đã triển khai

Hai prototype cùng codec và kiến trúc nhỏ: waveform4000điểm được demean và chuẩn hóa RMS, nén thành32PC cộng logRMS. PCA và scaler chỉ fit12ổ donor. Điều kiện gồm loại lỗi, tốc độ donor và logRMS nền khỏe donor. Không sử dụng lỗi ổ đích để fit, chọn checkpoint hoặc lọc mẫu.

Flow matching học trường vận tốc trên đường thẳng từ Gaussian noise tới latent, lấy mẫu50bước Euler. DDPM học dự đoán noise, cosine schedule100bước và lấy mẫu theo posterior DDPM. CùngMLP128ba tầng ẩn, batch32,1500updates. Có78model học sâu, nhưng chỉ13ổ đánh giá; không phải78thí nghiệm độc lập.

Đây là prototype trong không gian nén, chưa phải waveform U-Net hoặc tái lập đầy đủ các mô hình fault-generation chuyên biệt. Nếu prototype kém không được suy ra cả họ diffusion hay flow matching đều kém. PCA có thể mất xung nên có thêm đối chứng PCA reconstruction bootstrap.

## Kết quả tại liều đặt trước

Ratio1, alpha0.25:125mẫu thật cộng120mẫu sinh, trừ baseline chỉ125mẫu thật. RF và45features như T. Chính sách selective chọn cả lớp khỏe, không ngưỡng score thêm. Từ chối hoặc chọn healthy trên fault không được tính là chẩn đoán đúng.

| Phương pháp | Trước đoạn cuối | Đoạn cuối | Vòng trong cuối | Vòng ngoài cuối | Vòng cách cuối | Gán lỗi trên healthy giả định |
|---|---:|---:|---:|---:|---:|---:|
| Chỉ mẫu thật | 58.75% | 68.33% | 93.33% | 100.00% | 11.67% | 0.00% |
| Thêm bản sao | 68.06% | 72.64% | 86.67% | 99.58% | 31.67% | 0.00% |
| Thêm surrogate cũ | 64.17% | 74.26% | 91.11% | 100.00% | 31.67% | 0.00% |
| Thêm surrogate giữ đường bao | 65.46% | 74.07% | 85.56% | 100.00% | 36.67% | 0.00% |
| Thêm trộn nền cùng ổ | 69.91% | 77.22% | 83.33% | 100.00% | 48.33% | 1.03% |
| Thêm mẫu dựng lại qua PCA | 58.43% | 62.96% | 88.89% | 100.00% | 0.00% | 0.00% |
| Thêm flow matching | 53.70% | 61.06% | 81.11% | 98.75% | 3.33% | 0.00% |
| Thêm diffusion | 53.56% | 63.15% | 91.11% | 98.33% | 0.00% | 0.00% |

### Chênh lệch của hai prototype so với đối chứng cùng liều

**Thêm flow matching**

- So Chỉ mẫu thật: -7.27 điểm, CI thăm dò [-12.27; -2.22].
- So Thêm bản sao: -11.57 điểm, CI thăm dò [-22.50; -0.65].
- So Thêm surrogate cũ: -13.19 điểm, CI thăm dò [-25.97; +0.00].

**Thêm diffusion**

- So Chỉ mẫu thật: -5.19 điểm, CI thăm dò [-10.37; +0.00].
- So Thêm bản sao: -9.49 điểm, CI thăm dò [-21.11; +2.22].
- So Thêm surrogate cũ: -11.11 điểm, CI thăm dò [-23.89; +1.67].

## Tất cả liều đã chốt trước, không chỉ cấu hình tốt nhất

Không dùng bảng này chọn best test rồi gọi là xác nhận. Conditional chỉ chọn lớp lỗi, giả định alarm đã đúng; không đồng nghĩa selective hoặc hiệu quả end-to-end nhà máy.

| Policy | Bộ sinh | Ratio | Alpha | Recall trước cuối | Recall cuối | Vòng cách cuối | Gán lỗi healthy |
|---|---|---:|---:|---:|---:|---:|---:|
| selective | Chỉ mẫu thật | 0 | 0 | 58.75% | 68.33% | 11.67% | 0.00% |
| selective | Thêm bản sao | 0.5 | 0.25 | 66.39% | 71.30% | 25.00% | 0.00% |
| selective | Thêm bản sao | 0.5 | 1 | 73.43% | 76.30% | 43.33% | 0.00% |
| selective | Thêm bản sao | 1 | 0.25 | 68.06% | 72.64% | 31.67% | 0.00% |
| selective | Thêm bản sao | 1 | 1 | 66.11% | 72.41% | 38.33% | 0.00% |
| selective | Thêm bản sao | 2 | 0.25 | 65.65% | 71.48% | 30.00% | 0.00% |
| selective | Thêm bản sao | 2 | 1 | 64.81% | 73.89% | 41.67% | 0.00% |
| selective | Thêm surrogate cũ | 0.5 | 0.25 | 66.85% | 70.97% | 20.00% | 0.00% |
| selective | Thêm surrogate cũ | 0.5 | 1 | 68.43% | 73.89% | 38.33% | 0.00% |
| selective | Thêm surrogate cũ | 1 | 0.25 | 64.17% | 74.26% | 31.67% | 0.00% |
| selective | Thêm surrogate cũ | 1 | 1 | 65.42% | 74.07% | 33.33% | 0.00% |
| selective | Thêm surrogate cũ | 2 | 0.25 | 67.69% | 72.59% | 36.67% | 0.00% |
| selective | Thêm surrogate cũ | 2 | 1 | 65.51% | 72.41% | 38.33% | 1.03% |
| selective | Thêm surrogate giữ đường bao | 0.5 | 0.25 | 64.91% | 71.30% | 25.00% | 0.00% |
| selective | Thêm surrogate giữ đường bao | 0.5 | 1 | 69.17% | 74.26% | 41.67% | 0.00% |
| selective | Thêm surrogate giữ đường bao | 1 | 0.25 | 65.46% | 74.07% | 36.67% | 0.00% |
| selective | Thêm surrogate giữ đường bao | 1 | 1 | 62.13% | 69.81% | 28.33% | 0.51% |
| selective | Thêm surrogate giữ đường bao | 2 | 0.25 | 67.31% | 73.70% | 40.00% | 0.00% |
| selective | Thêm surrogate giữ đường bao | 2 | 1 | 61.30% | 72.08% | 36.67% | 0.51% |
| selective | Thêm trộn nền cùng ổ | 0.5 | 0.25 | 65.79% | 74.12% | 31.67% | 0.51% |
| selective | Thêm trộn nền cùng ổ | 0.5 | 1 | 66.34% | 71.30% | 35.00% | 0.00% |
| selective | Thêm trộn nền cùng ổ | 1 | 0.25 | 69.91% | 77.22% | 48.33% | 1.03% |
| selective | Thêm trộn nền cùng ổ | 1 | 1 | 67.82% | 74.49% | 45.00% | 0.00% |
| selective | Thêm trộn nền cùng ổ | 2 | 0.25 | 70.93% | 75.60% | 45.00% | 0.00% |
| selective | Thêm trộn nền cùng ổ | 2 | 1 | 61.34% | 71.16% | 31.67% | 0.00% |
| selective | Thêm mẫu dựng lại qua PCA | 0.5 | 0.25 | 61.90% | 63.33% | 3.33% | 0.00% |
| selective | Thêm mẫu dựng lại qua PCA | 0.5 | 1 | 59.68% | 64.07% | 3.33% | 0.00% |
| selective | Thêm mẫu dựng lại qua PCA | 1 | 0.25 | 58.43% | 62.96% | 0.00% | 0.00% |
| selective | Thêm mẫu dựng lại qua PCA | 1 | 1 | 59.17% | 58.94% | 0.00% | 0.00% |
| selective | Thêm mẫu dựng lại qua PCA | 2 | 0.25 | 60.65% | 62.96% | 0.00% | 0.00% |
| selective | Thêm mẫu dựng lại qua PCA | 2 | 1 | 55.14% | 58.15% | 0.00% | 0.00% |
| selective | Thêm flow matching | 0.5 | 0.25 | 55.23% | 62.45% | 0.00% | 0.00% |
| selective | Thêm flow matching | 0.5 | 1 | 54.91% | 61.90% | 0.00% | 0.00% |
| selective | Thêm flow matching | 1 | 0.25 | 53.70% | 61.06% | 3.33% | 0.00% |
| selective | Thêm flow matching | 1 | 1 | 51.99% | 56.85% | 0.00% | 0.00% |
| selective | Thêm flow matching | 2 | 0.25 | 57.69% | 60.74% | 0.00% | 0.00% |
| selective | Thêm flow matching | 2 | 1 | 51.99% | 56.34% | 0.00% | 0.00% |
| selective | Thêm diffusion | 0.5 | 0.25 | 56.90% | 61.85% | 0.00% | 0.00% |
| selective | Thêm diffusion | 0.5 | 1 | 49.17% | 54.86% | 0.00% | 0.00% |
| selective | Thêm diffusion | 1 | 0.25 | 53.56% | 63.15% | 0.00% | 0.00% |
| selective | Thêm diffusion | 1 | 1 | 51.85% | 54.81% | 0.00% | 0.00% |
| selective | Thêm diffusion | 2 | 0.25 | 58.33% | 65.19% | 1.67% | 0.00% |
| selective | Thêm diffusion | 2 | 1 | 50.74% | 54.68% | 0.00% | 1.54% |
| conditional | Chỉ mẫu thật | 0 | 0 | 69.58% | 76.11% | 35.00% | 100.00% |
| conditional | Thêm bản sao | 0.5 | 0.25 | 74.03% | 75.19% | 36.67% | 100.00% |
| conditional | Thêm bản sao | 0.5 | 1 | 78.98% | 77.96% | 48.33% | 100.00% |
| conditional | Thêm bản sao | 1 | 0.25 | 75.28% | 77.64% | 46.67% | 100.00% |
| conditional | Thêm bản sao | 1 | 1 | 73.33% | 75.74% | 48.33% | 100.00% |
| conditional | Thêm bản sao | 2 | 0.25 | 72.73% | 77.04% | 46.67% | 100.00% |
| conditional | Thêm bản sao | 2 | 1 | 69.26% | 75.56% | 46.67% | 100.00% |
| conditional | Thêm surrogate cũ | 0.5 | 0.25 | 74.21% | 77.64% | 40.00% | 100.00% |
| conditional | Thêm surrogate cũ | 0.5 | 1 | 74.95% | 77.22% | 48.33% | 99.49% |
| conditional | Thêm surrogate cũ | 1 | 0.25 | 74.58% | 79.26% | 46.67% | 100.00% |
| conditional | Thêm surrogate cũ | 1 | 1 | 73.06% | 77.96% | 45.00% | 100.00% |
| conditional | Thêm surrogate cũ | 2 | 0.25 | 75.88% | 77.04% | 50.00% | 100.00% |
| conditional | Thêm surrogate cũ | 2 | 1 | 71.48% | 75.74% | 48.33% | 100.00% |
| conditional | Thêm surrogate giữ đường bao | 0.5 | 0.25 | 72.41% | 75.19% | 36.67% | 100.00% |
| conditional | Thêm surrogate giữ đường bao | 0.5 | 1 | 74.03% | 75.37% | 45.00% | 100.00% |
| conditional | Thêm surrogate giữ đường bao | 1 | 0.25 | 73.94% | 77.96% | 48.33% | 100.00% |
| conditional | Thêm surrogate giữ đường bao | 1 | 1 | 69.91% | 74.81% | 43.33% | 100.00% |
| conditional | Thêm surrogate giữ đường bao | 2 | 0.25 | 74.26% | 76.48% | 48.33% | 99.49% |
| conditional | Thêm surrogate giữ đường bao | 2 | 1 | 66.57% | 75.42% | 46.67% | 100.00% |
| conditional | Thêm trộn nền cùng ổ | 0.5 | 0.25 | 72.45% | 76.90% | 40.00% | 100.00% |
| conditional | Thêm trộn nền cùng ổ | 0.5 | 1 | 73.70% | 75.19% | 46.67% | 100.00% |
| conditional | Thêm trộn nền cùng ổ | 1 | 0.25 | 73.10% | 77.22% | 48.33% | 100.00% |
| conditional | Thêm trộn nền cùng ổ | 1 | 1 | 76.30% | 75.60% | 48.33% | 99.49% |
| conditional | Thêm trộn nền cùng ổ | 2 | 0.25 | 75.93% | 76.71% | 48.33% | 100.00% |
| conditional | Thêm trộn nền cùng ổ | 2 | 1 | 68.98% | 73.38% | 38.33% | 100.00% |
| conditional | Thêm mẫu dựng lại qua PCA | 0.5 | 0.25 | 68.70% | 70.00% | 23.33% | 100.00% |
| conditional | Thêm mẫu dựng lại qua PCA | 0.5 | 1 | 63.01% | 67.96% | 15.00% | 100.00% |
| conditional | Thêm mẫu dựng lại qua PCA | 1 | 0.25 | 62.18% | 66.30% | 10.00% | 99.49% |
| conditional | Thêm mẫu dựng lại qua PCA | 1 | 1 | 63.33% | 58.94% | 0.00% | 99.49% |
| conditional | Thêm mẫu dựng lại qua PCA | 2 | 0.25 | 64.40% | 62.96% | 0.00% | 100.00% |
| conditional | Thêm mẫu dựng lại qua PCA | 2 | 1 | 58.89% | 58.15% | 0.00% | 100.00% |
| conditional | Thêm flow matching | 0.5 | 0.25 | 59.12% | 62.45% | 0.00% | 100.00% |
| conditional | Thêm flow matching | 0.5 | 1 | 59.35% | 61.90% | 0.00% | 99.49% |
| conditional | Thêm flow matching | 1 | 0.25 | 61.20% | 63.84% | 11.67% | 99.49% |
| conditional | Thêm flow matching | 1 | 1 | 58.10% | 59.63% | 8.33% | 100.00% |
| conditional | Thêm flow matching | 2 | 0.25 | 61.85% | 60.74% | 0.00% | 99.49% |
| conditional | Thêm flow matching | 2 | 1 | 56.16% | 56.34% | 0.00% | 100.00% |
| conditional | Thêm diffusion | 0.5 | 0.25 | 60.65% | 65.19% | 10.00% | 99.49% |
| conditional | Thêm diffusion | 0.5 | 1 | 54.44% | 59.31% | 13.33% | 99.49% |
| conditional | Thêm diffusion | 1 | 0.25 | 60.65% | 65.93% | 8.33% | 100.00% |
| conditional | Thêm diffusion | 1 | 1 | 53.80% | 54.81% | 0.00% | 100.00% |
| conditional | Thêm diffusion | 2 | 0.25 | 64.31% | 68.52% | 11.67% | 100.00% |
| conditional | Thêm diffusion | 2 | 1 | 54.35% | 54.68% | 0.00% | 100.00% |

## Kiểm tra codec, mẫu sinh và chi phí

PCA explained variance trung bình qua các lượt: 45.66%.
Sai số tái dựng waveform L2 tương đối trung bình: 0.7281.

| Phương pháp | Clamp latent trung bình | Clip8g trung bình | Tương quan gần nhất với train, trung bình | Thời gian fit mỗi model, trung bình |
|---|---:|---:|---:|---:|
| Thêm flow matching | 0.63% | 0.04% | 0.4111 | 4.81s |
| Thêm diffusion | 0.12% | 0.04% | 0.4096 | 4.60s |
| Thêm mẫu dựng lại qua PCA | 0.89% | 0.01% | 0.6706 | Không học mạng |

Tương quan đo tại độ trễ0 với các waveform train, không phải kiểm tra sao chép bất biến với dịch pha. Unique waveform không đồng nghĩa sự kiện lỗi mới. Giới hạn latent lấy từ train và giới hạn đầu ra cảm biến là xử lý số học, chưa chứng minh nhãn cơ học đúng.

## Điều có thể và chưa thể kết luận

Đề xuất giữ real rồi thêm synthetic đã được thử trực tiếp, cả về số lượng và trọng số. Không cần synthetic tái hiện100% một waveform thật; cần biến thể giữ thông tin lỗi hữu ích và cải thiện kiểm tra trên ổ ngoài train. Tín hiệu trông giống, loss thấp hoặc samplecount lớn chưa đủ chứng minh điều đó.

Hai ổ vòng cách vẫn là giới hạn lớn. Khi giữ một ổ để test, generator chỉ còn một ổ vòng cách nguồn; hàng trăm cửa sổ sinh không bổ sung sự kiện cơ khí độc lập. Các healthy snapshots chưa xác minh nhãn khỏe. Không có validation DENSO, bôi trơn, dị vật hoặc lỗi lạ trong phép thử S.

Baseline real tái dựng đúng toàn bộ raw scores của T. Source, input và protocol lưuhash; các mẫu và weights thật không bị thay đổi. Không đổi mặc định runtimeMVP. Cần kiểm tra ngoài tập phát triển trước bất kỳ tuyên bố phương pháp tốt nhất nào.

## Tái lập và nguồn

```powershell
python s_additive.py --workers 3
python s_report.py
python -m pytest -q
```

- [Protocol chốt trước S](PROTOCOL_S_GENERATION.md).
- [Flow Matching for Generative Modeling](https://arxiv.org/abs/2210.02747).
- [Denoising Diffusion Probabilistic Models](https://arxiv.org/abs/2006.11239).
- [Kết quả đầy đủ](results/s/additive.json).
- Checkpoint và waveform cục bộ: data/s_generation, không đưa vào Git.
