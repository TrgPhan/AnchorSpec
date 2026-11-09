# Cải tiến bộ sinh học sâu để chạy CPU

Ngày 06/11/2026. Đã hoàn tất S3 trên 13 ổ XJTU với ba seed, tiếp tục đối chiếu số bước lấy mẫu bằng S3B. Không sử dụng GPU.

**Kết quả chính:** flow matching học phần dư phổ quanh tín hiệu thật đạt recall trung bình cuối vòng đời 77,22%, so với 64,81% của flow đủ hạng trước đó. Chưa đủ bằng chứng kết luận thắng chắc surrogate hoặc dùng trực tiếp tại DENSO.

[Excel đầy đủ](results/s3/AnchorSpec_CPU_Benchmark_20261106.xlsx). [CSV so sánh](results/s3/comparisons.csv). [Protocol S3](PROTOCOL_S3_CPU_RESIDUAL.md). [Protocol số bước](PROTOCOL_S3B_STEPS.md).

## Vì sao bản học sâu trước chưa tốt?

1. **Biểu diễn làm mất thông tin:** PCA 32 giữ trung bình 45.66% phương sai huấn luyện. Nhưng PCA đủ hạng vẫn không cứu được lỗi vòng cách, nên nén không phải nguyên nhân duy nhất.
2. **Ít sự kiện độc lập:** mỗi lượt chỉ học từ 120 đoạn lỗi thuộc 12 ổ. Khi kiểm tra một ổ lỗi vòng cách, nguồn chỉ còn một ổ vòng cách. Thêm vòng huấn luyện hoặc sinh nhiều mẫu không tạo thêm cơ chế hỏng độc lập.
3. **Tín hiệu sinh bị biến dạng:** diffusion đủ hạng có trung bình 13.76% giá trị tín hiệu vượt dải 8 g trước bước cắt đỉnh cuối. Dữ liệu thật đã trừ trung bình sau mô phỏng cảm biến, nên cắt lại tại 8 g còn gây khác biệt trong cách xử lý.
4. **Mục tiêu học chưa gắn trực tiếp với chẩn đoán:** sai số dự đoán nhiễu hoặc vận tốc thấp không bảo đảm giữ đặc trưng lỗi. Học toàn bộ dạng sóng còn phải xử lý pha không được căn chỉnh. Đây là lý do có cơ sở để thử biểu diễn khác, chưa phải kết luận nhân quả đã được tách riêng bằng ablation.

Kiểm tra riêng lớp vòng cách cho thấy kurtosis trung bình của nguồn khoảng 0,384, còn diffusion đủ hạng khoảng -0,609. Tỷ lệ khớp nhãn theo tâm lớp trong không gian đặc trưng nguồn giảm từ 95,38% của mẫu thật xuống 47,95%. Đây chỉ là kiểm tra mô tả trên nguồn, không phải bằng chứng độc lập rằng từng nhãn sinh đúng hay sai.

## Phương pháp mới

Tên mô tả: **AnchorSpec Spectral Residual Flow**, nghĩa là flow matching học biến đổi phổ quanh tín hiệu lỗi thật. Tên này chưa hàm ý một phương pháp mới đã được công nhận trong nghiên cứu.

1. Giữ một đoạn lỗi thật của ổ nguồn làm tín hiệu nền.
2. Đo chênh lệch log biên độ giữa các đoạn cùng ổ trong 24 dải tần đến 1 kHz.
3. Mạng nhỏ học phân bố chênh lệch, có điều kiện theo phổ nền, loại lỗi, tốc độ và RMS khỏe của nguồn.
4. Sinh phần biến đổi với 16 bước rồi áp vào phổ phức của tín hiệu nền, giữ pha gốc.
5. Giới hạn biến đổi bằng dữ liệu nguồn, dựng lại waveform và tính 45 đặc trưng.
6. Giữ nguyên 125 mẫu thật cùng trọng số, thêm 120 mẫu sinh ở alpha bằng 0,25 rồi huấn luyện RF.

Mạng có hai lớp ẩn, mỗi lớp 64 nút, tổng cộng 9.688 tham số. So sánh cả flow matching và diffusion dự đoán v với DDIM. Mỗi mạng học 2.000 bước trên CPU một luồng. Có 1.080 cặp dẫn xuất từ 120 đoạn, không coi các cặp này là sự kiện hỏng mới.

Phương pháp giữ nguyên pha nhưng vẫn có thể làm đổi đường bao do thay biên độ phổ. Mức tương quan trung bình với mẫu nền khoảng 0,994; đây là tăng cường dữ liệu có kiểm soát, không phải sinh một lỗi cơ khí độc lập từ con số không. Chuỗi xử lý mới không cắt lại tín hiệu đã trừ trung bình tại 8 g; không được hiểu là đã mô phỏng chính xác cảm biến nhà máy.

