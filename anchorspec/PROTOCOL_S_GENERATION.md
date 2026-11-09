# S: giữ nguyên mẫu thật, bổ sung mẫu sinh, 06/11/2026

Chốt trước khi chạy S. Tiếp tục trên XJTU đã xem trong U/T nên đây là thăm dò,
không gọi là xác nhận ngoài tập phát triển. Không sửa các source frozen cũ.

## Câu hỏi và thiết kế

T trước đó đã giữ tất cả125mẫu thật: healthy target1–5 và120fault snapshots
từ12donor. Augmentation cũ giảm trọng số fault thật còn75%, dành25% cho synthetic
trong cùng tổng trọng số lớp. S giữ nguyên125dòng thật VÀ từng sample weight,
sau đó thêm synthetic với weight mỗi mẫu bằng alpha nhân weight mẫu thật
cùng donor. Alpha .25 hoặc1; số synthetic trên mỗi donor là5,10,20, tương ứng
ratio .5,1,2 so với10faultwindows. Tổng train185,245,365; baseline125.
Healthy weights giữ nguyên. Vì thế tỉ lệ tổng trọng số healthy/fault thay đổi;
duplicate là đối chứng thiết yếu cho thay đổi prior, không yêu cầu dự đoán
duplicate giống real như ở các phép thử cố định phân bố trước đó.

13outerbearings, seeds11,29,47, RF invariant như T. Singleaxis4kHz1kHz8g,
raw45features. Healthy6–10 chỉ test; preterminal10 vàterminal10 giữ nguyênT.
Primary là selective0, argmax cảhealthy; báo thêm conditional để hiểu sự khác
biệt endpoint, không chọn policy tốt nhất sau khi xem. Seed trung bình theo ổ
trước macro theo lớp, bootstrappaired5000 là CIthăm dò, không bằng chứng độc lập.

## Các nhánh

Real; real+duplicate; real+surrogate; real+envelope; real+severity;
real+PCA reconstruction bootstrap; real+conditional flow matching;
real+conditional latent DDPM. Mọi augmentation cùng số samples và alpha.
Primary prototype CFM tại ratio1 alpha.25, so real, duplicate, surrogate;
DDPM và mọi dose khác là kết quả phụ, giữ đầy đủ không chọn best test.

## Prototype học sâu và codec

Đây là hai prototype kỹ thuật, không tái lập toàn bộ một paper hoặc kết luận
flow/diffusion không tốt nếu prototype chưa tốt. Nén waveform4000điểm thành
32PC và1logRMS: demean, chiaRMS, PCAtrainonly, StandardScalertrainonly.
Codec chung cho cảhai model. PCAbootstrap kiểm tra riêng tác động nén waveform.
Nén có thể làm mất xung; phải báo explainedvariance và reconstructionerror.

Điều kiện gồm nhãn ba loại lỗi, tốcđộdonor vàlogRMShealthy donorfirst5;
không điều kiện hóa bằng lỗi target. Sampling dùng điều kiện từng donor,
không tự nhận là sinh cơ chế lỗi hoặc regime chưa quan sát. Class/donor balanced
sampling. CùngMLP128x3, Adam1e-3, batch32,1500steps, CPU1threadperworker;
không chọn checkpoint theo test. FM đường thẳngnoise-to-data, targetvelocity
data-noise,50Eulersteps; không gọi là OT-CFM. DDPM100cosine steps,epsilonMSE,
posteriorDDPMsampling100steps. Cùngtrain-dependent latentbounds khi decode,
giới hạnlogRMS vào trainrange; output CheapSensor8g. Ghi tỉ lệclamp/clip.

Mỗi donor sinh20waveforms cho mỗi model; các dose lấy prefix5,10,20. Duplicate
và PCAbootstrap dùng hai permutation của10windowthật, ratio1 giữ đủ10mẫu.
Không lọc mẫu theo lỗi test hoặc điểmclassifier. Lưu features, waveform mới,
modelcheckpoints, số bước vàloss; không dùng synthetic làm chứng cứ nhãn đúng.

## Liêm chính dữ liệu và báo cáo

Generator, PCA, scaler chỉ fit12donors, không chạm targetfault để học.
Đối chiếu RFreal với T raw scores; sốlượng, weights và donorlineage ghi theofold.
Lưu hash source, cachedinputs và protocol trước/sau. Không thay modelMVP.
Không dùng loss thấp hoặc waveform giống làm kết luận clinical/industrialvalidity.
Chỉ khi real+gen vượt cùngreal+duplicate vàreal+surrogate trên testgiữtheoổ,
không tănghealthyfalse hoặc giảmrecalllớp quantrọng, mới có lý do nghiêncứutiếp.

Nguồn: [Flow Matching](https://arxiv.org/abs/2210.02747),
[DDPM](https://arxiv.org/abs/2006.11239).
