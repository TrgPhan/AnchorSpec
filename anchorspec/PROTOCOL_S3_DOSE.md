# S3-Dose: sinh bao nhiêu mẫu cho mỗi loại lỗi khi sự cố thật bị lệch

Ghi ngày 11/11/2026, **trước khi chạy**. Thăm dò trên UORED và XJTU, hai bộ đã dùng nhiều lần; không phải xác nhận độc lập. Không phải dữ liệu DENSO.

## Câu hỏi

1. Khi nhà máy có số sự cố lệch giữa các loại lỗi (ví dụ 5 vòng trong, 2 vòng cách, 1 vòng ngoài), nên sinh bao nhiêu mẫu cho mỗi loại, và tin vào mẫu sinh đến mức nào?
2. Có tỉ lệ chung nào giữa dữ liệu khỏe và dữ liệu lỗi không?
3. Nếu không có quy tắc chung, có chọn được liều chỉ từ sự cố của chính máy (lúc lắp đặt) không?
4. Lựa chọn đó ổn định đến đâu theo seed và hạt giống lấy mẫu?

"Vòng giữa" trong câu hỏi được hiểu là **vòng cách (cage)**. Lớp bi của UORED không dùng, để giữ đúng 3 lớp như câu hỏi.

## Dữ liệu và cách chia

**UORED, 15 ổ:** vòng trong 1–5, vòng ngoài 6–10, vòng cách 16–20. Cảm biến giả lập 1 kHz như `s3_uored.py`.
- Ổ đích: 11 cửa sổ khỏe đầu để học; cửa sổ 12 trở đi của tệp khỏe để kiểm tra khỏe; trạng thái lỗi nặng (19 cửa sổ) để kiểm tra chính; trạng thái đang phát triển để báo phụ.
- Mỗi sự cố (ổ nguồn) góp 10 cửa sổ lỗi nặng không chồng lấn.

**Bộ sự cố (trong / cách / ngoài):** 5-2-1 (ví dụ của bạn), 1-2-5, 2-2-2, 1-1-1, 4-4-4.
- Ổ nguồn chọn theo hoán vị cố định cho từng (seed, lớp), bỏ ổ đích. Các bộ lồng nhau: 2 sự cố đầu của 5-2-1 chính là 2 sự cố của 2-2-2.
- Khi ổ đích cùng lớp, lớp đó chỉ còn tối đa 4 ổ, nên "5" thực tế là 4. Số thật được ghi lại.
- 15 ổ đích × 3 seed (11, 29, 47) × 5 bộ = 225 lượt.

**XJTU 13 ổ, bộ sự cố tự nhiên:** 3 vòng trong, 8 ngoài, 2 cách, leave-one-bearing-out, 39 lượt. Đặc trưng và tách dữ liệu như S3.

## Bộ sinh

Flow phần dư S3, giữ nguyên cấu hình: 2.000 bước, 16 bước lấy mẫu, mức 0,5. Mạng học **một lần mỗi lượt** từ cửa sổ của các ổ nguồn đã chọn.

Mẫu sinh của lớp c lấy anchor quay vòng trên mọi cửa sổ của các sự cố lớp c, theo một hoán vị cố định. Liều nhỏ là tiền tố của liều lớn, nên các liều lồng nhau. Flow lấy trung bình 3 hạt giống lấy mẫu (offset 20261106, 1, 2).

## Các nhánh (cùng RF `InvariantClassifier`, `causal_average`, `selective(p, 0)`)

Ký hiệu: m_c là tổng trọng số lớp c khi chỉ dùng mẫu thật. Lớp khỏe và mỗi lớp lỗi có cùng m (do `training()` cân bằng).

| Nhánh | Mẫu sinh | Trọng số |
|---|---|---|
| `real` | Không | Mặc định: khỏe và mỗi lớp lỗi cùng trọng số |
| `dup_add_a` | Bản sao mẫu thật | Mỗi lớp lỗi thêm a·m (a = 0,25 hoặc 1). Chỉ là dồn trọng số về lớp lỗi |
| `flow_add_a_N` | N mẫu Flow mỗi lớp | Thêm a·m mỗi lớp (a = 0,25 hoặc 1) |
| `flow_mix_b_N` | N mẫu Flow mỗi lớp | Mẫu thật giữ (1−b)·m, mẫu sinh b·m (b = 0,25 hoặc 0,5). **Tổng trọng số lớp không đổi** |
| `flow_prop` | 10 mẫu mỗi sự cố (cách S3) | Thêm 0,25·m mỗi lớp |
| `uw_real` | Không | Không trọng số: số dòng tự nhiên, lớp nào nhiều sự cố thì nhiều dòng |
| `uw_topup` | Flow bù để mỗi lớp lỗi có bằng số dòng của lớp nhiều nhất | Không trọng số |

N ∈ {10, 30, 90}.

## Chọn liều lúc lắp đặt (nested), chỉ dùng sự cố của máy

- Lần lượt giữ lại từng sự cố của lớp có ít nhất 2 sự cố. Huấn luyện lại Flow và RF trên các sự cố còn lại, rồi đo recall trên sự cố bị giữ lại.
- Mục tiêu: macro recall trên các lớp kiểm tra được.
- Ứng viên (8 nhánh): `real`, `dup_add_0.25`, `flow_add_0.25_{10,30,90}`, `flow_mix_0.5_{10,30,90}`. Dùng một hạt giống lấy mẫu.
- Hòa thì ưu tiên nhánh đứng trước trong danh sách (mẫu thật, liều nhỏ).
- Không lớp nào có 2 sự cố (ví dụ 1-1-1): dùng `real`.
- Lỗi và đoạn khỏe kiểm tra của ổ đích không bao giờ vào bước chọn.

## Chỉ số

**Chỉ số chính:** macro recall 3 lớp lỗi ở trạng thái nặng (theo ổ, trung bình seed và hạt giống lấy mẫu, rồi theo lớp).

**Kèm theo:**
- Recall từng lớp, và recall của **lớp ít sự cố nhất**.
- Tỉ lệ gán lỗi trên đoạn khỏe kiểm tra. Đoạn này cùng tệp với nền nên phép thử yếu.
- Trạng thái đang phát triển.
- Biên độ dao động theo seed và theo hạt giống lấy mẫu.
- CI 95% bootstrap theo ổ, phân tầng theo lớp, 5.000 lần.

## Quy tắc trả lời, khai báo trước

1. **"Có quy tắc liều chung":** một nhánh Flow có macro không thấp hơn nhánh tốt nhất quá 2 điểm ở **mọi** bộ sự cố của UORED và XJTU, không thấp hơn `real` ở bộ nào, và gán lỗi trên khỏe ≤ 5%.
2. **"Mẫu sinh có giá trị riêng":** `flow_mix` hơn `real` (cùng tổng trọng số), hoặc `flow_add_a` hơn `dup_add_a` (cùng khối lượng thêm), với CI không chứa 0, ở ít nhất 2 bộ sự cố.
3. **"Chọn được lúc lắp đặt":** bộ chọn nested không thấp hơn `real` quá 1 điểm ở mọi bộ, và trung bình hơn `real`.

Không chọn nhánh hay bộ sự cố sau khi xem điểm để đổi các câu hỏi trên. Báo mọi nhánh.
