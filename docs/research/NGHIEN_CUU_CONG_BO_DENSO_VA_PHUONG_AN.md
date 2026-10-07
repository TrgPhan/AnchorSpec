# Công bố DENSO, phản biện lựa chọn phương pháp và mã nguồn hỗ trợ

**Ngày nghiên cứu:** 06/10/2026. **Phạm vi chính:** nhánh P của hồ sơ “Neo và Mở rộng”: thiếu dữ liệu lỗi cho bảo trì; nhánh K chỉ là phương án thay thế nếu đội được giao A2 trên website. **Không có dữ liệu nội bộ DENSO hoặc kết quả benchmark của đội.**

**Cập nhật sau yêu cầu generation-first:** đã có benchmark waveform CWRU, không benchmark detector. Kết quả và quyết định implementation duy nhất ở `C:\Users\Ad\Downloads\DENSO\docs\results\KET_QUA_THU_NGHIEM_SINH_DU_LIEU_A2.md` thay thế khuyến nghị detector-first của bản nghiên cứu dưới đây. Cách gọi A2 theo hồ sơ đội được giữ cho thử nghiệm.

Tài liệu chính: `C:\Users\Ad\Downloads\DENSO\docs\plans\KE_HOACH_NGHIEN_CUU_DENSO.md`. Biên bản: `C:\Users\Ad\Downloads\DENSO\docs\reviews\BIEN_BAN_RASOAT_METHOD_DENSO.md`. Snapshot nguồn: `C:\Users\Ad\Downloads\DENSO\research_evidence`.

## 1. Trả lời ngắn: kế hoạch có khả dụng không, có cách tốt hơn không?

**Có khả dụng như một giả thuyết augmentation hẹp; chưa đủ bằng chứng để chọn anchored simulator làm giải pháp vận hành mặc định.** Cách ít rủi ro hơn là:

> Thu và kiểm soát dữ liệu → đặc trưng vật lý theo điều kiện → detector khỏe + baseline ít nhãn → kiểm tra augmentation đơn giản → simulator vật lý → neo ít mẫu nếu thật sự tăng utility → cảnh báo có xác nhận kỹ sư.

Không đổi từ “diffusion-first” sang “anchoring-first” rồi bỏ bước kiểm tra cần thiết. Độ khó có thể nằm ở sensor/metadata/nhóm độc lập và báo giả hơn là model. Healthy-only không thay thế đủ đầu ra generator/augmented dataset/report của chủ đề P: giữ nghiên cứu augmentation, nhưng cho phép detector vận hành cuối cùng không dùng synthetic nếu thử nghiệm âm.

**Phát hiện DENSO quan trọng nhất:** DENSO đã công bố patent về tạo chữ ký rung cho predictive maintenance; vì vậy “không cần chờ lỗi thật, tạo dữ liệu rung giống lỗi” **không phải claim mới an toàn**. Có thể đóng góp engineering ở cách neo, uncertainty, provenance, đánh giá ít mẫu và alarm budget, nhưng phải đối chiếu R2 trước khi claim novelty học thuật.

## 2. Phạm vi tìm kiếm và giới hạn tính đầy đủ

### 2.1. Các kênh đã query/đọc

- Website cuộc thi `densohackathon.vn`, evidence bundle local có A1/A2.
- Corporate DENSO EN/JP: business, industry, sitemap, DRIVEN BASE; lần đầu direct fetch trả 403. Sau đó đọc bản văn bản của cùng URL chính thức qua **Jina Reader** (`https://r.jina.ai/` + URL). Đây là bản chuyển đổi của bên thứ ba; nguồn tác giả vẫn là DENSO nhưng extraction/cache có thể thiếu hình hoặc khác bản live.
- DRIVEN BASE `all/` EN và JP; theo links đã tìm tới manufacturing series, DX, D-tote; loại các bài ADAS không đúng domain.
- DENSO Technical Review: index chính xác là <https://www.denso.com/jp/ja/business/innovation/review/>. Index trả 38 links volume/issue; đã query các trang mục lục theo links này. 34 snapshot volume được lưu; 4 mục cuối `03-1`, `02-2`, `02-1`, `01` bị HTTP 429 trong lượt đọc. Đây là **tìm theo title mục lục**, không đọc mọi PDF trong 34 số, không phải exhaustive full-text search.
- Google Patents: kết hợp assignee Denso với `"predictive maintenance"`, `"anomaly detection"`, `"fault data"`, `"training data" "vibration"`; đọc toàn văn US10767725B2. Các truy vấn rộng có kết quả automotive và doanh nghiệp cùng tên; không lấy số hits làm số inventions phù hợp, không duyệt hết mọi trang patent.
- Crossref/OpenAlex: tìm DENSO maintenance/anomaly; query chung không đủ chứng minh affiliation. Truy vấn DOI R2 riêng để tìm bản OA.
- GitHub/source gốc của các phương pháp; raw license TimeGAN; trang chính thức dataset PU và HUST.

