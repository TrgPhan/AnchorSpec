# S2: kiểm tra diffusion và flow khi bỏ mất mát PCA, 06/11/2026

Chốt sau khi xem S, trước chạy S2. S cho thấy PCA32 mất nhiều phương sai và
reconstructionbootstrap kém real; không đủ cơ sở đổ lỗi hoàn toàn cho generator.
S2 giữ nguyên mô hình, optimizer,1500steps, condition, sourcefold và mọi dose S.
Chỉ đổi PCA từ32 sang119components, là rank tối đa của120waveforms source
sau centering. Thêm1logRMS, latent120chiều. Phải đạt train-reconstructionL2
nhỏ hơn1e-6 trước giới hạn sensor. Đây không phải đảm bảo generalization;
không gian tuyến tính vẫn chỉ học từ12donors và rất dễ overfit.

Hai networks fit riêng đủ1500steps mỗi outer13*3seed. Sinh20mẫu mỗi donor,
decode trainbounds và sensor như S. Chạy flow_full, diffusion_full,
pca_full_bootstrap ở toàn bộ ratio.5/1/2,alpha.25/1. Tổng702classifierfits.
Mẫu thật, surrogate, duplicate và các mẫu sinh cũ lấy nguyên kết quả S làm
đối chứng; không tái chọn hay đổi primaryS. LượtS2 primaryflow_full ratio1
alpha.25, selective0; báo cảDDPM, PCAfull và mọi dose như sensitivity.

Không sửa sourcefrozenS. Freezehash S inputmanifest, additive.json, S2code,
protocol. Rawtargetfault không vào generator/codec/scaler; các cách chấm và
nhãnhealthy giả định giữ nguyên. Cả S và S2 đều là thăm dò trên dataset đã xem,
không phải78validationđộc lập hoặc nghiên cứu đủ để nói model nào tốt nhất.