## So sánh cùng lượng dữ liệu và trọng số

| Phương pháp | Recall trước đoạn cuối | Recall cuối | Vòng trong | Vòng ngoài | Vòng cách | Gán lỗi trên mẫu khỏe |
|---|---:|---:|---:|---:|---:|---:|
| Chỉ mẫu thật | 58.75% | 68.33% | 93.33% | 100.00% | 11.67% | 0.00% |
| Thêm bản sao | 68.06% | 72.64% | 86.67% | 99.58% | 31.67% | 0.00% |
| Surrogate cũ | 64.17% | 74.26% | 91.11% | 100.00% | 31.67% | 0.00% |
| Trộn nền cùng ổ | 69.91% | 77.22% | 83.33% | 100.00% | 48.33% | 1.03% |
| Flow matching đủ hạng | 59.68% | 64.81% | 94.44% | 100.00% | 0.00% | 0.00% |
| Diffusion đủ hạng | 59.86% | 66.30% | 98.89% | 100.00% | 0.00% | 0.00% |
| Bootstrap phần dư mức 0,5 | 60.79% | 65.74% | 82.22% | 100.00% | 15.00% | 0.00% |
| Gaussian phần dư mức 0,5 | 70.88% | 74.21% | 85.56% | 98.75% | 38.33% | 0.00% |
| Flow phần dư mức 0,5 | 70.42% | 77.22% | 90.00% | 100.00% | 41.67% | 0.00% |
| Diffusion phần dư mức 0,5 | 67.31% | 72.82% | 85.56% | 99.58% | 33.33% | 0.00% |

Mẫu khỏe là 65 đoạn được giả định khỏe, lặp lại ba seed. Không ghi nhận gán lỗi trong benchmark không có nghĩa tỷ lệ cảnh báo giả ngoài nhà máy bằng 0.

**Mức cải thiện của flow phần dư 16 bước:**

- So flow đủ hạng cũ: +12.41 điểm, CI 95% [-5.93; +30.74].
- So thêm bản sao: +4.58 điểm, CI 95% [-0.60; +9.77].
- So surrogate cũ: +2.96 điểm, CI 95% [-4.44; +10.37].
- So Gaussian phần dư: +3.01 điểm, CI 95% [-4.03; +11.11].

Điểm trung bình bằng trộn nền cùng ổ, nhưng recall vòng cách thấp hơn; chưa thể gọi là thắng trên mọi tiêu chí. Khoảng tin cậy so với surrogate và Gaussian vẫn chứa 0. Các phép thử đã xem nhiều lần trên cùng cohort, nên các khoảng bootstrap chỉ mang tính thăm dò.

## Độ nhạy mức biến đổi và số bước

| Cấu hình | Recall cuối | Vòng cách | Gán lỗi mẫu khỏe |
|---|---:|---:|---:|
| Bootstrap phần dư mức 0,5 | 65.74% | 15.00% | 0.00% |
| Bootstrap phần dư mức 1,0 | 66.11% | 11.67% | 0.00% |
| Gaussian phần dư mức 0,5 | 74.21% | 38.33% | 0.00% |
| Gaussian phần dư mức 1,0 | 66.94% | 18.33% | 0.00% |
| Flow phần dư mức 0,5 | 77.22% | 41.67% | 0.00% |
| Flow phần dư mức 1,0 | 71.11% | 30.00% | 0.00% |
| Diffusion phần dư mức 0,5 | 72.82% | 33.33% | 0.00% |
| Diffusion phần dư mức 1,0 | 70.56% | 31.67% | 0.00% |
| Flow phần dư 4 bước | 75.42% | 43.33% | 0.00% |
| Flow phần dư 8 bước | 74.44% | 36.67% | 0.00% |
| Flow phần dư 32 bước | 76.85% | 41.67% | 0.00% |
| Diffusion phần dư 4 bước | 71.16% | 28.33% | 0.00% |
| Diffusion phần dư 8 bước | 72.08% | 33.33% | 0.00% |
| Diffusion phần dư 32 bước | 74.86% | 41.67% | 0.00% |

Tăng mức biến đổi flow từ 0,5 lên 1 làm recall giảm từ 77,22% xuống 71,11%. Giảm còn tám bước làm recall còn 74,44%. Vì vậy giữ nguyên cấu hình chính 16 bước; không mặc định ít bước hoặc biến đổi mạnh hơn sẽ tốt hơn.

## Chi phí CPU

Thời gian huấn luyện trung bình mỗi mạng: flow 1.89 giây; diffusion 1.82 giây. Đo trong lượt chạy ba worker, mỗi worker một luồng; không phải phép đo trên Raspberry Pi.