### 2.2. Truy vấn search engine đã thử nhưng không cho bằng chứng dùng được

`site:denso.com predictive maintenance AI factory abnormality`; `site:denso.com "maintenance" "AI" "data"`; `DENSO predictive maintenance patent anomaly synthetic data`; `site:denso.com "Factory-IoT"`; `DENSO Factory Hacks 2026 scarce fault data`; `site:denso.com 予知保全 AI`.

Google trả nội dung chuyển hướng thay vì kết quả; DuckDuckGo yêu cầu CAPTCHA; Yahoo trả lỗi 500; hai truy vấn Bing trả Anki/WordPad không liên quan. **Không sử dụng các output này làm evidence, không kết luận không có công bố.** Một đường GitHub đoán sai trả 404 không chứng minh paper không có code; bảng dưới chỉ giữ repository đã mở đúng.

### 2.3. Không thể bảo đảm “tất cả DENSO từng công bố”

Còn thiếu full-text archive, PDF scan/OCR, patent family dedup và claims review, J-PlatPat/Espacenet, tài liệu supplier/conference, video không transcript, thông báo riêng Việt Nam và tài liệu mentor. Không có quyền truy cập dữ liệu nội bộ. Khác năm volume với thời gian file upload không phải hai nghiên cứu khác nhau. Kết quả dưới đây là **evidence map có phạm vi và khoảng trống**, không kiểm toán toàn bộ IP hoặc freedom-to-operate.

## 3. Công bố DENSO đã xác minh và ý nghĩa với kế hoạch

### DS1 — Đầu ra cuộc thi: nguồn yêu cầu trực tiếp

Nguồn: <https://densohackathon.vn/challenges>; evidence đã lưu tại `C:\Users\Ad\Downloads\DENSO\research_evidence\official_snapshots\DENSO_website_evidence.txt`.

- A1: **Predictive-Maintenance AI Despite Scarce Fault Data**; generator bất thường, augmented dataset, báo cáo trước/sau augmentation.
- A2: **Accumulate Master Know-How for AI to Learn**; capture workflow/reasoning, KB, trợ lý LLM, usefulness report.
- PDF `A2.pdf` là hồ sơ dự án thứ cấp; không xác nhận nhiệm vụ được giao riêng. Không ghép hai đề chỉ để né mâu thuẫn mã.

**Hệ quả:** nếu làm P, generator vẫn là deliverable nhưng được đánh giá theo real utility; nếu chính thức làm K, áp dụng mục 10 kế hoạch và không dùng benchmark rung để chứng minh usefulness của trợ lý.

### DS2 — Prior art trực tiếp: dữ liệu rung lỗi không phải chờ hỏng thật

**Nagdev Amruthnath, US10767725B2, “Amplitude-modulating vibrator for predictive maintenance modeling”.** Priority/filing 25/07/2018; grant publication 08/09/2020. Original/current assignee hiển thị: **Denso International America Inc**.

Nguồn toàn văn: <https://patents.google.com/patent/US10767725B2/en>. Bản application liên quan: **US20200032874A1** (30/01/2020).

Mô tả nêu chi phí và thời gian chờ sự cố; tạo vibrations ở tần số khác nhau để replicate faults và dùng replicated data xây ML predictive-maintenance model. Claims trình bày thiết bị có lower/upper plates, slots, fastener điều chỉnh, vibrator; truyền vibration signatures sang subject device. **Đây là fault emulation bằng phần cứng**, không phải bằng chứng phần mềm cộng nền khỏe và fit θ few-shot của đội đã hiệu quả.

