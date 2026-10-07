# Biên bản tự phản biện phương pháp DENSO

**Ngày:** 06/10/2026. **Loại review:** tự rà soát lập luận và nguồn bằng công cụ, **không review của chuyên gia độc lập**. **Trạng thái:** hoàn tất bản phương pháp/roadmap có điều kiện; chưa làm benchmark ML hoặc pilot.

**Bổ sung thực nghiệm:** đã chạy benchmark sinh waveform CWRU và GAN/DDPM prototypes, không detector/pilot. Bộ sinh duy nhất chọn sau yêu cầu generation-first: bounded-phase constrained surrogate. Sản xuất 30.000 mẫu từ 30.015 attempts; scale/stress/unit tests có artifacts trong `C:\Users\Ad\Downloads\DENSO\generator_benchmark`. Review trước bên dưới là historical; quyết định mới và limits ở `C:\Users\Ad\Downloads\DENSO\docs\results\KET_QUA_THU_NGHIEM_SINH_DU_LIEU_A2.md`.

## 1. Hồ sơ và phạm vi

- Kế hoạch: `C:\Users\Ad\Downloads\DENSO\docs\plans\KE_HOACH_NGHIEN_CUU_DENSO.md`.
- Hồ sơ PDF và extracted text: `C:\Users\Ad\Downloads\DENSO\inputs\a2\A2.pdf`, `C:\Users\Ad\Downloads\DENSO\inputs\a2\A2_extracted.txt`.
- Evidence yêu cầu website: `C:\Users\Ad\Downloads\DENSO\research_evidence\official_snapshots\DENSO_website_evidence.txt`, `C:\Users\Ad\Downloads\DENSO\research_evidence\official_snapshots\DENSO_scoring_evidence.txt`.
- Nghiên cứu bổ sung: `C:\Users\Ad\Downloads\DENSO\docs\research\NGHIEN_CUU_CONG_BO_DENSO_VA_PHUONG_AN.md`.
- Snapshot web: `C:\Users\Ad\Downloads\DENSO\research_evidence`; sources manifest và audit inventory trong cùng thư mục.

Thông tin PDF 10 trang/hình trang 3 và 6 trong bản trước được giữ là **ghi nhận của lượt trước**; lượt bổ sung này đọc text kế hoạch/evidence và truy nguồn, không giả là mở lại mọi hình PDF. Mã giao P/K vẫn chưa có xác nhận mentor.

## 2. Lịch phản biện và quyết định chốt

| Phần | Vấn đề | Quyết định |
|---|---|---|
| 1–2 | PDF thứ cấp và mâu thuẫn A1/A2; nguồn snippets yếu | Yêu cầu mentor xác nhận; phân biệt facts/hypotheses, không sửa mã đăng ký tự động |
| 3 | H1–H5 và nhiều bộ phận quá rộng | H1 augmentation trước; H2–H5 và đai/rail/deep điều kiện, không deadline promises |
| 4 | Amplitude/modulation/transfer có thể bù nhau, fit không định danh | Một resonance, bounds/prior, normalized distances, sensitivity/multi-start, joint parameter sampling, pre-roll/crop; fit/check không là external test |
| 5 | Rank/fusion learning dùng chung calibration làm score không cố định | Train/dev-rank-fusion/final-cal/test phân vai; conformity giả thiết exchangeability ghi rõ; A endpoint chính, C/fusion không tùy biến theo generator/test |
| 6 | Shots/group/license không được kiểm kê | PU subpages xác nhận counts/settings/repeats; raw/fact sheets còn thiếu, NC permission và six-healthy-group limitation rõ |
| 7 | Rejection nâng recall/FPR giả; threshold chọn test | Raw denominator ledger; accepted/end-to-end/coverage/quality-workload; nominal cal FPR khác actual test FPR; không point adjustment |
| 8 | “Import được” bị hiểu thành pipeline chạy | Import/versions/CUDA kiểm tra riêng; stage artifacts/test trước UI, không clone repo/cài thêm vô cớ |
| 9 | OEE literature bị quy thành ROI; IoT giả định bị gọi kiến trúc DENSO | Đọc F-IoT paper thực; loose-coupled/read-only đề xuất, access chưa cấp; shadow/ticket/outcome và exposure |
| 10 | Tacit reasoning không thể tự biết; case leakage, unsafe citations | Expert-confirmed reasons, incident split, ACL/citation gate, abstention và utility người dùng; K tách khỏi P |
| 11 | Slides số đẹp/lịch cứng không có evidence | Evidence thật/giả thuyết tách rõ, deadline/requirements riêng cần xác nhận |
| 12 | Novelty chưa đọc R2; public paper/code/license lẫn nhau | R2 chỉ metadata; OpenAlex closed và Elsevier request lỗi; không claim novelty. Repository/license riêng cho từng nguồn |
| 13 | Cùng volume chưa đủ fairness; chọn winner test | Real group mass và class weighting chốt; accepted synthetic/background/tune/objective/compute budget; endpoint và stopping rule đăng ký trước |
| 14 | Thiếu quyết định cuối sau phản biện | Thêm conclusion, comparative directions và G0–G5 staged implementation, không hứa efficacy |

