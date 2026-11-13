# V4-DEV: phát triển trên UORED (PLAN_V4.md mục 4.2)

Ghi ngày 12/11/2026, **trước khi chạy** (chỉ đã chạy thử 1 lượt: ổ 12, seed 11, m = 2, để kiểm tra code).

## Nguyên tắc
- Mỗi lỗi đúng một bộ sinh: trong / ngoài chỉ vật lý; bi / vòng cách chỉ Flow (mô hình S3 của Trường), hoặc photocopy ở nhánh đối chứng. `assert_exclusive` kiểm tra trong code.
- Không có F-neo.

## Thiết lập
- UORED, 20 ổ đích, 8 seed (11, 29, 47, 101, 202, 303, 404, 505), m = 1, 2 sự cố mỗi lớp ở ổ khác. Kiểm tra trên cửa sổ lỗi nặng.
- Tầng 2 luôn là bản đã khóa: thật + vật lý trong / ngoài, 25%.

## Nhánh
| Nhánh | Nhóm vòng ở tầng 1 | Bi / cách ở tầng 1 | Trọng số |
|---|---|---|---|
| `hier` | thật | thật | — |
| `copy` | thật | + photocopy, 20 / sự cố | chiếm 25% |
| `flow_within_05`, `flow_within_10`, `flow_class_05`, `flow_class_10` | thật | + Flow theo lớp, 20 / sự cố | chiếm 25% |
| `flow_truong` | thật | + Flow (within, 0,5), 1 mẫu / cửa sổ thật | **cộng thêm** 0,25 (công thức Trường) |
| `copy_add` | thật | + photocopy 1 / cửa sổ | cộng thêm 0,25 |
| `bal_phys` | + vật lý (máy đích) | thật | chiếm 25% |
| `bal_copy` | + vật lý | + photocopy | chiếm 25% |
| `bal_flowgain` | + vật lý | + Flow-gain (học từ lỗi thật, vẽ trên nền máy đích) | chiếm 25% |

Đối chứng của từng nhánh Flow: `flow_*` (chiếm 25%) so với `copy`; `flow_truong` so với `copy_add`; `bal_flowgain` so với `bal_copy`.

## Quy tắc khóa (giá trị trung bình hai mức m)
1. **Bảo vệ:** recall vòng trong ≥ `hier` − 2 điểm, recall vòng ngoài ≥ `hier` − 2 điểm (xét riêng từng lớp), và macro ≥ `hier` − 1.
2. **Có ích:** đạt bảo vệ, không-luật (trung bình bi và vòng cách) > đối chứng của nhánh, và ≥ `hier` + 2.
3. Chọn nhánh có ích có không-luật cao nhất. Nếu một nhánh `flow_*` hoặc `flow_truong` có ích và kém nhánh tốt nhất không quá 1 điểm, chọn nhánh Flow-từ-lỗi cao nhất.
4. Không có nhánh có ích: khóa nhánh Flow-từ-lỗi cao nhất trong số nhánh đạt bảo vệ, ghi là "trung tính". Không nhánh nào đạt bảo vệ: Flow không vào pipeline (`hier`).
5. Ghi kèm nhánh đối chứng tương ứng để kiểm chứng đóng góp riêng của Flow.