**Ảnh hưởng:**

1. Bỏ claim “đầu tiên tạo dữ liệu lỗi khi không có lỗi thật”.
2. Rig/testbed kích rung ngoài dây chuyền là một phương án giảm domain gap **nếu được kỹ sư và an toàn phê duyệt**, có thiết bị/budget. Không tự gắn vibrator vào máy sản xuất; dữ liệu emulated vẫn phải kiểm tra utility trên hỏng thật.
3. Patent công khai không phải quyền sử dụng tự do, không phải repository code; legal status Google là thông tin tham khảo, cần registry/chuyên gia IP cho triển khai thương mại.

### DS3 — F-IoT: giá trị nằm ở dữ liệu, con người và cải tiến liên tục

**Motohiro Ishibashi (2022), “Factory Work Style Reform by Building an F-IoT Platform”, DENSO Technical Review Vol.27.** PDF 6 trang, header volume ghi 2022; thời gian upload nguồn là 2023, không đổi năm paper thành 2023.

Index: <https://www.denso.com/jp/ja/business/innovation/review/27/>. PDF: <https://www.denso.com/jp/ja/-/media/Global/business/innovation/review/27/paper-01.pdf>.

Đã đọc văn bản: dự án F-IoT bắt đầu năm 2015; chia sẻ dữ liệu/thông tin cải tiến qua các nhà máy; electronic forms, data-driven morning meetings, data infrastructure, ORiN, loose coupling OSS qua app nội bộ, môi trường app development và monitoring/security. Paper nêu sample code/sample apps **cho người phát triển trên nền tảng**; không thấy link repo public trong bản đọc, không gọi đó là mã nguồn mở DENSO sẵn cho đội.

Paper mô tả OEE activities và explicitly nói F-IoT không phải “magic wand”: phải tìm nguyên nhân, thực hiện biện pháp và hoạt động cải tiến liên tục. Không có counterfactual tách riêng hiệu quả detector của kế hoạch.

**Ảnh hưởng:** thiết kế detector như một module read-only có data contract/evidence/event feedback; không tái xây cả IoT platform, không suy quyền truy cập interface hiện có; đo thời gian review và workload cùng metric ML. Không copy số OEE chart thành ROI của đội. Đây cũng là căn cứ thực tiễn cho capture/reuse knowledge nhánh K, không chứng minh LLM đã giải đúng.

### DS4 — DENSO đã dùng một phương pháp nhẹ: quan hệ đa biến + GLASSO

**Shuhei Yoshida, Nobuo Yamamoto, Tomoko Kanke (2020), “Data-Driven Anomaly Detection of Battery Capacity using Monitoring Data”, DENSO Technical Review Vol.25.** PDF 4 trang.

Nguồn: <https://www.denso.com/jp/ja/-/media/Global/business/innovation/review/25/paper-07.pdf>.

HEMS battery: 40 batteries, khoảng 3,5 năm capacity measurements; 9 monitoring variables gồm voltage/current/temperature, sampling mỗi phút. So sánh quan hệ biến giữa các khoảng thời gian bằng **Graphical Lasso, L1 regularization**, định lượng change qua thống kê; implementation bài viết dùng **R `glasso`**. Tune window, shift, statistic/comparison intervals bằng training data; mô tả test data khác train, sudden deterioration khoảng ngày 700 trong ví dụ. Bản văn bản chưa đủ xác nhận đầy đủ battery-level split allocation/CI; không coi 40 máy là 40 test độc lập.

Paper tự nêu còn vấn đề tuning, threshold và áp dụng hệ battery khác. **Không phải bằng chứng healthy-only hoàn toàn không dùng failure information** vì tuning đã xem train behavior. Không có link raw/code public đã xác minh trong văn bản.

**Ảnh hưởng:** nếu DENSO giao telemetry thấp tần đa biến, kNN/Mahalanobis/relationship-change có thể hợp hơn raw vibration simulator. Có implementation `sklearn.covariance.GraphicalLasso` trong stack hiện có, nhưng đây không phải tái lập nguyên bản DENSO; phải viết comparator và condition normalization/causal window/threshold của task mới. Không dùng paper battery để claim hiệu quả trên vòng bi.