## 3. Evidence đã xác minh trong lượt bổ sung

### 3.1. Nguồn DENSO

- Patent **US10767725B2**: toàn văn description/claims/assignee hiển thị đã đọc; hardware amplitude-modulating vibrator, không software anchored simulator. Public disclosure **không** permission reuse/FTO.
- **Ishibashi, F-IoT, DENSO Technical Review Vol.27 2022**: PDF text qua Reader; data platform/app/OSS/ORiN/security và human improvement activities; OEE không magic wand. Không original repo public đã xác minh.
- **Yoshida/Yamamoto/Kanke, battery capacity anomaly, Vol.25 2020**: PDF text qua Reader; Graphical Lasso relation-change, telemetry battery; không healthy-only no-fault-tuning proof và không bearing deployment.
- DENSO WAVE IoT trang trực tiếp: lineup/ORiN/information interfaces; không xác nhận simulator/model/API permission.
- D-tote JP 2022 và manufacturing EN series 2023/DX 2025: text đã đọc; collection/capture/operations implications, không downstream fault accuracy.
- Technical archive: 38 linked issue/volume pages query; 34 saved volume snapshots; 4 HTTP429. Chỉ title-level screening phần lớn, không claim đã đọc toàn bộ lịch sử PDF.
- Equipment diagnosis 1999: title/index và PDF metadata 6 trang, **không body extraction**; chưa dùng làm evidence phương pháp.

Corporate direct 403 đã được thay bằng đọc public text qua bên thứ ba Jina. Phải đối chiếu PDF gốc/hình khi dùng quantitative claims; không suy extraction là authoritative legal document.

### 3.2. Paper/dataset/code

- R1 full text đọc lại: 3D simulation + measured healthy background; 18k/6k simulated train/val images; real additional bearing results có failure cases, measured-training comparator tốt hơn trong phạm vi outer ring. Không bằng chứng anchored procedure mới; data on request.
- R3 full text đọc lại: PRONOSTIA RtF partition có healthy prefix đích tùy γ, fault definition heuristic, transfer minor success; code model gốc chưa xác minh.
- R2 Crossref/OpenAlex đã query lại: metadata/closed OA, full text chưa đọc. Elsevier endpoint 400 không chứng minh paper không có full text ở nơi khác.
- PU download/conditions/damage pages: 6 healthy/12 artificial/14 accelerated lifetime damage, 20×4s×4 conditions; CC BY-NC4.0. Physical IDs lớp cụ thể và raw hashes chưa có.
- HUST Mendeley direct: shell/footer, không license raw đủ; không nâng thành xác minh quyền.
- Repo SciPy/scikit-learn/PyOD/TS2Vec/DeepSVDD/TimeEval/TSB-AD/TimeGAN/ALCE/GraphRAG mở đúng và license đọc được như bảng báo cáo. Chưa clone hoặc chạy original code. Một số URL đoán sai 404 bị loại, không tái dùng.

## 4. Kết quả công cụ: phân biệt đã thấy, không thấy và không thành công

### 4.1. Đã chạy trực tiếp

Python **3.12.10**, NumPy **2.4.4**, SciPy **1.17.1**, scikit-learn **1.8.0**, PyTorch **2.7.1+cu118** import thành công. `torch.cuda.is_available()` trả **True**, CUDA build **11.8**. Không suy GPU throughput/VRAM/tái lập repo từ availability.

