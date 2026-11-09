# V: healthy-conditioned measured-fault transport, 04/11/2026

Viết trước khi chạy V. Mục tiêu chính là chứng minh hoặc bác bỏ lợi ích DỮ LIỆU
SINH trên cùng classifier, feature, donor và sensor, không gộp cải tiến mô hình
với cải tiến generator. UORED là development đã xem. Phải giữ kết quả âm.

## Giả thuyết

Surrogate giữ phổ source có thể giữ cả đường truyền và nền máy source. Tạo
waveform mới bằng lọc phổ source fault theo tỷ lệ phổ HEALTHY target/source,
không dùng target fault. PSD Welch1024, làm mượt log PSD theo48Hz, gain giới
hạn0.5 đến2.0, dưới1kHz; gain trên1kHz bằng1. Hiệu chỉnh tốc độ bằng nội suy
tuần hoàn tỷ lệ fr_target/fr_source, chỉ dùng fr từ healthy. Phép lọc này là
giả thuyết thích nghi môi trường, không phải ước lượng đường truyền cơ khí đã
được kiểm chứng. Không gọi là cơ chế lỗi mới hay digital twin chính xác.

Đối chứng: real-only; exact duplicate; constrained surrogate cũ; severity-only
trộn source fault với source healthy; transport; transport_mix trộn waveform
transport với target healthy. Mix dùng sqrt(a) fault + sqrt(1-a) healthy,
a đều0.35 đến1.0. Transport làm dịch vòng ngẫu nhiên, không đổi pha độc lập
như surrogate. Ra qua quantization/range CheapSensor. Ghi tỷ lệ clipping,
không lọc theo target test hoặc theo việc mô hình đoán đúng nhãn.

Transport áp dụng cho cả bốn lớp từ lỗi thật đã xác nhận, không dựa vào công
thức cage/lube/foreign chưa kiểm chứng. Chưa bảo đảm mọi waveform giữ nhãn,
nên phải đo utility và kiểm tra chất lượng riêng. Không sinh nhãn chưa có.

## Đánh giá

20 UORED, seeds11/29/47,1/2/4donor mỗi loại, state2 donor để học/sinh. State1
và2 của target giữ ngoài training. Dùng đúng donorY/W. 64mẫu sinh mỗi lớp,
chia đều donor; exact duplicate dùng nguyên cửa sổ donor, trọng số tương đương.
Class/source/event balanced, cùng tổng trọng số bằng số cửa sổ THẬT, kể cả
healthy. So cả conditional diagnosis và argmax healthy trên hold ngắn;
hold không đại diện báo nhầm theo tháng hoặc end-to-end detection.

Lựa chọn classifier trên real-only: RF50,RBF SVM C1/C10; raw/delta/z. Inner
CV leave-one-donor-bearing-out, healthy của donor held-out đóng vai trò nền
máy đích; mọi target-fault derivatives bị loại khi fold dùng ổ đó validation.
Với1donor/lớp không đủ CV còn đủ lớp, fallback SVM1 raw.

Sau đó KHÓA classifier/representation cho mọi generator. Chỉ chọn synthetic
mass0.25 hoặc0.5 theo cùng donor validation; từng generator có cùng hai lựa
chọn. Tie mass0.25. Nhánh adaptive có quyền chọn real-only, tie ưu tiên real,
duplicate,surrogate,severity,transport,transport_mix. Không dùng outertest.
Mỗi inner validation target có library transport riêng tạo từ training donors
và healthy của validation target, mô phỏng đúng vai trò lúc inference.

Chỉ số: macro theo ổ/lớp, average seed trước; early,late,mean hai trạng thái,
worst class, pairedbootstrap5000. Primary generator transport_mix. Gate cần
tăng trung bình hai trạng thái ít nhất5điểm, không trạng thái giảm quá2điểm,
không lớp giảm quá5điểm, CI dương; và xác nhận nguồn phù hợp khác sau freeze.
Không bootstrap windows thành hàng nghìn thử nghiệm độc lập. CI thăm dò,
không bảo đảm tính độc lập khi các training set chồng nhau.

## Nguồn ý tưởng

[FDA, Yang và Soatto, CVPR2020](https://openaccess.thecvf.com/content_CVPR_2020/html/Yang_FDA_Fourier_Domain_Adaptation_for_Semantic_Segmentation_CVPR_2020_paper.html)
là tham khảo về thích nghi miền phổ cho ảnh; không phải bằng chứng đúng với
rung. V dùng tỷ lệ nền khỏe, khác thay biên độ tần số thấp trongFDA.
[FBSDA, JCDE](https://academic.oup.com/jcde/article/12/1/34/7915075)
là công trình gần hướng fault simulation với normal background; V không tái
hiện mạng hoặc kết quả bài đó. Tên V chỉ tên thí nghiệm, chưa claim novelty.