### DS5 — DENSO WAVE: kết nối thiết bị, không phải thuật toán lỗi đã xác minh

Nguồn: <https://www.denso-wave.com/en/system/iot/>. Trang mô tả ORiN cho unified access old/latest equipment, real-time/historical data interfaces, lineup **IoT Data Server, IoT Data Share, IoT Data View, ORiN2 SDK**.

DENSO WAVE là nguồn thuộc nhóm DENSO nhưng không đồng nhất với đội challenge/nhà máy sẽ pilot. Trang đọc không chứng minh một bộ sinh lỗi ít mẫu, không xác minh bandwidth rung hay API được cấp cho đội. ORiN2 SDK được giới thiệu không tự động có open-source license.

**Ảnh hưởng:** hỏi mentor interface/export được phép; ưu tiên loader offline CSV/MAT được cấp trước tích hợp. Timestamp/RPM/units có thể quan trọng hơn thay classifier.

### DS6 — D-tote: tách thu dữ liệu khỏi lớp phân tích

Nguồn bài DENSO JP ngày 24/10/2022: <https://www.denso.com/jp/ja/driven-base/tech-design/d-tote/>.

Mô tả reusable data collection cho PoC, Linux/Docker phía thiết bị, AWS phía cloud, signal/timestamp/value JSON và HIVE/Athena. Bài nói D-tote tập trung **collection**, không có analytics app layer; ứng dụng nhà máy là khả năng mở rộng được nêu, không xác nhận deployed bearing diagnosis.

**Ảnh hưởng:** data platform và ML nên loose-coupled; không buộc dùng AWS/JSON cho rung cao tần, không khẳng định D-tote được phép dùng hoặc có public code. Không nâng collection platform thành digital twin.

### DS7 — Manufacturing DX và hệ thống hóa know-how

Các bài chính thức đã đọc:

- **08/12/2023 (bản EN)**, manufacturing 1: <https://www.denso.com/global/en/driven-base/tech-design/techlinks_manufacturing_1/> — production engineers, robots/AI/digital twins/production simulation, bối cảnh DX.
- **08/12/2023 (EN)**, manufacturing 2: <https://www.denso.com/global/en/driven-base/tech-design/techlinks_manufacturing_2/> — thiết kế/fabrication/start-up, models, visualization, remote troubleshooting; một số nội dung được mô tả là **vision**, không phải đo efficacy của fault generator.
- **08/12/2023 (EN)**, manufacturing 3: <https://www.denso.com/global/en/driven-base/tech-design/techlinks_manufacturing_3/> — formalization/standardization, Lean Automation School, chia sẻ operations/know-how; cơ sở cho capture có ngữ cảnh nhánh K, không phải RAG trial.
- **26/08/2025**, DX citizen development: <https://www.denso.com/global/en/driven-base/project/digital-transformation/> — nhấn mạnh frontline user needs, training/community và process transformation, không benchmark PdM.

Một số bài JP cùng chủ đề có ngày xuất bản khác; báo ngày của ngôn ngữ đã đọc. Các bài `techlinks_ai_1/2` đã kiểm tra chủ yếu về **automated driving**, loại khỏi bằng chứng trực tiếp cho factory scarce fault data. Bài `team-fiot_2109` về teamwork, không dùng chứng minh thuật toán bảo trì.

### DS8 — Nguồn còn chờ đọc/không đủ extraction

Review Vol.4 No.1 (1999), title **設備診断の応用による形状精度診断技術の開発**, tác giả Takashi Kubo / Masuaki Murao theo index JP: <https://www.denso.com/jp/ja/business/innovation/review/04-1/>. PDF <https://www.denso.com/jp/ja/-/media/Global/business/innovation/review/04-1/04-1-doc-dissertation10-ja.pdf> trả metadata 6 trang nhưng không body qua Reader. **Chỉ xác minh title/index**, không suy thuật toán hay performance; cần OCR trước sử dụng.

Vol.27 paper-07 về battery degradation factor analysis được thấy trong index, **chưa đọc toàn văn**, không dùng làm chứng cứ thêm. Không tìm được xác nhận trực tiếp FAIN phù hợp task này trong các nội dung đã đọc; giữ là câu hỏi cho mentor, không gán tính năng.