Smoke môi trường đã thực thi trên dữ liệu **toy**: Hilbert envelope có peak modulation 40 Hz đúng thiết kế, RF `predict_proba` hữu hạn, LedoitWolf covariance distance hữu hạn, tensor PyTorch bình phương/cộng cho 5 trên `cuda:0`. Lưu `C:\Users\Ad\Downloads\DENSO\research_evidence\environment_smoke.json`. Không phải code benchmark/generator, không dùng làm accuracy/utility của đề xuất. Đã kiểm tra UTF-8, code fences Markdown, existence và hash snapshot bằng Python; báo cáo cấu trúc ở `document_validation.json`, không thay review khoa học.

Workspace không Git repository; lệnh liệt kê + `git status` trả exit1 do Git, nhưng listing hiện có. Không tạo Git/cài dependencies trong task tài liệu này.

Snapshot downloader lần đầu thành công với các file đã hiện. Một lượt downloader bổ sung bị PowerShell làm hỏng Unicode regex nên command exit1 sau khi lưu các file/manifest. Đã **kiểm tra lại existence và SHA-256 từng entry manifest**, 9 entry đầu đều khớp; không dựa command thất bại để khẳng định phần sau chạy. Sau đó dùng Unicode escapes cho search.

### 4.2. Không có evidence dùng được

- Google redirect, DuckDuckGo CAPTCHA, Yahoo500, Bing irrelevant results: query log ở báo cáo, **không** kết luận “không tồn tại tài liệu”.
- Corporate403, một URL technical cũ page-not-found, một số GitHub404: lỗi truy cập/URL, không technical result.
- Technical archive429: chưa đọc bốn issues cuối; không lặp request áp đảo khi đã rate-limit.
- R2 endpoint400 và không OA location: không toàn văn. Equipment1999 Reader có metadata nhưng body trống: chỉ index evidence.
- Output trống ở lịch sử trước summary: không phục hồi được phiên bản/library/CUDA từ đó; dùng kiểm tra trực tiếp mới thay vì khẳng định lượt cũ đã xác minh.

## 5. Những gì là đề xuất, chưa phải facts/results

- DENSO sẽ cấp rung/RPM/geometry, vài anchors, healthy dài, incidents/labels hoặc platform/API access.
- Anchoring giảm domain gap, P4 tốt hơn P3, A+C tốt hơn C, unknown recall hữu ích.
- 5 điểm phần trăm recall improvement đủ giá trị, alarm budget/ca, chi phí maintenance và roadmap ngày công.
- Simulator cộng tuyến tính phù hợp sensor/transfer thực; θ uncertainty có ý nghĩa xác suất.
- Code repo mở chạy trên Python3.12/NumPy2.4; các dependency legacy có thể không tương thích.

Những điểm này có gates/contract và validation requirements trong kế hoạch; không mô tả như đã đạt.

## 6. Acceptance checklist cho tài liệu chốt

- [x] Calibration score-learning tách final threshold set; serial exchangeability limitations rõ.
- [x] Fairness anchors/real weight/background/volume/search/training compute rõ.
- [x] Quality/OOD rejection có coverage/end-to-end và workload, không biến mất khỏi denominator.
- [x] Primary endpoint, locked test, paired groups và stopping rule rõ.
- [x] DENSO prior art so với novelty hiện tại; paper/code/license distinctions.
- [x] Comparative baseline-first recommendation và conditional extensions.
- [x] Đường dẫn review record có tệp thực, không chỉ reference chưa tạo.
- [ ] Mentor xác nhận P/K và private requirements.
- [ ] Raw download/fact sheets/group manifest/permission.
- [ ] Original repo reproduction và benchmark utility.
- [ ] R2 toàn văn/novelty technical comparison.
- [ ] Đủ healthy exposure, field incidents và shadow review để claim khả dụng DENSO.

**Kết luận reviewer:** có thể chuyển sang implementation theo G0–G5. Chưa thể tuyên bố chọn phương pháp tốt nhất bằng accuracy, triển khai thành công, novelty học thuật hoặc ROI. Kết quả âm của augmentation là một kết quả hợp lệ; không cần thêm diffusion để cứu ý tưởng.