Bảng dưới đo 120 waveform, mỗi waveform 4.000 điểm; một lượt khởi động và mười lượt đo. Hai cách thực thi được chạy xen kẽ trên cùng máy. Không gồm đọc checkpoint, huấn luyện hoặc suy luận RF. Chi phí tạo cache được ghi riêng.

| Bộ sinh | Thực thi | Sinh và dựng lại, trung vị | Tính đặc trưng, trung vị | Tổng, trung vị | Tổng P95 | Tạo cache |
|---|---|---:|---:|---:|---:|---:|
| flow | original | 29.61 ms | 419.23 ms | 449.64 ms | 525.32 ms | 0.00 ms |
| flow | cached | 19.10 ms | 298.77 ms | 319.04 ms | 396.16 ms | 42.14 ms |
| diffusion | original | 39.27 ms | 525.43 ms | 559.08 ms | 686.26 ms | 0.00 ms |
| diffusion | cached | 23.94 ms | 372.31 ms | 401.90 ms | 466.53 ms | 24.25 ms |

Cache giữ phổ của tín hiệu nền và các hằng số bộ lọc. Đã kiểm tra waveform, đặc trưng và toàn bộ score RF trùng chính xác trên 78 lượt mô hình của S3. Bản thử nội suy thưa và gom tín hiệu theo tốc độ trước đó lại chậm hơn, nên không chọn; số đo được giữ trong sheet CPU_rejected.

Thời gian tuyệt đối biến động đáng kể giữa các lượt đo trên máy phát triển. Chỉ dùng hai cách thực thi chạy xen kẽ trong cùng bảng để tính mức tăng tốc; không đối chiếu các lần chạy khác tải máy thành một tuyên bố tăng tốc. Mười lần đo và P95 này chưa đủ để cam kết độ trễ vận hành.

Các bản học sâu cũ đã chạy CPU. Lợi ích mới đến từ giảm số tham số từ 66.680 xuống 9.688, giảm số bước lấy mẫu, thay biểu diễn và tái sử dụng phép tính; không phải chuyển từ GPU sang CPU. Thời gian tính đặc trưng vẫn chiếm phần lớn tổng thời gian.

## Chạy và kiểm tra

```powershell
python s3_generate_cpu.py --target 1_1 --seed 11 --kind flow
python s3_cpu_benchmark.py --workers 3
python s3b_steps.py
python s3_diagnostics.py
python s3_cached_profile.py
python s3_report.py
python -m pytest -q
```

Kiểm tra sau thay đổi cuối cùng: 136 bài kiểm tra đạt trong 38,65 giây. Kiểm tra gồm nguồn đóng băng, loại trừ ổ đích, trọng số mẫu, dựng lại dự đoán, tính lại recall và tính tương đương của cache.

Lệnh sinh mặc định xuất 120 waveform cùng đặc trưng, nhãn nguồn và checksum vào data/s3_cpu_export. Target là ổ bị loại khỏi thư viện nguồn; không phải máy được dùng để học lỗi. Checkpoint và dữ liệu công khai cần tồn tại ở cache cục bộ.

## Việc chưa được chứng minh

- Chưa có kiểm chứng độc lập trên cohort mới cho bộ sinh vừa phát triển.
- Lớp vòng cách chỉ có hai ổ; thiếu bôi trơn, dị vật và lỗi ngoài thư viện chưa được xác nhận.
- Không thể quy toàn bộ mức tăng cho mạng học sâu vì biểu diễn, anchoring và xử lý đầu ra cùng thay đổi.
- Chưa đo độ trễ thiết bị DENSO, hiệu quả bảo trì, tiết kiệm downtime hoặc mức cảnh báo giả theo ca.

Hướng đáng giữ hiện tại là bộ sinh phần dư nhỏ, có tín hiệu thật làm nền. Cần khóa cấu hình này rồi kiểm tra trên sự kiện mới; tiếp tục chọn điểm cao nhất trên cùng 13 ổ sẽ không tạo thêm bằng chứng tổng quát hóa.

## Tài liệu

- [Flow Matching](https://arxiv.org/abs/2210.02747): cơ sở học trường vận tốc.
- [DDIM](https://arxiv.org/abs/2010.02502): lấy mẫu diffusion với ít bước hơn.
- [Time Series Diffusion in the Frequency Domain](https://arxiv.org/abs/2402.05933): động cơ nghiên cứu biểu diễn miền tần số; không phải bằng chứng cho cấu hình DENSO này.
- [Benchmark đầy đủ trước S3](FULL_BENCHMARK_VA_UU_TIEN_NHA_MAY_20261106.md).