## 4. Phản biện phương án: điều gì khả dụng hơn?

| Hướng | Phù hợp khi | Ưu điểm thực dụng | Điểm thất bại / điều kiện chọn |
|---|---|---|---|
| Rule + envelope/order features | Rung/RPM/geometry có, lỗi tạo signature rõ | CPU, giải thích, kiểm tra sensor nhanh | Slip/load/sensor ảnh hưởng; không phát hiện mọi lỗi; baseline bắt buộc |
| Healthy-only condition-aware kNN/Mahalanobis/IF | Khỏe nhiều, lỗi rất ít/không có | Không cần phát sinh nhãn lỗi giả; hỗ trợ abnormality chưa biết | Healthy contamination/drift, khó gán nguyên nhân; không thay deliverable augmentation |
| Real-only few-label RF/SVM + standard aug | Có vài physical anchors và holdout | Fit ít tham số, thường nhanh, comparator khó bị đánh bại giả | Cỡ mẫu thật nhỏ, mode confounding; không gọi softmax là confidence calibrated |
| Unanchored physics + healthy background | Biết cơ chế và transfer approximation | Kiểm soát, không phải học distribution lỗi từ 1 record | Domain gap, amplitude/nonlinear damage; phải chấm real utility |
| Anchored physics point/ensemble | Anchors hữu ích, fit có ràng buộc, baseline chưa đủ | Nhắm domain gap, kiểm toán θ/provenance | Non-identifiability, copy anchor, leakage; ưu tiên nghiên cứu **sau baseline**, chưa winner |
| Feature-space augmentation/regularization | Waveform simulator quá khó, ít thời gian | Rẻ và dễ ablate, có thể đủ cho classifier | Feature không bảo đảm tín hiệu vật lý tồn tại; không gọi là waveform fault generator |
| Relationship-change/GLASSO telemetry | Nhiều biến chậm có tương quan đáng tin | Gần hướng DENSO battery đã công bố, model nhẹ | Condition change cũng đổi covariance; battery→factory chưa chứng minh; task riêng |
| Source SSL + frozen embedding | Public/source train nhiều, anchors ít | Tái sử dụng representation | Domain mismatch và test-pretraining leak; thêm TS2Vec có gate, không mặc định |
| GAN/diffusion | Có nhiều fault/source groups và compute, baseline cho thấy thiếu diversity | Flexible multivariate synthesis | Không học reliable fault distribution từ vài phụ thuộc windows; cost/tune/shortcut lớn; backlog |
| Rig/hardware fault emulation | Có testbed ngoài line, approval và budget | Đo được sensor/transfer thực thay mô phỏng hoàn toàn | Safety/IP/time, emulation ≠ hỏng thật; không thử trên line tùy tiện |

**Quyết định đề xuất:** giữ architecture core nhỏ: **QA/context → features → C khỏe và A ít nhãn → event/evidence/review**. Generator là offline module nghiên cứu có gates; E1 đánh giá A riêng để C không che generator thất bại. Nếu C đủ tốt với operational budget, dùng C cho pilot trong khi báo augmentation research trung thực. Nếu dữ liệu thực là telemetry chậm, đổi feature/task trước chọn generator, không resample giả thành rung.

Đây là ưu tiên theo data/engineering risk, **không ranking accuracy đã đo**. Chỉ outer real test khóa và shadow exposure mới quyết định hướng nào thực sự tốt hơn.

## 5. Paper liên quan và mức hỗ trợ thực sự

**Feasibility thực nghiệm bổ sung:** xem mục 5 của `C:\Users\Ad\Downloads\DENSO\docs\results\KET_QUA_THU_NGHIEM_SINH_DU_LIEU_A2.md`. TS2Vec/DeepSVDD/TSB-AD không phải waveform generators; không chạy detector để đánh lạc mục tiêu. Physics/GAN/DDPM prototypes đã chạy nhưng không tái lập nguyên bản các paper. Hướng production chốt là bounded-phase constrained surrogate.

