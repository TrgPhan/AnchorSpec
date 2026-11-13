# So sánh 4 cách (hậu nghiệm, 12/11): cùng lượt, 8 seed, chỉ chọn loại lỗi

## Paderborn (vòng trong/ngoài, 11 ổ)

| Cách | 1 sự cố/loại | 2 sự cố/loại | 4 sự cố/loại |
|---|---:|---:|---:|
| Chỉ dữ liệu gốc | 44.8 | 45.7 | 61.0 |
| Gốc + Flow | 45.6 (+0.8 [-1.5; +3.4]) | 45.1 (-0.6 [-1.9; +0.3]) | 61.9 (+0.9 [-0.7; +3.0]) |
| Chỉ cấy lỗi neo (0 sự cố) | 73.4 (+28.7 [+12.2; +45.6]) | 73.4 (+27.7 [+5.0; +50.7]) | 73.4 (+12.4 [-18.1; +43.6]) |
| Gốc + cấy lỗi neo | 65.8 (+21.0 [+6.6; +36.3]) | 61.4 (+15.7 [+4.6; +28.1]) | 76.3 (+15.3 [+1.4; +32.9]) |
| Gốc + cấy lỗi neo + Flow | 65.3 (+20.6 [+6.5; +35.8]) | 61.8 (+16.1 [+4.2; +30.6]) | 75.9 (+14.9 [+1.0; +32.7]) |

**Mốc chung:** điểm cao nhất của chỉ dữ liệu gốc = 61.0% (4 sự cố/loại). Số sự cố thật ít nhất (trong các mức đã đo) để đạt mốc:

- Chỉ dữ liệu gốc: 4
- Gốc + Flow: 4
- Chỉ cấy lỗi neo (0 sự cố): 0 (đạt)
- Gốc + cấy lỗi neo: 1
- Gốc + cấy lỗi neo + Flow: 1

## HUST (trong/ngoài/bi, 14 ổ)

| Cách | 1 sự cố/loại | 2 sự cố/loại | 3 sự cố/loại |
|---|---:|---:|---:|
| Chỉ dữ liệu gốc | 55.9 | 57.5 | 56.0 |
| Gốc + Flow | 51.4 (-4.5 [-8.7; -1.0]) | 56.6 (-1.0 [-2.7; +0.8]) | 56.2 (+0.2 [-1.1; +1.4]) |
| Chỉ cấy lỗi neo (0 sự cố) | 56.1 (+0.3 [-10.8; +11.4]) | 56.1 (-1.4 [-13.1; +10.8]) | 56.1 (+0.2 [-11.8; +12.7]) |
| Gốc + cấy lỗi neo | 62.2 (+6.3 [+1.8; +11.1]) | 64.6 (+7.0 [+2.2; +12.2]) | 65.9 (+10.0 [+3.7; +17.4]) |
| Gốc + cấy lỗi neo + Flow | 62.3 (+6.4 [+2.2; +10.8]) | 63.9 (+6.4 [+1.5; +11.6]) | 65.9 (+9.9 [+3.6; +17.8]) |

**Mốc chung:** điểm cao nhất của chỉ dữ liệu gốc = 57.5% (2 sự cố/loại; đường này gần như phẳng: 55.9 / 57.5 / 56.0). Số sự cố thật ít nhất để đạt mốc:

- Chỉ dữ liệu gốc: 2
- Gốc + Flow: không đạt trong các mức đã đo (cao nhất 56.6)
- Chỉ cấy lỗi neo (0 sự cố): không đạt (56.1)
- Gốc + cấy lỗi neo: 1
- Gốc + cấy lỗi neo + Flow: 1

Ô: macro % (chênh so với chỉ dữ liệu gốc, CI 95% bootstrap theo ổ). "Chỉ cấy lỗi" không dùng sự cố thật nên giống nhau ở mọi cột, khác nhau chỉ do bootstrap ghép cặp.