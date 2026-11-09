# Mẫu thật cộng mẫu sinh: kết quả diffusion và flow matching

Ngày 06/11/2026. Hoàn tất S và phép đối chiếu S2 trên 13 ổ XJTU với ba seed. S2 được thiết kế sau S nên cả hai là thăm dò trên dữ liệu đã xem.

## Số lượng train có bằng nhau không?

**Không.** U trước đây có 130 mẫu thật ở baseline và 130 mẫu thật cộng 190–192 mẫu sinh ở nhánh augmentation. T trước đây có 125 mẫu thật ở baseline và 125 mẫu thật cộng 190–192 mẫu sinh. Mọi mẫu thật đều được giữ lại.

Trước đây, mẫu thật chiếm 75% tổng trọng số lớp lỗi, mẫu sinh chiếm 25%. Trong S và S2, giữ nguyên toàn bộ 125 mẫu thật và trọng số từng mẫu, rồi thêm 60, 120 hoặc 240 mẫu sinh. Mỗi mẫu sinh có trọng số bằng 0,25 hoặc 1 lần một cửa sổ lỗi thật cùng ổ nguồn. Mọi phương pháp dùng cùng tập test và RF.

Như vậy thử nghiệm mới thực hiện trực tiếp đề xuất giữ real rồi thêm gen. Số lượng được khớp giữa các bộ sinh, không ép nhánh real-only phải có cùng số dòng với real+gen.

## Bảng tại liều đặt trước

125 mẫu thật cộng 120 mẫu sinh, alpha bằng 0,25. Baseline chỉ có 125 mẫu thật. Chấm selective gồm cả lớp khỏe, không thêm ngưỡng score. Đơn vị là macro recall phần trăm; chỉ số này chưa đo hiệu quả bảo trì.

| Cấu hình | Trước đoạn cuối | Đoạn cuối | Vòng cách cuối | Gán lỗi trên healthy giả định |
|---|---:|---:|---:|---:|
| Chỉ mẫu thật | 58.75% | 68.33% | 11.67% | 0.00% |
| Thêm bản sao | 68.06% | 72.64% | 31.67% | 0.00% |
| Thêm surrogate cũ | 64.17% | 74.26% | 31.67% | 0.00% |
| Thêm surrogate giữ đường bao | 65.46% | 74.07% | 36.67% | 0.00% |
| Thêm trộn nền | 69.91% | 77.22% | 48.33% | 1.03% |
| PCA32 dựng lại mẫu thật | 58.43% | 62.96% | 0.00% | 0.00% |
| Flow matching, PCA32 | 53.70% | 61.06% | 3.33% | 0.00% |
| Diffusion, PCA32 | 53.56% | 63.15% | 0.00% | 0.00% |
| PCA đủ hạng dựng lại mẫu thật | 69.91% | 75.79% | 40.00% | 0.00% |
| Flow matching, PCA đủ hạng | 59.68% | 64.81% | 0.00% | 0.00% |
| Diffusion, PCA đủ hạng | 59.86% | 66.30% | 0.00% | 0.00% |

## Vì sao phải có đối chứng bản sao?

Thêm faultwindows làm tổng trọng số fault tăng so vớihealthy dù weightmỗi dòng thật giữ nguyên. Chỉ sao chép cũng có thể cải thiện classifier do đổi phân bố trọng số. Phần vượt duplicate mới là bằng chứng liên quan hơn tới giá trị biến thể mới; vẫn phải xét CI và kết quả trên ổ chưa dùng phát triển.

## Khoảng bất định tại liều đặt trước

| Phương pháp | So mẫu thật | So bản sao cùng liều | So surrogate cùng liều |
|---|---|---|---|
| Thêm surrogate cũ | +5.93 điểm, CI thăm dò [-3.70; +15.56] | +1.62 điểm, CI thăm dò [-0.97; +5.69] | +0.00 điểm, CI thăm dò [+0.00; +0.00] |
| Thêm trộn nền | +8.89 điểm, CI thăm dò [-8.89; +26.67] | +4.58 điểm, CI thăm dò [-5.79; +14.81] | +2.96 điểm, CI thăm dò [-5.19; +11.11] |
| Flow matching, PCA32 | -7.27 điểm, CI thăm dò [-12.27; -2.22] | -11.57 điểm, CI thăm dò [-22.50; -0.65] | -13.19 điểm, CI thăm dò [-25.97; +0.00] |
| Diffusion, PCA32 | -5.19 điểm, CI thăm dò [-10.37; +0.00] | -9.49 điểm, CI thăm dò [-21.11; +2.22] | -11.11 điểm, CI thăm dò [-23.89; +1.67] |
| Flow matching, PCA đủ hạng | -3.52 điểm, CI thăm dò [-10.74; +3.70] | -7.82 điểm, CI thăm dò [-21.11; +5.46] | -9.44 điểm, CI thăm dò [-20.74; +1.85] |
| Diffusion, PCA đủ hạng | -2.04 điểm, CI thăm dò [-7.78; +3.70] | -6.34 điểm, CI thăm dò [-19.49; +6.81] | -7.96 điểm, CI thăm dò [-20.37; +4.44] |