| Paper | Evidence được đọc | Hỗ trợ | Không hỗ trợ / code status |
|---|---|---|---|
| Kahr et al., Sensors 2022, DOI `10.3390/s22072490` | [Toàn văn](https://pmc.ncbi.nlm.nih.gov/articles/PMC9002605/) | 3D simulation + measured healthy background + wavelet/CNN, real damaged measurements kiểm tra | Không chứng minh few-anchor fit của đội; raw data **on request**, không repo mở đã xác minh |
| Ma et al., KBS 2025, DOI `10.1016/j.knosys.2024.112952` | Crossref metadata, OpenAlex OA lookup | Prior-art **gần nhất theo title** cho physics/few-shot | Chưa toàn văn; OpenAlex ghi closed/no OA location, Elsevier endpoint thử trả 400; chưa xác minh code. Không claim novelty vượt bài này |
| Thompson et al., 2024, arXiv `2411.05848` | [Toàn văn v1](https://arxiv.org/html/2411.05848v1) | Diffusion augmentation PRONOSTIA, partition available/unavailable RtFs | Unavailable RtFs có healthy prefix vào available tùy γ: không phải inductive unseen-machine mặc định; unseen fault transfer chỉ minor success. 9 h RTX4090 trong paper không phải cost đội; không thấy original model repo link trong bản HTML |
| Yue et al., AAAI 2022, TS2Vec | Abstract trước đó + original repo README | SSL representation có conditional extension | Không đã tái lập bearing task; dependencies cũ, phải audit fit/eval leakage |
| Ruff et al., ICML 2018, Deep One-Class Classification | [PMLR](https://proceedings.mlr.press/v80/ruff18a.html), repo README | Deep SVDD objective | Original code demo images MNIST/CIFAR, không loader rung plug-and-play |
| Kim et al., Towards a Rigorous Evaluation of TSAD | [arXiv](https://arxiv.org/abs/2109.05257), mức abstract của kế hoạch | Cảnh báo point adjustment | Không thay grouped split và operational alarm metrics |
| Liu & Paparrizos, NeurIPS 2024, The Elephant in the Room / TSB-AD | Original repo/readme và citation | Benchmark/algorithms cho TSAD | Không DENSO fault dataset, không mọi default metric đều operational phù hợp |
| Yoon et al., NeurIPS 2019, TimeGAN | Original repo/readme/license | General time-series synthesis comparator nếu đủ data | Ví dụ sine/stock/energy; không chứng minh 1–2 physical anchors đủ. Không tự động chọn GAN vì public code |

**R1 đọc lại để chống cherry-pick:** bài dùng 18.000 simulated training và 6.000 validation images; thêm measured healthy background. Có additional measured bearings nhưng không đủ cơ sở nâng toàn bộ protocol thành benchmark group-held-out theo kế hoạch. Bài báo mean prediction performance simulation **60,5%** vs measured-training **88,3%**, phạm vi outer-ring faults và có outliers/mild faults yếu; đây không phải accuracy mục tiêu đội. Prior art cho thấy sim-to-real có ích nhưng **không luôn hơn real-only**, cần equal-data comparator và independent groups.

**R3 đọc lại:** mỗi sample 2560×2; fault horizon theo EoL heuristic 3 SD và unavailable healthy prefix phải khai báo; không dùng heuristic đó làm onset thật DENSO. Mục đích bài khác few-anchor constrained fit. Không có original source link đã xác minh không đồng nghĩa tác giả không phát hành ở nơi khác.

## 6. Source code public đã mở: chọn gì và cần sửa gì?

Chỉ là **đã đọc repository/license**, chưa clone/cài/tái lập. Giấy phép bên dưới của repo tại thời điểm đọc không cấp quyền cho datasets, models hoặc patents kèm theo. Trước reuse lưu commit, full license/NOTICE và requirements; không dựa stars hay tên paper để chọn.

| Repository chính xác | License hiển thị/đã đọc | Module dùng được | Mức ưu tiên và giới hạn |
|---|---|---|---|
| <https://github.com/scipy/scipy> | BSD-3-Clause | Filter, Hilbert/envelope, PSD/FFT, optimization | **Core**; tự kiểm tra unit/fs/causal preprocessing/boundaries |
| <https://github.com/scikit-learn/scikit-learn> | BSD-3-Clause | RF/SVM/kNN/IF, covariance, GraphicalLasso, group split | **Core**; chốt calibration ngoài `predict`/contamination defaults; project train-only pipeline |
| <https://github.com/yzhao062/pyod> | BSD-2-Clause | Nhiều outlier detectors và comparator | Optional; classic APIs, không cần agentic orchestration; không dùng contamination train làm operational FPR |
| <https://github.com/zhihanyue/ts2vec> | MIT | Original TS2Vec encoder | Conditional SSL. URL tác giả cũ `yuezhihan` redirect; README Python3.8/torch1.8.1/numpy1.19.2 khác môi trường hiện tại |
| <https://github.com/lukasruff/Deep-SVDD-PyTorch> | MIT | Objective/pretraining structure | Conditional deep; Python3.7/image loader, cần 1D network/loader và split riêng |
| <https://github.com/TimeEval/TimeEval> | MIT | Benchmark framework, adapters, metrics | Tham khảo hoặc môi trường riêng; README yêu cầu Python≥3.9,<3.13, dependency `prts`/NumPy<2 có thể xung đột NumPy2.4.4 hiện tại; không cài đè |
| <https://github.com/TheDatumOrg/TSB-AD> | Apache-2.0 | TSAD algorithms/tutorials/evaluation | Optional evaluation reference; thuật toán có online/test updates phải tách khỏi frozen inductive protocol; audit dataset/third-party licenses |
| <https://github.com/jsyoon0823/TimeGAN> | Raw `license`: Apache-2.0 header | Original GAN generation/metrics | Backlog; legacy dependencies và metrics distribution/predictive không thay real-fault utility |
| <https://github.com/princeton-nlp/ALCE> | MIT | Citation evaluation/baselines, K | **K-only**; ASQA/QAMPARI/ELI5 không safety benchmark nhà máy; data/model terms riêng |
| <https://github.com/microsoft/graphrag> | MIT | Graph memory/index/search, K | Backlog; repo đọc cảnh báo indexing expensive, research demonstration, largely maintenance mode; hybrid case retrieval nhẹ trước |

**Khoảng trống quan trọng:** chưa xác minh được một repo mở hoàn chỉnh thực hiện chính xác “fit ít real fault anchors + impulse response constrained ensemble + real healthy background + independent-bearing evaluation”. Core generator cần hiện thực kiểm thử có chủ đích; không lấy repo TimeGAN rồi nói đã giải phần neo. Repo public không đồng nghĩa code chạy được trên môi trường này.

## 7. Dataset: khả thi được nâng lên ở đâu, vẫn yếu ở đâu?

PU nguồn chính thức đã đọc cả [download](https://mb.uni-paderborn.de/en/kat/research/bearing-datacenter/data-sets-and-download), [conditions](https://mb.uni-paderborn.de/en/kat/research/bearing-datacenter/operating-conditions) và [damage](https://mb.uni-paderborn.de/en/kat/research/bearing-datacenter/bearing-damage):

- 6 undamaged, 12 artificial, 14 real damages caused by accelerated lifetime; bearing type 6203.
- 20 recordings ×4 s mỗi setting, 4 settings. Setting basic 1500 rpm/0,7 Nm/1000 N; thay từng biến xuống 900 rpm, 0,1 Nm, 400 N; temperature khoảng 45–50 °C.
- Fact sheets/measurement logs là nguồn map physical ID, location/combined/severity. Chưa download raw/fact sheets để xác định đủ nhóm mỗi fault class. Không gọi real accelerated damage là field DENSO failures.
- License **CC BY-NC 4.0**, commercial use cần liên hệ. Không coi mọi hackathon use là NC hợp lệ mặc định; chốt quyền demo/distribution với đội/BTC.
- Sáu healthy physical groups ít cho train/dev/rank/final-cal/test và subgroup FPR; repeats/windows không tăng independent groups. Conformal window calibration khi serial correlated không được bảo đảm như iid. Ưu tiên fixed score protocol/nested groups có limitations, không tạo pseudo-replicates.

HUST Mendeley `/3` direct fetch chỉ trả JS shell/footer, **không xác minh raw license ở lượt này**. Bài HUST đã có trong kế hoạch hỗ trợ 99 signals/conditions, không map đủ physical independence. CWRU chủ yếu smoke test; nguồn public không mặc định quyền thương mại. Không tải hàng GB trước khi biết task/group/permission. PU chưa phải lựa chọn chắc chắn cho k=10.

## 8. Giao thức tối thiểu để kiểm tra “khả dụng hơn”

1. Xác nhận scope P/K và data contract. Với P chọn một cơ chế/condition; khóa physical holdout và dataset permissions.
2. Train fit features/model/generator; **development** chọn config/rank-reference/fusion/state machine; **final-calibration khỏe riêng** đặt ngưỡng score đã khóa; test cuối không làm quality gate hoặc select model.
3. Core comparator: rule/envelope, P0 real-only, P1 standard augmentation, C healthy-only. Tiếp P2 unanchored/P3 anchored; P4 uncertainty nếu có lý do. Chấm A trước; C-only và A+C riêng, không thay C/fusion tùy test.
4. Giữ real-group weights, anchors, background quotas, synthetic accepted count và search budgets như mục 13.5 kế hoạch. Ghi attempted/rejected, cost fit/generation/classifier/search, không chỉ “cùng model”.
5. Primary endpoint H1: paired delta recall A trên real groups tại threshold có cùng **nominal calibration FPR**; báo actual heldout FPR, coverage và per-group errors. Không dùng test labels để tune threshold tới đúng 1% rồi gọi khả dụng.
6. Quality/OOD rejection không biến mất: raw ledger, accepted vs end-to-end recall/FPR denominators, subgroup coverage, quality tickets, unresolved incidents. Rejection thành công không tự động bằng phát hiện fault.
7. Replay theo thời gian: valid exposure/invalid time, fault và quality/OOD tickets, incident recall/delay, cooldown/alarm time, compute. Zero alarm vài giây không chứng minh alarm/day; không tính intervals không đo là giám sát.
8. Nếu generator không cải thiện trong development budget, dừng thêm model; báo negative result. Nếu test dùng một lần không xác nhận improvement, hạ claim. Nếu pilot không đủ healthy hours hoặc incidents, kết luận chưa đủ bằng chứng, không hứa ROI.

## 9. Kết luận cuối và các vấn đề chưa thể đóng

**Khuyến nghị chọn hướng:** baseline-first + condition-aware healthy detector + augmentation có kiểm toán. Anchoring là phép thử trung tâm, không tín điều. Giữ phạm vi vòng bi/một cơ chế trước; telemetry relationship-change có thể hợp hơn nếu đó là dữ liệu được giao; diffusion không ưu tiên mặc định.

**Claim nên dùng:** “Thử nghiệm bộ sinh lỗi cơ chế hẹp có neo trên nền khỏe, đo giá trị tăng cường bằng holdout thật và ngân sách báo giả; nếu không có ích, hệ thống vẫn giữ detector nhẹ và báo giới hạn.”

**Claim không nên dùng:** đầu tiên tạo fault data; học được mọi unknown; vài windows chứng minh few-shot; calibrated confidence chắc chắn dưới drift; OEE/RUL/ROI DENSO đã được chứng minh; có repo mở nên chỉ cần chạy.

**Còn mở:** xác nhận nhiệm vụ riêng, DENSO raw/labels/sensor permission, PU fact sheets và physical class counts, healthy exposure, R2 toàn văn/code, IP/FTO cho hardware extension, các PDF scan và archive/patent chưa duyệt hết. Không thể giải quyết bằng cách viết thêm architecture. Tài liệu đã sẵn cho triển khai có gates, không sẵn để tuyên bố kết quả chưa làm.

**Kiểm tra môi trường:** import versions đã xác nhận trong kế hoạch; smoke trên tín hiệu/mảng toy cho Hilbert envelope 40 Hz, RF/covariance output hữu hạn và PyTorch tensor trên CUDA chạy thành công. Bản ghi: `C:\Users\Ad\Downloads\DENSO\research_evidence\environment_smoke.json`. Chỉ giảm rủi ro môi trường ban đầu; không chứng minh phương pháp, không đã chạy repository ngoài hoặc dữ liệu lỗi thật.
