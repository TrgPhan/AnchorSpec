# W-Amplitude, thử sau W-Spectral, 04/11/2026

Giả thuyết: đặc trưng loại bỏ biên độ có thể mất thông tin về mức tăng rung so
với nền cùng máy. Bổ sung log RMS và log peak vào45đặc trưng, hoặc thêm cả
196đặc trưng phổ của W-Spectral. Không đổi đơn vị, cảm biến, nhãn, donor/test.

Ba view: original45, amplitude47, spectral_amplitude243. Chuẩn hóa theo nền khỏe
của từng máy; classifier/inner selection dùng nguyên DiagnosticExperts real-only
Y, bao gồm healthy ởtraining và chọn lỗi có điều kiện ởtest. Raw/delta/z,
RF50/SVM C1/C10, cùng tập lựa chọn mỗi view. Chọn view bằng validation macro
recall donor; tie ưu tiên original, amplitude, spectral_amplitude.

Chỉ ngân sách2 và4 sự kiện mỗi loại vì1 không đủ inner CV còn đủ lớp. Cùng20ổ,
3seed11/29/47. Chạy lại original45 và yêu cầu prediction counts khớpY trước
khi diễn giải điểm view mới. Báo cả các view cố định và view selected, từng lớp,
early/late. Không lựa chọn view dựa vào outertest rồi gọi là thuật toánselected.

Đây là nghiên cứu exploratory sau khi đã xem các kết quả trước. Không gọi
là xác nhận độc lập, không dùng thiếu bôi trơn/dị vật từ datasetkhông có nhãn.