Bootstrap theo ổ với5000resamples, seed trung bình trong từng ổ trước khi tính; chỉ mang tính thăm dò. Có3inner,8outer,2cage; các tập train chồng lấn nên không coi CI này là xác nhận độc lập.

## Đã thử loại flow và diffusion nào?

CFM có điều kiện loại lỗi, tốc độ và logRMShealthy nguồn; đường thẳng từGaussian noise tới latent, học velocity,50Eulersteps. DDPM cùngcondition, cosine100steps, họcnoise và posterior sampling100steps. CùngMLP128ba tầng ẩn, Adam1e-3,batch32,1500updates. Không dùng testfault để huấn luyện codec hoặc network.

S dùng32PC cộnglogRMS. S2 giữ119PC cộnglogRMS để tái dựng trainwaveform gần như đầy đủ trước giới hạn cảm biến. PCAfit trên120waveforms từ12donors, không gồm ổ test. Mẫu sinh được dựng thành waveform4000điểm rồi tính lại45features choRF, không chỉ sinh trực tiếp feature.

| Codec | Phương sai giải thích trung bình | Sai số waveform L2 tương đối trung bình |
|---|---:|---:|
| PCA32 | 45.66% | 0.728100 |
| PCA đủ hạng | 100.00% | 4.860e-15 |

Tái dựng tốt dữ liệu train không đảm bảo sinh được lỗi cơ khí đúng hoặc tổng quát sang ổ khác. Hai prototype này chưa phải U-Net học trực tiếp waveform hoặc mô hình được tiền huấn luyện trên nguồn dữ liệu lớn. Kết quả không đủ kết luận cho toàn bộ họ diffusion hoặc flow matching.

Đối chứng PCA đủ hạng vẫn đi qua giới hạn 8g và lượng tử hóa sau tái dựng. Cửa sổ thật đã trừ trung bình có thể vượt 8g dù tín hiệu trước đó đã qua cảm biến, nên giới hạn lần nữa có thể đổi dữ liệu. Không quy lợi ích của đối chứng này cho việc học thêm cơ chế lỗi.

Audit sau giới hạn cảm biến: sai số L2 tương đối trung bình của PCA đủ hạng là 0.006314, sai lệch biên độ lớn nhất 0.5467g. Đây là tác động sau decode, tách biệt với sai số PCA trước giới hạn.

## Toàn bộ độ nhạy số lượng và trọng số S2

