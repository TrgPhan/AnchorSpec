# W-Hierarchy, sau phân tích W-Amplitude, 04/11/2026

Giả thuyết có mục tiêu: spectral_amplitude cải thiện bi/vòng cách nhưng làm
giảm vòng ngoài. Chọn một kiến trúc cố định theo nhóm vật lý thay vì chọn view
theo điểm outer test. Đây vẫn là phát triển trên dữ liệu đã xem.

Cổng phân nhóm: vòng trong/ngoài là nhóm1; bi/vòng cách là nhóm2, view243
(45gốc+196phổ+2logbiênđộ). Chuyên gia vòng: view45, chỉ inner/outer. Chuyên gia
bi/vòng cách: view243, chỉ ball/cage. Cả ba dùng DiagnosticExperts real-only
Y, giữ nguyên lựa chọn classifier/representation bằng donorCV. Không dùng
physics/surrogate vì chỉ xét có4sự kiện xác nhận mỗi loại.

Ghép mềm: chuẩn hóa điểm trên hai nhãn lỗi ở từng chuyên gia, nhân điểm cổng
nhóm với điểm chuyên gia để được4điểm; trung bình nhân quả5cửa sổ rồi argmax.
Không gọi điểm ghép là xác suất hiệu chỉnh; cờ bất thường vẫn giả định đúng.

20ổ,3seed,4donor mỗi lớp nhưY. Reportmacro, từnglớp,early/late, CItheoổ so
Y gốc và view243. Không thay kiến trúc theo kết quả này và không coi các lần
thử trước là xác nhận độc lập. Không chạy1/2 sự kiện trong đợt này vì mỗi tầng
cần đủ donor để validation các lớp; claim chỉ ởngân sách4.