| Policy | Phương pháp | Ratio | Alpha | Recall trước cuối | Recall cuối | Vòng cách cuối | Gán lỗi healthy |
|---|---|---:|---:|---:|---:|---:|---:|
| selective | PCA đủ hạng dựng lại mẫu thật | 0.5 | 0.25 | 67.27% | 71.30% | 21.67% | 0.00% |
| selective | PCA đủ hạng dựng lại mẫu thật | 0.5 | 1 | 69.91% | 74.44% | 36.67% | 0.00% |
| selective | PCA đủ hạng dựng lại mẫu thật | 1 | 0.25 | 69.91% | 75.79% | 40.00% | 0.00% |
| selective | PCA đủ hạng dựng lại mẫu thật | 1 | 1 | 63.52% | 72.22% | 36.67% | 0.00% |
| selective | PCA đủ hạng dựng lại mẫu thật | 2 | 0.25 | 69.17% | 75.93% | 46.67% | 0.00% |
| selective | PCA đủ hạng dựng lại mẫu thật | 2 | 1 | 64.44% | 72.78% | 38.33% | 0.51% |
| selective | Flow matching, PCA đủ hạng | 0.5 | 0.25 | 59.31% | 63.43% | 0.00% | 0.00% |
| selective | Flow matching, PCA đủ hạng | 0.5 | 1 | 65.97% | 71.30% | 15.00% | 0.00% |
| selective | Flow matching, PCA đủ hạng | 1 | 0.25 | 59.68% | 64.81% | 0.00% | 0.00% |
| selective | Flow matching, PCA đủ hạng | 1 | 1 | 59.40% | 63.80% | 0.00% | 0.00% |
| selective | Flow matching, PCA đủ hạng | 2 | 0.25 | 62.64% | 66.02% | 0.00% | 0.00% |
| selective | Flow matching, PCA đủ hạng | 2 | 1 | 57.13% | 64.58% | 0.00% | 0.00% |
| selective | Diffusion, PCA đủ hạng | 0.5 | 0.25 | 62.27% | 71.11% | 16.67% | 0.00% |
| selective | Diffusion, PCA đủ hạng | 0.5 | 1 | 62.64% | 70.00% | 16.67% | 0.00% |
| selective | Diffusion, PCA đủ hạng | 1 | 0.25 | 59.86% | 66.30% | 0.00% | 0.00% |
| selective | Diffusion, PCA đủ hạng | 1 | 1 | 60.88% | 65.93% | 0.00% | 0.00% |
| selective | Diffusion, PCA đủ hạng | 2 | 0.25 | 62.13% | 73.33% | 23.33% | 0.00% |
| selective | Diffusion, PCA đủ hạng | 2 | 1 | 61.02% | 66.34% | 1.67% | 0.00% |
| conditional | PCA đủ hạng dựng lại mẫu thật | 0.5 | 0.25 | 74.07% | 76.30% | 36.67% | 100.00% |
| conditional | PCA đủ hạng dựng lại mẫu thật | 0.5 | 1 | 75.74% | 77.78% | 46.67% | 99.49% |
| conditional | PCA đủ hạng dựng lại mẫu thật | 1 | 0.25 | 76.02% | 78.01% | 46.67% | 100.00% |
| conditional | PCA đủ hạng dựng lại mẫu thật | 1 | 1 | 70.74% | 76.11% | 48.33% | 100.00% |
| conditional | PCA đủ hạng dựng lại mẫu thật | 2 | 0.25 | 73.89% | 75.93% | 46.67% | 100.00% |
| conditional | PCA đủ hạng dựng lại mẫu thật | 2 | 1 | 69.44% | 75.56% | 46.67% | 100.00% |
| conditional | Flow matching, PCA đủ hạng | 0.5 | 0.25 | 67.78% | 68.98% | 16.67% | 100.00% |
| conditional | Flow matching, PCA đủ hạng | 0.5 | 1 | 70.14% | 71.30% | 15.00% | 100.00% |
| conditional | Flow matching, PCA đủ hạng | 1 | 0.25 | 69.54% | 72.59% | 23.33% | 97.95% |
| conditional | Flow matching, PCA đủ hạng | 1 | 1 | 61.62% | 63.80% | 0.00% | 100.00% |
| conditional | Flow matching, PCA đủ hạng | 2 | 0.25 | 68.47% | 71.57% | 16.67% | 100.00% |
| conditional | Flow matching, PCA đủ hạng | 2 | 1 | 59.63% | 64.58% | 0.00% | 100.00% |
| conditional | Diffusion, PCA đủ hạng | 0.5 | 0.25 | 73.10% | 77.78% | 36.67% | 99.49% |
| conditional | Diffusion, PCA đủ hạng | 0.5 | 1 | 69.44% | 71.11% | 20.00% | 99.49% |
| conditional | Diffusion, PCA đủ hạng | 1 | 0.25 | 72.22% | 71.85% | 16.67% | 100.00% |
| conditional | Diffusion, PCA đủ hạng | 1 | 1 | 67.69% | 70.93% | 15.00% | 100.00% |
| conditional | Diffusion, PCA đủ hạng | 2 | 0.25 | 68.38% | 77.78% | 36.67% | 98.97% |
| conditional | Diffusion, PCA đủ hạng | 2 | 1 | 69.49% | 70.79% | 15.00% | 100.00% |

Các dose S và mọi kết quả gốc: [báo cáo S](REAL_CONG_SYNTHETIC_FLOW_DIFFUSION_20261106.md). Không chọn max trong bảng sensitivity để thay primary đã chốt.

## Kết luận phù hợp với bằng chứng

Cần giữ mẫu thật và kiểm chứng phần thêm vào; không cần synthetic tái hiện100% waveform thật. Nhưng nhãn lỗi của mẫu sinh cần được hỗ trợ bằng cơ chế tín hiệu, kiểm tra ngoài sự kiện train và lợi ích chẩn đoán thực tế.

Cảhai điều kiện số lượng và trọng số đã được kiểm tra. Chưa có generator được chứng minh tốt nhất cho nhà máy. Lớp cage khi giữ một ổ đểtest chỉ còn một ổnguồn; mẫu sinh không tạo thêm sự kiện cơ khí độc lập. Healthyđầu đời chỉ làgiảđịnh; cảm biến8g vàbăngthông1kHz chưa đượcxácnhậnchoDENSO.

Lưu modelcheckpoint, waveform, generatedfeatures, per-foldscores, sourcehash vàprotocol. S có78modeldeep và1677classifierfits; S2 thêm78modeldeep và702classifierfits. Đơn vị đánhgiá vẫn13ổ. Không thay runtimeMVP.

## Tài liệu và tái lập

- [Protocol S](PROTOCOL_S_GENERATION.md).
- [Protocol S2](PROTOCOL_S2_FULLRANK.md).
- [Flow Matching for Generative Modeling](https://arxiv.org/abs/2210.02747).
- [Denoising Diffusion Probabilistic Models](https://arxiv.org/abs/2006.11239).
- [Kết quả S2 đầy đủ](results/s2/fullrank.json).

```powershell
python s2_fullrank.py
python s2_report.py
python -m pytest -q
```
