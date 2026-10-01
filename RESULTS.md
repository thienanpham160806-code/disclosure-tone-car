# Kết quả – Đồ án 05: Giọng điệu văn bản công bố và phản ứng thị trường (Mỹ + Việt Nam)

**Câu hỏi nghiên cứu:** giọng điệu (tone) của văn bản công bố thông tin tác động tích cực hay tiêu cực lên CAR[T, T+3], tức là văn bản có mang thông tin cho thị trường hay không?

**Tóm tắt**

- **Mỹ (10-K, 2015–2024):** không có bằng chứng cho thấy giọng điệu mang thông tin cho giá.
  - CAR[0,3] không khác 0.
  - Hệ số của tone tiêu cực chuẩn hóa là −0,04 điểm % trên 1 độ lệch chuẩn, không có ý nghĩa.
  - Kết luận giữ nguyên trong mọi phép kiểm định độ vững, với LM tf-idf, MD&A và cả FinBERT.
- **Việt Nam (thông điệp của ban lãnh đạo – chủ yếu Chủ tịch HĐQT – trong BCTN 2016–2025):**
  - Ở cửa sổ chính [0,3], hệ số có dấu âm như kỳ vọng (−0,16 điểm % trên 1 độ lệch chuẩn) nhưng không có ý nghĩa (p = 0,39).
  - Ở cửa sổ [0,5] hệ số có ý nghĩa (−0,68 điểm %, p = 0,0045) và qua hiệu chỉnh Bonferroni cho 7 cửa sổ (ngưỡng 0,0071), phù hợp với giả thuyết thị trường phản ứng chậm.
  - Bằng chứng này vẫn chưa vững: [0,10] không có ý nghĩa (p = 0,12); p của [0,5] đã dao động quanh ngưỡng qua các bước làm sạch dữ liệu (0,0051 → 0,0077 → 0,0045, mục 4.5–4.7); CAR placebo cũng âm có ý nghĩa và hệ số placebo ở mức 10%; bốn phân tích bổ sung đăng ký trước (ngày công bố thật, thay đổi tone, bỏ sự kiện trùng tin) không có kiểm định chính nào có ý nghĩa (mục 4.8).
- **Từ điển tổng quát sai lệch rất nặng trong ngữ cảnh tài chính:**
  - 73,9% số lần Harvard GI gắn nhãn "tiêu cực" rơi vào từ không tiêu cực trong tài chính (TAX, COST, CAPITAL…). Với VietSentiWordNet, tỷ lệ này là 92,0% ("cho", "thương", "bán"…).

> Mọi con số trong tài liệu này lấy từ file trong `outputs/` (tên file ghi trong ngoặc vuông). Mọi thay đổi code, cấu hình và từ điển trong lần chạy này đều ghi trong `CHANGELOG_RUN.md`. Có ba quyết định phương pháp do nhóm duyệt: danh sách LM theo cờ > 0 (#12), mở rộng `fin_vn.csv` (#21), và chấp nhận thông điệp của **ban lãnh đạo** (Chủ tịch HĐQT, TGĐ, thư chung, HĐQT) khi BCTN không có thư riêng của Chủ tịch (#26). Ngoài ra có ba thay đổi về nguồn dữ liệu hoặc ngày sự kiện: dùng ngày ModDate của PDF làm T=0 (#14); nguồn giá VN là CafeF (#15, #19) do vnstock bị PyPI cách ly (quarantine). Các số liệu VN trong bản này dùng văn bản thư **đã qua tầng AI sửa OCR** (Gemini chép nguyên văn từ ảnh trang, #33–#42; từ #65 áp cho mọi trang phải OCR; mục 4.5), **trang thư đã được rà lại bằng ảnh** cho 238 thư (104 thư ở #44, #55 – mục 4.6; 134 thư ở #65 – mục 4.7) và **thứ tự đọc theo cột** cho trang nhiều cột (#65). Văn bản 10-K đã bỏ khối dữ liệu máy XBRL lọt vào toàn văn (#64, mục 4.7). Phân tích bổ sung S1–S4 được **đăng ký trước** trong CHANGELOG #66 trước khi chạy (mục 4.8).

---

## 1. Mẫu cuối cùng

### 1.1 Phễu mẫu

**Mỹ** [`outputs/us/sample_funnel.csv`]

| Bước | Số văn bản |
|---|---:|
| Công ty trong mẫu | 50 |
| Hồ sơ 10-K nộp 2015–2024 (SEC submissions API, gồm CIK tiền nhiệm của XOM, DIS, GOOGL) | 500 |
| Tải được file HTML chính | 500 |
| Toàn văn ≥ 2.000 từ | 500 |
|   trong đó cắt được MD&A | 457 |
| Có CAR[0,3] | 500 |
| Vào hồi quy M2 (đủ biến kiểm soát) | 470 |

Hồi quy mất 30 quan sát so với 500: 10 hồ sơ của **V**, vì XBRL không có số cổ phiếu tổng (Visa chỉ khai theo lớp A/B/C); và 20 hồ sơ có **vốn chủ sở hữu âm** (BA, LOW, MCD, HD, ORCL), vì B/M không xác định được. MD&A không cắt được ở 43 hồ sơ, và tất cả đều là trường hợp MD&A được "incorporated by reference" sang Exhibit 13, tức không nằm trong file 10-K chính: IBM, WFC, PFE, VZ, T, WMT…

**Việt Nam** [`outputs/vn/sample_funnel.csv`]

| Bước | Số văn bản |
|---|---:|
| Mã VN30 + VN100 (rổ hiện hành, kỳ 7/2026) | 100 |
| Mã–năm có BCTN PDF trên CafeF (2016–2025; gồm 10 BCTN giải nén từ .zip/.rar) | 813 |
| Tìm được thông điệp của ban lãnh đạo | 605 |
|   không có thư (`not_found`) | 195 |
|   loại sau kiểm tra tay | 13 |
| Có ngày sự kiện T=0 hợp lệ | 537 |
| Có CAR (≥ 80 phiên ước lượng) | 508 |
| Có CAR[0,3] | 505 |
| Vào hồi quy M2 | 505 |

Tìm được thư ở 605/813 = 74,4% BCTN. Nguyên nhân chính của phần còn lại là nhiều BCTN, đặc biệt loại lập theo mẫu biểu, **không có** thông điệp của lãnh đạo (ANV, EVF, SJS, VGC, VSC, VIX, DSE gần như mọi năm). Những BCTN này bị loại, **không** thay bằng "Báo cáo của HĐQT".

Có 278 văn bản được xác định trang bằng tay (`data/vn/processed/manual_pages.csv`, có ghi chú từng ca), dựa trên text từng trang và **ảnh trang PDF**:
- 50 ca từ đợt kiểm tra đầu (#26): 49 văn bản được trích lại, 1 văn bản bị loại (CTD 2021).
- 80 thư mà bước trích tự động cắt ở trần 6 trang, tức không tìm thấy chỗ kết thúc thư (#44): 71 được xác định lại trang (46 sai cả trang bắt đầu, vì regex bắt nhầm mục lục hoặc trang "dấu ấn"), 9 bị loại vì BCTN không có thư (CMG 2016, EVF 2023, VIB 2020, VIC 2018, VIX 2016 và 2021–2024).
- 24 thư không có lời chào hay câu kết nào (“Kính gửi”, “Trân trọng”…) (#55): 9 được xác định lại trang (MWG 2025 trước đó là trang mục lục; STB 2019, NLG 2019, VJC 2018, BSR 2021 lấy nhầm trang khác; VPI 2017, VCB 2017, MBB 2018, MBB 2020 lấy lố trang), 3 bị loại (BMP 2022 – file thực chất là bản tiếng Anh; NAB 2019, OCB 2018 – không có thư), 12 đúng trang (thư chỉ viết không có lời chào).
- 134 thư trong đợt rà #65: rà ảnh 181 thư có dấu hiệu lấy nhầm trang (trang có tiêu đề mục lục, trang < 150 từ hoặc tiêu đề của mục khác ở đầu trang) trong số 452 thư trước đó chưa rà tay; 134 thư sai khoảng trang và được sửa. Lỗi hay gặp: lẫn trang mục lục, trang bìa chương, trang giới thiệu hay "dấu ấn năm"; lẫn thư của TGĐ hoặc Phó Chủ tịch ngay sau thư Chủ tịch; thiếu trang cuối có chữ ký; VIC 2023 lấy nhầm công văn gửi UBCK, REE 2019 và PVT 2025 trỏ sai hẳn trang.
- 5 văn bản bị font mã hóa sai, được ép OCR (`force_ocr`).
- 1 thư có thật nhưng không đọc được chữ (DCM 2025, chữ trên nền màu) vẫn để ngoài mẫu.

Quy tắc chọn văn bản: ưu tiên thư riêng của Chủ tịch HĐQT; nếu BCTN chỉ có thư chung (Chủ tịch + TGĐ), "Thông điệp Ban lãnh đạo" hoặc thư của TGĐ thì dùng thư đó (VCB, NLG, VIC, POW, BSR…).

### 1.2 Độ phủ theo năm

| Năm tài chính | Mỹ: có tone | Mỹ: có CAR[0,3] | VN: có tone | VN: có CAR[0,3] |
|---|---:|---:|---:|---:|
| 2014 | 36 | 36 | – | – |
| 2015 | 49 | 49 | – | – |
| 2016 | 50 | 50 | 50 | 36 |
| 2017 | 51 | 51 | 54 | 40 |
| 2018 | 50 | 50 | 66 | 52 |
| 2019 | 50 | 50 | 57 | 50 |
| 2020 | 49 | 49 | 48 | 36 |
| 2021 | 50 | 50 | 61 | 55 |
| 2022 | 50 | 50 | 42 | 35 |
| 2023 | 51 | 51 | 67 | 56 |
| 2024 | 14 | 14 | 78 | 71 |
| 2025 | – | – | 82 | 74 |

[`outputs/us/coverage_by_year.csv`, `outputs/vn/coverage_by_year.csv`]

Ở Mỹ, "năm" là năm tài chính: 10-K nộp năm 2015 phần lớn là FY2014. Ở VN, độ phủ năm 2020 và 2022 thấp vì CafeF không có tài liệu nào cho năm đó ở khoảng 30 mã. Độ phủ các năm đầu thấp hơn vì nhiều mã chưa niêm yết.

---

## 2. Mục tiêu 1: Biến văn bản thành biến định lượng

Tone = số từ (âm tiết) thuộc từng nhóm / tổng số từ. Mẫu số ở Mỹ là số từ nằm trong LM Master Dictionary, đúng theo phụ lục của LM (2011). Mọi biến tone được winsorize ở mức 1%/99%.

**Thống kê mô tả (%)** [`outputs/us/tone_descriptive.csv`, `outputs/vn/tone_descriptive.csv`]

| Biến | Mỹ: trung bình | Mỹ: độ lệch chuẩn | VN: trung bình | VN: độ lệch chuẩn |
|---|---:|---:|---:|---:|
| fin_neg (tiêu cực, từ điển tài chính) | 1,909 | 0,489 | 0,591 | 0,501 |
| fin_pos (tích cực) | 0,587 | 0,174 | 3,334 | 1,034 |
| fin_unc (bất định) | 1,611 | 0,335 | 0,282 | 0,251 |
| fin_lit (pháp lý) | 1,304 | 0,434 | 0,002 | 0,012 |
| gen_neg (tiêu cực, từ điển tổng quát) | 2,761 | 0,377 | 2,110 | 0,709 |
| fin_net = (Pos−Neg)/(Pos+Neg) | −0,519 | 0,138 | +0,703 | 0,239 |
| finA_neg (MD&A, chỉ Mỹ) | 1,409 | 0,593 | – | – |

- **Mỹ:** `fin_neg` trung bình 1,9% toàn văn, cùng bậc với con số khoảng 1,4% trong LM (2011). Đối chiếu độc lập với LM 10X Summaries trên 40 hồ sơ ngẫu nhiên cùng phạm vi văn bản cho tương quan N_Negative = 0,989 và N_Positive = 0,991, lệch trung vị +3,5% và −1,2% [`outputs/us/validate_vs_lm_fullsub.csv`]. Khâu làm sạch và đếm từ vì vậy tái lập được kết quả của LM. So với số liệu LM trên toàn bộ hồ sơ, tương quan chỉ 0,66 [`outputs/us/validate_vs_lm.csv`], vì LM đếm cả exhibit (EX-13…) còn biến chính của nhóm chỉ dùng file 10-K chính.
- **Việt Nam:** thư của lãnh đạo **rất tích cực**. Tỷ lệ từ tích cực (3,3%) gấp khoảng 5,6 lần tỷ lệ từ tiêu cực (0,6%), nên `fin_net` = +0,70, trong khi 10-K Mỹ có `fin_net` = −0,52. `fin_lit` gần 0: thư lãnh đạo hầu như không dùng ngôn ngữ pháp lý.

**Xu hướng theo năm (%)** [`outputs/us/tone_by_year.csv`, `outputs/vn/tone_by_year.csv`; hình `fig1_tone_by_year.png`]

| Năm | Mỹ fin_neg | Mỹ finA_neg (MD&A) | VN fin_neg | VN fin_pos | VN fin_net |
|---|---:|---:|---:|---:|---:|
| 2016 | 1,83 | 1,45 | 0,43 | 3,09 | 0,76 |
| 2017 | 1,82 | 1,40 | 0,32 | 3,21 | 0,82 |
| 2018 | 1,81 | 1,31 | 0,39 | 3,23 | 0,79 |
| 2019 | 1,89 | 1,36 | 0,69 | 3,03 | 0,65 |
| **2020** | **1,94** | **1,48** | **0,99** | 3,08 | **0,52** |
| 2021 | 1,98 | 1,38 | 0,92 | 2,99 | 0,53 |
| 2022 | 2,02 | 1,43 | 0,88 | 3,13 | 0,57 |
| 2023 | 2,09 | 1,47 | 0,73 | 3,16 | 0,62 |
| 2024 | 2,18 | 1,22 | 0,47 | 3,83 | 0,78 |
| 2025 | – | – | 0,33 | 4,03 | 0,84 |

**Năm 2020:**
- **Việt Nam:** 2020 là **đỉnh** tỷ lệ từ tiêu cực, 0,99%, gấp khoảng 3 lần năm 2017 (0,32%). `fin_net` cũng xuống đáy (0,52–0,53, 2020–2021). Giọng điệu sau đó hồi dần về mức trước COVID vào 2024–2025.
- **Mỹ:** MD&A có đỉnh cục bộ năm 2020 (1,48% so với 1,36% năm 2019). Tuy vậy, toàn văn 10-K cho thấy xu hướng tiêu cực **tăng liên tục** từ 1,81% (2018) lên 2,18% (2024), không đảo chiều sau COVID. Nguyên nhân phù hợp nhất là 10-K ngày càng dài phần rủi ro (Item 1A) và phần pháp lý.

---

## 3. Mục tiêu 2: Từ điển tổng quát sai lệch trong ngữ cảnh tài chính

**Tỷ lệ nhiễu:** trong tổng số lần từ điển tổng quát gắn nhãn "tiêu cực", tỷ lệ rơi vào từ không nằm trong danh sách tiêu cực tài chính:
- Mỹ (Harvard GI IV-4): **73,9%** [`outputs/us/dictionary_comparison.txt`]
- Việt Nam (VietSentiWordNet 1.3.5): **92,0%** [`outputs/vn/dictionary_comparison.txt`]

Tương quan giữa tỷ lệ từ tiêu cực đo bằng hai từ điển chỉ là 0,566 (Mỹ) và 0,455 (VN), nên hai thước đo đo những thứ khác nhau.

**Các từ bị gán sai hay gặp nhất** [`outputs/us/misclassified_general_neg.csv`, `outputs/vn/misclassified_general_neg.csv`; hình `fig2_misclassified.png`]

| Mỹ – từ | % tần suất | Nghĩa trong tài chính | VN – từ | % tần suất | Nghĩa trong văn bản |
|---|---:|---|---|---:|---|
| TAX | 10,94 | thuế (trung tính, mục bắt buộc) | cho | 25,93 | giới từ "cho, đối với" |
| COST | 5,70 | chi phí, giá vốn | thương | 8,26 | âm tiết trong "thương mại", "thương hiệu" |
| CAPITAL | 5,43 | vốn | bán | 5,26 | "bán hàng", "bán lẻ" – hoạt động kinh doanh |
| FOREIGN | 4,75 | nước ngoài (ngoại tệ, thị trường nước ngoài) | giảm | 4,69 | chiều biến động, không phải giọng điệu (LM cũng không xếp "decrease" vào tiêu cực) |
| EXPENSE | 4,61 | chi phí | hạn | 3,85 | "ngắn hạn", "hạn mức", "kỳ hạn" |
| SERVICE | 4,11 | dịch vụ; "debt service" = trả nợ | mạnh mẽ | 4,53 | mang nghĩa **tích cực** trong thư lãnh đạo |
| LIABILITY | 2,45 | nợ phải trả (khoản mục kế toán) | xanh | 2,81 | "tăng trưởng xanh", "tín dụng xanh" |
| BOARD | 1,75 | hội đồng quản trị | vàng | 1,59 | kim loại vàng, "thời kỳ vàng" |
| VICE | 1,43 | "Vice President" (chức danh) | tệ | 0,98 | âm tiết trong "tiền tệ" |

Từ tiêu cực thật cũng có mặt trong top: LOSS (5,20%), AGAINST, ADVERSE ở Mỹ; "khó khăn" (5,30%) ở VN. Nhưng chúng chỉ chiếm phần nhỏ. Ở VN, nhiễu còn bị khuếch đại vì từ điển tổng quát khớp **từng âm tiết** trong từ ghép ("tệ" trong "tiền tệ"). Khớp cụm dài nhất trong `fin_vn.csv` tránh được lỗi này.

**Mô hình đối đầu M4:** đưa cả hai thước đo vào cùng một hồi quy CAR[0,3], với biến kiểm soát và hiệu ứng cố định (FE) [`outputs/*/regression_main.csv`].

| | fin_neg_z (tài chính) | gen_neg_z (tổng quát) | N |
|---|---|---|---:|
| Mỹ | −0,0018 (0,0018) | +0,0025\* (0,0015) | 470 |
| VN | −0,0017 (0,0022) | +0,0001 (0,0025) | 505 |

Ở Mỹ, từ điển tổng quát cho hệ số **dương**: M3 +0,0018 (p = 0,16), M4 +0,0025\* (p = 0,08) [`outputs/us/xbrl_fix_effect.csv`]. Nếu đọc theo nghĩa đen thì "văn bản càng tiêu cực, giá càng tăng", điều vô lý về kinh tế. Giải thích hợp lý là `gen_neg` chủ yếu đo mật độ các từ như TAX, COST, CAPITAL, LIABILITY, tức đặc điểm ngành và cấu trúc 10-K chứ không phải tin xấu – loại suy luận sai mà LM (2011) cảnh báo khi dùng từ điển tổng quát. Lưu ý: trước khi bỏ khối dữ liệu máy XBRL khỏi toàn văn (#64), hệ số này lớn hơn và có ý nghĩa hơn (M3 +0,0025\*, p = 0,086; M4 +0,0035\*\*, p = 0,034): khối XBRL chứa các tên mục như LAWSUIT, COMPLAINT, PLAINTIFF mà Harvard GI đếm là tiêu cực. Bài học về đo lường vẫn giữ nguyên nhưng độ mạnh của bằng chứng giảm; mức ý nghĩa hiện tại chỉ ở 10%. Từ điển tài chính cho dấu âm như kỳ vọng nhưng không có ý nghĩa. Ở VN, cả hai từ điển đều không có ý nghĩa.

---

## 4. Mục tiêu 3: Tone có mang thông tin cho thị trường không?

Mô hình chuẩn (market model) ước lượng trên [−150, −11] phiên, yêu cầu ≥ 80 phiên. Beta trung vị là 0,94 (Mỹ) và 1,06 (VN); |CAR[0,3]| lớn nhất là 31,6% và 25,5%, không có giá trị vô lý [`outputs/*/event_study_diag.csv`]. Với Mỹ, T=0 là `acceptanceDateTime` (nộp sau 16:00 thì tính là phiên sau). Với VN, T=0 là ngày ModDate của PDF BCTN. Mọi biến tone được chuẩn hóa z, nên hệ số chính là mức thay đổi CAR (theo đơn vị thập phân) khi tone tăng 1 độ lệch chuẩn.

### 4.1 CAR[T, T+3] dương hay âm, có khác 0 không?

[`outputs/*/car_tests.csv`]

| | N | CAR[0,3] trung bình | Trung vị | t (p) | t BMP | p Wilcoxon | % CAR > 0 (p sign test) |
|---|---:|---:|---:|---|---:|---:|---|
| Mỹ | 500 | −0,17% | −0,13% | −1,02 (0,31) | −0,99 | 0,19 | 48,2% (0,45) |
| VN | 505 | −0,33% | −0,26% | −1,56 (0,12) | −1,12 | 0,07 | 46,3% (0,11) |

**Ở cả hai thị trường, CAR[0,3] hơi âm nhưng không khác 0**, theo cả kiểm định tham số lẫn phi tham số.

Ở VN, cửa sổ dài hơn cho CAR âm có ý nghĩa: CAR[0,5] = −0,76% (p = 0,003); CAR[0,10] = −1,05% (p = 0,002). Dạng điều chỉnh theo thị trường (market-adjusted) cho CAR[0,5] = −0,59% (p = 0,020). Tuy nhiên, **CAR placebo [−60] cũng âm và có ý nghĩa**: −0,38% (p = 0,044; Wilcoxon p = 0,024). Như vậy một phần độ trôi âm là đặc điểm chung của giai đoạn tháng 3–5 hoặc của mô hình ước lượng, chưa chắc là phản ứng với BCTN.

Ở Mỹ, CAR placebo **dương** và có ý nghĩa (+0,25%, p = 0,02). Lùi 60 phiên từ ngày nộp 10-K (tháng 2) thì rơi vào mùa công bố KQKD quý 3, thời điểm thường có lợi suất bất thường dương.

### 4.2 Có phân hóa theo tone không (T3 − T1)?

Chia mẫu thành ba nhóm bằng nhau theo `fin_net` [`outputs/*/car_by_tone.csv`; hình `fig3_caar_by_tone.png`]:

| | T1 Tiêu cực | T2 Trung tính | T3 Tích cực | **T3 − T1 (p Welch)** |
|---|---|---|---|---|
| Mỹ | −0,08% (p 0,79) | −0,13% (p 0,58) | −0,26% (p 0,20) | **−0,19 điểm % (0,60)** |
| VN | −0,49% (p 0,18) | −0,45% (p 0,15) | −0,09% (p 0,78) | **+0,40 điểm % (0,42)** |

- **Mỹ:** không có phân hóa; chênh lệch còn ngược dấu kỳ vọng.
- **VN:** chênh lệch T3 − T1 đúng dấu nhưng nhỏ và không có ý nghĩa. Ở cửa sổ [0,3], nhóm tone tiêu cực nhất có CAR âm nhất (−0,49%) nhưng không khác 0 (p = 0,18); không nhóm nào có ý nghĩa. (Các lần chạy trước: lần đầu T1 = −0,74%, p = 0,057; sau rà trang #44/#55, nhóm trung tính là nhóm âm nhất −0,61%, p = 0,045 – kết quả theo nhóm nhạy với việc trích đúng văn bản.) Đường CAAR của nhóm tiêu cực nhất (cộng dồn từ T−10) tiếp tục đi xuống sau T+3 và thấp nhất trong ba nhóm ở T+6, khoảng −1,9% (hình 3) [`outputs/vn/caar_by_tone.csv`], phù hợp với phản ứng chậm ở cửa sổ [0,5].

### 4.3 Hồi quy: hệ số fin_neg_z và độ lớn kinh tế

OLS gộp, sai số chuẩn cluster theo mã, FE năm (Mỹ thêm FE ngành SIC 2 chữ số). Biến kiểm soát:
- **Mỹ:** log vốn hóa, log B/M, log turnover, pre_alpha, log độ dài văn bản.
- **VN:** log GTGD, pre_ret, log độ dài, dummy VN30, beta.

[`outputs/*/regression_main.csv`, `outputs/*/economic_magnitude.csv`]

| Mô hình | Mỹ: hệ số (SE) | Mỹ: Δ CAR khi +1 SD | VN: hệ số (SE) | VN: Δ CAR khi +1 SD |
|---|---|---:|---|---:|
| **M2 fin_neg_z** | −0,0004 (0,0016) | **−0,04 điểm %** | −0,0016 (0,0019) | **−0,16 điểm %** |
| M5 fin_net_z | −0,0009 (0,0013) | −0,09 | +0,0010 (0,0025) | +0,10 |
| M5 fin_unc_z | −0,0018 (0,0026) | −0,18 | −0,0028 (0,0021) | −0,28 |
| M6 fin_neg_tfidf_z (LM eq. 1) | −0,0012 (0,0039) | −0,12 | −0,0005 (0,0024) | −0,05 |
| M7 finA_neg_z (MD&A) | −0,0006 (0,0021) | −0,06 | – | – |
| M8 finbert_net_z (FinBERT) | −0,0011 (0,0016) | −0,11 | – | – |

1 độ lệch chuẩn của `fin_neg` tương ứng 0,49 điểm % số từ ở Mỹ và 0,50 điểm % số âm tiết ở VN [`outputs/*/tone_descriptive.csv`].

**Câu trả lời trực tiếp:**
- **Mỹ:** tăng 1 độ lệch chuẩn tone tiêu cực làm CAR[0,3] thay đổi −0,04 điểm %. Mức này **không khác 0** về thống kê và rất nhỏ về kinh tế: khoảng 1/90 độ lệch chuẩn của CAR[0,3], vốn là 3,72% [`outputs/us/event_study_diag.csv`]. Không mô hình nào, kể cả FinBERT (tương quan với `fin_net` là 0,35 [`outputs/us/event_study_diag.csv`]; 200 câu đầu của MD&A, mục 4.7), tìm thấy thông tin trong giọng điệu 10-K.
- **VN:** tăng 1 độ lệch chuẩn tone tiêu cực làm CAR[0,3] giảm 0,16 điểm %, khoảng 1/30 độ lệch chuẩn của CAR[0,3] (4,73% [`outputs/vn/event_study_diag.csv`]). Kết quả đúng dấu kỳ vọng nhưng **không có ý nghĩa** (p = 0,39 [`outputs/vn/goc_fix_effect.csv`]). Tone bất định `fin_unc_z` cũng không có ý nghĩa (p = 0,17); ở hai bước làm sạch trung gian nó từng đạt mức 10% (p = 0,055–0,069) [`outputs/vn/llm_ocr_effect.csv`, `outputs/vn/page_fix_effect.csv`].

**Fama–MacBeth** [`outputs/*/regression_fama_macbeth.csv`]:
- Mỹ: `fin_neg_z` = −0,0011 (t = −0,95), trên 10 kỳ cắt ngang. Chỉ quý 1 mỗi năm đủ quan sát, vì 10-K tập trung nộp vào tháng 2–3.
- VN: `fin_neg_z` = −0,0001 (t = −0,06), trên 10 năm.

Cả hai đều không có ý nghĩa.

### 4.4 Placebo và độ vững

Hệ số `fin_neg_z`, dùng cùng biến kiểm soát và FE [`outputs/*/regression_robustness.csv`]:

| Biến phụ thuộc | Mỹ | VN |
|---|---|---|
| CAR market-adjusted [0,3] | +0,0006 (0,0018) | −0,0016 (0,0019) |
| BHAR[0,3] (LM 2011) | +0,0007 (0,0018) | −0,0018 (0,0018) |
| **Placebo −60 phiên** | +0,0008 (0,0012) | +0,0032\* (0,0018) |
| CAR[0,1] | +0,0003 (0,0014) | +0,0012 (0,0014) |
| CAR[−1,1] | +0,0024 (0,0019) | +0,0019 (0,0018) |
| CAR[0,5] | −0,0003 (0,0018) | **−0,0068\*\*\* (0,0024)** |
| CAR[0,10] | −0,0016 (0,0025) | −0,0048 (0,0031) |

- **Placebo** không có ý nghĩa ở Mỹ, đúng như mong đợi. Ở VN hệ số placebo **dương** và ở mức 10% (p = 0,076 [`outputs/vn/goc_fix_effect.csv`]) – ngược dấu với hiệu ứng [0,5], nhưng cho thấy mô hình còn nhiễu.
- **VN:** kết quả duy nhất có ý nghĩa là **CAR[0,5]**. Tăng 1 độ lệch chuẩn tone tiêu cực đi kèm CAR[0,5] thấp hơn 0,68 điểm % (p = 0,0045 [`outputs/vn/goc_fix_effect.csv`]). Điều này khớp với hình 3, nơi đường nhóm tiêu cực tách ra rõ nhất ở T+3 đến T+6. Với hiệu chỉnh Bonferroni cho 7 cửa sổ (α = 0,05/7 ≈ 0,0071), kết quả **qua** ngưỡng. Tuy vậy p đã dao động quanh ngưỡng qua các bước làm sạch: 0,0078 (OCR thuần) → 0,0051 (sau tầng AI) → 0,0077 (sau rà 104 thư) → 0,0045 (sau sửa tận gốc #65) – kết quả nằm sát ngưỡng và nhạy với chất lượng trích văn bản. [0,10] không có ý nghĩa (−0,48 điểm %, p = 0,12).
- **Mỹ, kiểm tra bổ sung** (không thuộc thiết kế gốc) [`outputs/us/earnings_overlap.csv`, `outputs/us/regression_excl_earnings.csv`]:
  - 93/500 hồ sơ 10-K (18,6%) được nộp trong vòng ±3 ngày quanh 8-K công bố KQKD (mục 2.02). Nhóm này có |CAR[0,3]| trung bình 4,65%, so với 1,65% ở nhóm còn lại.
  - Sau khi loại các hồ sơ này, `fin_neg_z` = +0,0012 (0,0017), vẫn không có ý nghĩa (`src/analysis/a11_us_excl_earnings.py`).

### 4.5 Tầng AI sửa OCR: có đổi kết luận không?

Tầng AI (`src/textkit/llm_client.py`, gọi từ `v03 --llm`; CHANGELOG #33–#42) chấm điểm chất lượng chữ `quality_score` cho từng trang thư. Chỉ trang dưới ngưỡng 0,85 mới được gửi ảnh cho Gemini (`gemini-3.5-flash-lite`, temperature = 0) để **chép nguyên văn**. Bản AI chỉ được nhận khi điểm không giảm. Bảng dưới là lần chạy tầng AI trên 617 thư, trước khi sửa trang thư ở #44 [`outputs/vn/llm_ocr_summary_truoc_sua_trang.csv`]. Hiện tại, sau khi rà lại trang thư (#44, #55, #65) và áp tầng AI cho **mọi trang phải OCR** (#65), còn 893 trang thuộc 605 thư; 194 trang được gửi AI (36 trang dưới ngưỡng, còn lại là trang OCR có điểm ≥ ngưỡng), 189 trang nhận bản AI, 109 thư có trang dùng bản AI; điểm chất lượng TB (theo token) các thư đó 0,944 → 0,991; tổng token Gemini 503.935 / 204.813, chi phí ước tính nếu trả phí ≈ 0,66 USD [`outputs/vn/llm_ocr_summary.csv`]. Bảng dưới là lần chạy đầu, giữ để đối chiếu:

| | Số lượng |
|---|---:|
| Trang thuộc thư (617 văn bản) | 1.444 |
| Trang gửi AI (dưới ngưỡng) | 131 |
| Trang nhận bản AI | 118 (70 có điểm tăng; 46 là trang gần như trống ở cả hai bản) |
| Trang loại bản AI | 13 (8 điểm không tăng, 4 AI trả rỗng, 1 nghi viết lại) |
| Văn bản có ≥ 1 trang dùng bản AI | 81 |
| Điểm chất lượng TB các văn bản đó (theo token) | 0,922 → 0,964 |
| Token Gemini (đầu vào / đầu ra, gồm lượt chạy thử) | 195.526 / 47.489 |
| Chi phí ước tính nếu dùng gói trả phí | ≈ 0,18 USD (gói miễn phí: 0) |

**Độ chính xác so với trang chuẩn** [`outputs/vn/ocr_eval.csv`, `outputs/vn/ocr_eval_tone.csv`; hình `fig_ocr_eval.png`]: 15 trang chọn ngẫu nhiên (seed 42; 10 trang dưới ngưỡng, 5 trang còn lại). Bản chuẩn do Claude chép từ ảnh trang, không xem bản OCR hay bản Gemini, rồi được người dò lại đối chiếu với ảnh. Tính gộp (tổng lỗi / tổng độ dài chuẩn) trên 13 trang có đủ cả ba phương án; 2 trang Gemini từ chối chép ở chế độ đọc ảnh (RECITATION):

| Phương án | CER | WER | Sai lệch `fin_net` trung bình so với bản chuẩn |
|---|---:|---:|---:|
| Tesseract thuần | 31,3% | 45,2% | 0,257 |
| OCR + LLM sửa lỗi ký tự | 7,2% | 8,4% | 0,003 |
| LLM đọc ảnh (phương án mặc định) | 2,9% | 3,4% | 0,004 |

Lưu ý: bản chuẩn cũng do một mô hình ngôn ngữ chép (dù đã có người dò lại), nên sai số của hai phương án dùng LLM có thể bị đánh giá thấp hơn thực tế.

Ví dụ: MWG 2019 có trang 6 OCR không đọc được (chữ trên nền màu). Bản AI bổ sung khoảng 490 từ, và điểm chất lượng cả thư tăng từ 0,69 lên 0,98. Với các trang số liệu hoặc biểu đồ (SBT 2019, VND 2020), bản AI bỏ các con số OCR vỡ, nên văn bản ngắn đi.

Cùng mô hình, biến kiểm soát, FE và sai số chuẩn cluster, ước lượng trên panel trước và sau khi sửa (cùng trang thư như lần chạy đầu) [`outputs/vn/llm_ocr_effect.csv`]:

| Hệ số (biến phụ thuộc) | Trước: hệ số (SE), p | Sau: hệ số (SE), p |
|---|---|---|
| fin_neg_z (CAR[0,3]) | −0,0019 (0,0020), 0,33 | −0,0024 (0,0020), 0,23 |
| gen_neg_z (CAR[0,3]) | −0,0004 (0,0021), 0,87 | −0,0010 (0,0021), 0,64 |
| fin_unc_z (CAR[0,3], M5) | −0,0029 (0,0021), 0,17 | −0,0037 (0,0020), 0,069 |
| fin_neg_z (CAR[0,5]) | −0,0058 (0,0022), 0,0078 | −0,0063 (0,0023), 0,0051 |
| fin_neg_z (CAR[0,10]) | −0,0044 (0,0031), 0,15 | −0,0049 (0,0031), 0,12 |
| fin_neg_z (Placebo −60) | +0,0021 (0,0016), 0,20 | +0,0025 (0,0016), 0,12 |

N không đổi (514; 499 với placebo), vì tầng AI chỉ thay văn bản chứ không thay mẫu. **Kết luận chính không đổi:** tone không có tác động có ý nghĩa lên CAR[0,3]. Mọi hệ số đều giữ dấu và tăng nhẹ về độ lớn, khớp với việc giảm sai số đo lường (attenuation bias). Ở bước này CAR[0,5] vượt ngưỡng Bonferroni với cách biệt nhỏ; sau khi rà xong trang thư (mục 4.6) thì không còn vượt.

### 4.6 Rà lại trang thư: có đổi kết luận không?

Trang thư được rà lại bằng ảnh trang PDF trong hai đợt và ghi vào `manual_pages.csv`:
- **80 thư** mà bước trích tự động (v03) cắt ở trần `max_letter_pages` = 6 trang (#44): 9 bị loại vì BCTN không có thư của lãnh đạo; 71 được xác định lại trang, thư thật phần lớn dài 1–3 trang.
- **24 thư không có lời chào hay câu kết nào** (#55): 9 sửa trang (MWG 2025 trước đó là trang mục lục), 3 bị loại (BMP 2022 là bản tiếng Anh; NAB 2019, OCB 2018 không có thư), 12 đúng.

Cùng mô hình, ước lượng trên panel trước khi rà trang (đã qua tầng AI) và panel hiện tại [`outputs/vn/page_fix_effect.csv`]:

| Hệ số (biến phụ thuộc) | Trước: hệ số (SE), p | Sau: hệ số (SE), p |
|---|---|---|
| fin_neg_z (CAR[0,3]) | −0,0024 (0,0020), 0,23 | −0,0017 (0,0020), 0,38 |
| gen_neg_z (CAR[0,3]) | −0,0010 (0,0021), 0,64 | −0,0002 (0,0023), 0,91 |
| fin_unc_z (CAR[0,3], M5) | −0,0037 (0,0020), 0,069 | −0,0030 (0,0020), 0,13 |
| fin_neg_z (CAR[0,5]) | −0,0063 (0,0023), 0,0051 | −0,0062 (0,0023), 0,0077 |
| fin_neg_z (CAR[0,10]) | −0,0049 (0,0031), 0,12 | −0,0051 (0,0031), 0,10 |
| fin_neg_z (Placebo −60) | +0,0025 (0,0016), 0,12 | +0,0025 (0,0017), 0,13 |
| N (CAR[0,3]) | 514 | 505 |

Hệ số chính gần như không đổi về dấu và độ lớn; kết luận cho CAR[0,3] giữ nguyên. Hai điểm thay đổi: (1) CAR[0,5] không còn vượt ngưỡng Bonferroni (p 0,0051 → 0,0077); (2) nhóm tone tiêu cực nhất không còn có CAR[0,3] âm có ý nghĩa (mục 4.2). Cả hai cho thấy các kết quả “có ý nghĩa” ở VN nằm sát ngưỡng và nhạy với chất lượng trích văn bản, nên không được dùng làm bằng chứng riêng lẻ cho giả thuyết. (Sau đợt sửa tận gốc #65 ở mục 4.7, p của CAR[0,5] là 0,0045 và lại vượt ngưỡng – xem mục 4.7.)

### 4.7 Sửa tận gốc văn bản (#64 Mỹ, #65 VN): có đổi kết luận không?

**Mỹ – bỏ khối dữ liệu máy XBRL (#64).** Bước làm sạch chỉ bỏ `<ix:hidden>` nên các “context” XBRL trong `<ix:resources>` (mã CIK, ngày, `US-GAAP:…MEMBER`, cả các tên mục như `V:LAWSUIT`, `V:COMPLAINT`) lọt vào toàn văn của 260/500 hồ sơ iXBRL, trung vị 12,5% số ký tự (WFC tới 86%). Nay bỏ toàn bộ `<ix:header>`. Biến tone tài chính gần như không đổi: tương quan trước/sau theo hồ sơ 0,9998 (fin_neg), 0,9998 (fin_lit), 0,9996 (fin_unc), 1,0000 (fin_net); thước đo tổng quát đổi nhiều hơn (gen_neg 0,990) vì Harvard GI đếm LAWSUIT, COMPLAINT… là tiêu cực; MD&A không đổi [`outputs/us/xbrl_fix_tone.csv`].

| Hệ số (CAR[0,3] trừ khi ghi khác) | Trước: hệ số (SE), p | Sau: hệ số (SE), p |
|---|---|---|
| M2 fin_neg_z | −0,0005 (0,0016), 0,75 | −0,0004 (0,0016), 0,79 |
| M3 gen_neg_z | +0,0025 (0,0015), 0,086 | +0,0018 (0,0013), 0,16 |
| M4 gen_neg_z | +0,0035 (0,0016), 0,034 | +0,0025 (0,0015), 0,082 |
| M5 fin_unc_z | −0,0019 (0,0026), 0,47 | −0,0018 (0,0026), 0,49 |
| fin_neg_z → CAR[0,5] | −0,0005 (0,0018), 0,80 | −0,0003 (0,0018), 0,86 |
| M8 finbert_net_z | −0,0015 (0,0013), 0,25 | −0,0011 (0,0016), 0,48 |

Ghi chú FinBERT: lần chạy trước (28/09) dùng 100 câu đầu của MD&A để chạy nhanh; lần này chạy lại toàn bộ 500 hồ sơ với mặc định của code là 200 câu (#64), nên điểm của các hồ sơ có MD&A dài hơn 100 câu thay đổi (tương quan với `fin_net` 0,44 → 0,35); kết quả vẫn không có ý nghĩa.

[`outputs/us/xbrl_fix_effect.csv`] Kết luận cho Mỹ không đổi; điểm khác duy nhất đáng kể là bằng chứng “từ điển tổng quát cho dấu sai” yếu đi (mục 3).

**Việt Nam – thứ tự cột, AI cho mọi trang OCR, rà 134 thư (#65).** (1) Lớp chữ PDF trước đây được sắp theo hàng ngang nên ở trang nhiều cột dòng của các cột xen kẽ nhau; nay dùng thứ tự đọc XY-cut (đọc hết cột trái rồi sang cột phải). (2) Mọi trang phải OCR được Gemini chép lại từ ảnh (mục 4.5). (3) Rà bằng ảnh 181 thư nghi lấy nhầm trang, sửa 134 thư (mục 1.1). Văn bản thay đổi đáng kể: tương quan fin_neg trước/sau theo văn bản 0,967 (162/508 thư đổi giá trị), fin_pos 0,903, gen_neg 0,944 [`outputs/vn/goc_fix_tone.csv`].

| Hệ số (biến phụ thuộc) | Trước #65: hệ số (SE), p | Sau #65: hệ số (SE), p |
|---|---|---|
| fin_neg_z (CAR[0,3]) | −0,0017 (0,0020), 0,38 | −0,0016 (0,0019), 0,39 |
| gen_neg_z (CAR[0,3]) | −0,0002 (0,0023), 0,91 | −0,0006 (0,0022), 0,79 |
| fin_unc_z (CAR[0,3], M5) | −0,0030 (0,0020), 0,13 | −0,0028 (0,0021), 0,17 |
| fin_neg_z (CAR[0,5]) | −0,0062 (0,0023), 0,0077 | −0,0068 (0,0024), **0,0045** |
| fin_neg_z (CAR[0,10]) | −0,0051 (0,0031), 0,10 | −0,0048 (0,0031), 0,12 |
| fin_neg_z (Placebo −60) | +0,0025 (0,0017), 0,13 | +0,0032 (0,0018), 0,076 |
| N (CAR[0,3]) | 505 | 505 |

[`outputs/vn/goc_fix_effect.csv`] Kết luận cho CAR[0,3] không đổi (đúng dấu, không có ý nghĩa). CAR[0,5] vượt ngưỡng Bonferroni cho 7 cửa sổ (0,0045 < 0,0071). Placebo có dấu **dương** và ở mức 10% (p = 0,076) – ngược chiều với hiệu ứng [0,5], nên không phải cùng một xu hướng chung kéo cả hai; nhưng đây cũng là dấu hiệu cho thấy mô hình còn nhiễu.

### 4.8 Phân tích bổ sung đã đăng ký trước (S1–S4)

Thiết kế được ghi vào CHANGELOG #66 và đưa lên GitHub **trước khi chạy** (commit `aae423f`), để tránh chọn cách làm sau khi đã thấy kết quả: CAR[0,3] là biến phụ thuộc chính, cùng biến kiểm soát/FE/SE như M2; 4 kiểm định chính → Bonferroni α = 0,05/4 = 0,0125; CAR[0,5] chỉ để mô tả [`outputs/vn/extra_results.csv`, `outputs/vn/extra_summary.csv`, `outputs/vn/extra_dates.csv`].

- **S1 – ngày công bố thật:** T=0 = ngày CafeF đăng tin công bố thông tin “Báo cáo thường niên năm …” (tin sớm nhất đúng năm, bỏ đính chính/tạm hoãn). Có ngày này cho 182/508 sự kiện. So với ngày ModDate, tin CafeF muộn hơn trung vị 1 phiên (p10 = 0, p90 = 2; muộn hơn ở 119 sự kiện, trùng phiên ở 38, sớm hơn ở 11) – ModDate quả thật sớm hơn ngày công bố.
- **S2 – thay đổi tone:** Δfin_neg = fin_neg năm t − năm t−1 của cùng công ty (370 sự kiện có thư năm trước).
- **S3 – bỏ sự kiện trùng tin:** 215/508 sự kiện có tin CafeF về KQKD hoặc ĐHĐCĐ trong [0,3]; còn 293 sự kiện.
- **S4 – kết hợp S1 + S2 + S3:** 72 sự kiện.

| Mô hình | Mẫu | N | Hệ số CAR[0,3] (SE) | p | Điểm % khi +1 SD | CAR[0,5]: hệ số (p) |
|---|---|---:|---|---:|---:|---|
| M2 gốc (đối chiếu) | toàn mẫu | 505 | −0,0016 (0,0019) | 0,39 | −0,16 | – |
| S1 đối chiếu: M2, T=0 ModDate | sự kiện có ngày CafeF | 166 | +0,0022 (0,0028) | 0,44 | +0,22 | – |
| **S1: M2, T=0 CafeF** | sự kiện có ngày CafeF | 181 | −0,0048 (0,0034) | 0,16 | −0,48 | −0,0065 (0,11) |
| **S2: Δfin_neg** | có thư năm trước | 367 | +0,0000 (0,0027) | 1,00 | 0,00 | −0,0033 (0,23) |
| S2 phụ: Δfin_net | có thư năm trước | 367 | +0,0003 (0,0025) | 0,90 | +0,03 | – |
| **S3: M2, bỏ sự kiện trùng tin** | không trùng tin [0,3] | 291 | −0,0023 (0,0025) | 0,34 | −0,23 | −0,0084 (0,016) |
| S3 độ nhạy: bỏ thêm tháng kho tin hổng | | 268 | −0,0025 (0,0025) | 0,32 | −0,25 | – |
| **S4: Δfin_neg, T=0 CafeF, bỏ trùng tin** | S1 ∩ S2 ∩ S3 | 72 | −0,0076 (0,0067) | 0,26 | −0,76 | −0,0071 (0,40) |

**Kết quả: không kiểm định chính nào có ý nghĩa** (p nhỏ nhất 0,16 so với ngưỡng 0,0125). Hai điểm đáng chú ý, chỉ mang tính mô tả: (1) cùng 166–181 sự kiện, chuyển T=0 sang ngày công bố thật làm hệ số đổi từ +0,22 sang −0,48 điểm % – đúng hướng kỳ vọng nếu ModDate làm lệch cửa sổ, nhưng mẫu nhỏ nên sai số lớn; (2) bỏ sự kiện trùng tin làm hệ số [0,5] lớn hơn (−0,84 điểm %, p = 0,016), tức hiệu ứng [0,5] không do tin KQKD/ĐHĐCĐ gây ra. Thay đổi tone (S2) không mang thêm thông tin nào. Mẫu S4 quá nhỏ (72) để kết luận.

---

## 5. So sánh Mỹ và Việt Nam

| Khía cạnh | Mỹ | Việt Nam |
|---|---|---|
| Giọng điệu văn bản | Tiêu cực, mang tính pháp lý (fin_net −0,52) | Rất tích cực, mang tính quan hệ cổ đông (fin_net +0,70) |
| CAR[0,3] | ≈ 0 | ≈ 0 (âm nhẹ) |
| Tone → CAR[0,3] | Không | Đúng dấu, không có ý nghĩa |
| Tone → CAR dài hơn | Không | Có ý nghĩa ở [0,5] (p = 0,0045, qua Bonferroni cho 7 cửa sổ nhưng sát ngưỡng), chưa vững |

**Lập luận kinh tế:**
1. **Hiệu quả thông tin và thời điểm:**
   - **Mỹ:** 10-K ra 1–4 tuần **sau** thông cáo KQKD và earnings call. Khi 10-K được nộp, phần lớn thông tin đã vào giá, nên giọng điệu gần như không còn gì mới. Mẫu gồm 50 công ty vốn hóa lớn nhất, được theo dõi sát nhất, càng làm tăng hiệu quả này. Tone 10-K còn phản ánh ngôn ngữ rủi ro soạn theo khuôn mẫu pháp lý, ít thay đổi giữa các năm. Kết quả này khác LM (2011), vốn dùng mẫu 1994–2008 với toàn bộ công ty CRSP, gồm nhiều công ty nhỏ ít được theo dõi.
   - **VN:** BCTN và thư của lãnh đạo là kênh truyền đạt quan điểm của ban lãnh đạo tới nhà đầu tư cá nhân, nhóm chiếm phần lớn giao dịch. Mức độ phân tích và đưa tin về doanh nghiệp thấp hơn Mỹ, nên văn bản có nhiều khả năng còn nội dung mới.
2. **Biên độ giá và thanh khoản:** HOSE giới hạn biên độ ±7%/phiên (UPCOM ±15%). Trong cửa sổ ước lượng, tỷ lệ phiên lợi suất bằng 0 có trung vị 7,9% (p90 = 17,1%), so với 0% ở Mỹ [`outputs/*/event_study_diag.csv`]. Thông tin vì vậy vào giá **chậm** hơn, phù hợp với việc phản ứng chỉ hiện rõ ở [0,5]. `log_tradeval` có hệ số âm ở hầu hết các mô hình VN: cổ phiếu thanh khoản thấp phản ứng khác cổ phiếu thanh khoản cao.
3. **Chất lượng công bố thông tin:** thư lãnh đạo ở VN thiên về "tô hồng": từ tích cực gấp khoảng 5,6 lần từ tiêu cực. Vì vậy **mức độ tiêu cực tương đối**, tức việc dám nhắc tới "khó khăn", "suy giảm", là tín hiệu hiếm và có thể mang thông tin. Đây là lập luận tín hiệu tốn kém, tương tự tin xấu trong môi trường ít minh bạch. Điều này khớp với hình 3: đường CAAR của nhóm tone tiêu cực nhất (T1) giảm sâu nhất sau T+3, dù CAR[0,3] của nhóm này không khác 0.
4. **T=0 kém chính xác ở VN:** nếu ngày ModDate sớm hơn ngày đăng thực tế vài ngày, phản ứng thật sẽ lệch sang cửa sổ muộn hơn. Đây là một cách giải thích thay thế, **thuần kỹ thuật**, cho việc tác động chỉ xuất hiện ở [0,5]. Dữ liệu CafeF ủng hộ một phần giải thích này: ở 182 sự kiện có tin công bố, ngày công bố thật muộn hơn ModDate trung vị 1 phiên (mục 4.8).

---

## 6. Kiểm định giả định

[`outputs/*/assumption_tests.csv`, tính trên M2]

| Kiểm định | Mỹ | VN | Kết luận và xử lý |
|---|---:|---:|---|
| Breusch–Pagan (p) | 0,000 | 0,0002 | Phương sai sai số thay đổi → toàn bộ hồi quy dùng **sai số chuẩn cluster theo mã** (vững với phương sai thay đổi và tương quan trong cùng công ty); Fama–MacBeth dùng Newey–West |
| Jarque–Bera (p) | 0,000 | 0,000 | Phần dư không chuẩn (đuôi dày, điển hình của lợi suất) → **winsorize 1%/99%** cho CAR và các biến tone; cỡ mẫu 470–505 đủ lớn để suy luận tiệm cận; bổ sung kiểm định **phi tham số** (Wilcoxon, sign test) và t BMP (chuẩn hóa theo phương sai ước lượng) |
| VIF lớn nhất | 2,98 (log_turn); fin_neg_z 2,85 | 2,97 (log_tradeval); fin_neg_z 1,29 | < 5 → không có đa cộng tuyến đáng lo |
| corr(fin_neg, gen_neg) | 0,566 | 0,472 | Đủ thấp để M4 tách được tác động riêng của hai thước đo |

---

## 7. Hạn chế

1. **Survivorship bias:**
   - Mỹ: 50 công ty lớn đang niêm yết.
   - VN: rổ VN30/VN100 **hiện hành** (kỳ 7/2026) dùng cho mọi năm từ 2016; các công ty bị hủy niêm yết hoặc rơi khỏi rổ không có trong mẫu.
   - Mẫu Mỹ lại gồm những công ty được phân tích nhiều nhất, nên thiên về kết quả "không có phản ứng".
2. **Ngày sự kiện ở VN là ước lượng** [`outputs/vn/event_date_check.csv`]:
   - Khi thu thập BCTN, CDN của CafeF không gửi Last-Modified và không có tài liệu ĐHĐCĐ, nên T=0 là ngày ModDate của PDF (537/605 thư). Về sau, API tin tức theo mã của CafeF cho ngày đăng tin công bố BCTN ở 182/508 sự kiện; ở đó ngày công bố thật muộn hơn ModDate trung vị 1 phiên (mục 4.8).
   - 94,8% ngày T=0 rơi vào tháng 3–5. Ngày ĐHĐCĐ thường niên đến sau T=0 với trung vị 13 ngày (p10 = 3, p90 = 63).
   - ModDate là ngày file được hoàn thiện, nên ngày đăng thật có thể **muộn hơn** vài ngày.
   - 68 thư không có ModDate hợp lệ bị loại khỏi phần nghiên cứu sự kiện.
3. **Từ điển tiếng Việt do nhóm tự xây:**
   - `fin_vn.csv` gồm 201 cụm; bổ sung 9 cụm và bỏ từ đơn "kiện" qua duyệt tay từ `candidate_terms.csv` (CHANGELOG #21).
   - Chưa được kiểm định độc lập kiểu đối chiếu với LM 10X Summaries như ở Mỹ.
   - Chưa tách từ tiếng Việt, chỉ khớp cụm dài nhất theo âm tiết.
4. **Sự kiện trùng thời điểm:**
   - **Mỹ:** 18,6% hồ sơ 10-K trùng KQKD. Đã kiểm tra: loại chúng không đổi kết luận.
   - **VN:** BCTN ra sát ĐHĐCĐ (trung vị 13 ngày) và mùa KQKD quý 1 (tháng 4). Cửa sổ [0,5] và [0,10] có thể lẫn các tin này. CAR placebo VN cũng âm và có ý nghĩa. Phân tích đăng ký trước S3 (mục 4.8) bỏ 215 sự kiện có tin KQKD/ĐHĐCĐ trong [0,3]: hệ số [0,3] không đổi đáng kể, hệ số [0,5] lớn hơn. Tin CafeF quanh ngày công bố (thu thập thêm; `src/vn/v05_news.py`) cho thấy mức độ trùng này là đáng kể [`outputs/vn/news_summary.csv`]: 409/508 sự kiện có ít nhất 1 tin trong [0,3] (trung bình 2,57 tin); trong [0,5], 252 sự kiện có tin về ĐHĐCĐ và 149 sự kiện có tin về kết quả kinh doanh (gán nhãn theo từ khóa trong tiêu đề). Lưu ý: kho tin CafeF bị hổng tháng 02–03/2022, đúng mùa công bố BCTN năm 2021 (số tin mỗi mã dưới 25% trung vị 8,25 tin/mã/tháng [`outputs/vn/news_coverage_monthly.csv`]). 32 sự kiện có cửa sổ [−10,+10] chạm giai đoạn này; 18 trong số đó không có tin trong [0,3] và 5 không có tin nào – với các sự kiện này, "không có tin" không có nghĩa là không có thông tin. Ngoài phân tích S3 (mục 4.8), dữ liệu này không được đưa vào hồi quy chính.
5. **Trích văn bản ở VN:**
   - Mẫu QC 10% (`data/vn/processed/qc_sample.csv`, 59 văn bản, đối chiếu đầu/cuối văn bản và ảnh trang): 49 đúng (10 trong số đó lệch biên nhỏ), 10 sai trang. 9 văn bản sai đã sửa trang, 1 đã loại. Tỷ lệ sai trang khoảng 17% gợi ý phần chưa kiểm tra cũng có tỷ lệ tương tự, chủ yếu là lẫn trang mục lục.
   - Sau đó, toàn bộ 80 thư mà bước trích tự động cắt ở trần 6 trang được rà bằng ảnh (#44): 9 bị loại vì BCTN không có thư, 46 sai cả trang bắt đầu, và cả 71 thư còn lại đều lấy lố trang cuối. Nhóm này đã được sửa hết. Tiếp theo, 24 thư không có lời chào hay câu kết nào được rà bằng ảnh (#55): 9 sửa trang (MWG 2025 trước đó là trang mục lục), 3 bị loại, 12 đúng. Đợt #65 rà thêm bằng ảnh 181 thư có dấu hiệu lấy nhầm trang (trong 452 thư chưa rà) và sửa 134 thư – tỷ lệ sai cao (22% số thư chưa rà), khớp với ước lượng 17% của mẫu QC. Khoảng 270 thư trích tự động không có dấu hiệu nào vẫn chưa được rà toàn bộ bằng ảnh.
   - Lỗi OCR ước lượng (% âm tiết ngoài từ vựng): trung vị 0,5% với văn bản lấy từ lớp chữ, 1,2% với văn bản OCR.
   - Thư chung Chủ tịch + TGĐ và thư của TGĐ được dùng khi không có thư riêng của Chủ tịch. Người viết khác nhau có thể có giọng điệu khác nhau.
   - OCR có lỗi dấu, và trước #65 bố cục nhiều cột làm các dòng của các cột xen kẽ nhau (nay đọc theo thứ tự cột). Việc đếm từ theo túi từ (bag-of-words) chịu ảnh hưởng ít, nhưng vẫn có sai số đo lường. Sai số này kéo hệ số về 0 (attenuation bias). Tầng AI (mục 4.5) đã chép lại mọi trang phải OCR (189 trang dùng bản AI trong mẫu hiện tại); các hệ số tone VN tăng nhẹ về độ lớn sau lần sửa đầu, khớp với hướng của attenuation bias. Thứ tự đọc theo cột dựa trên khe trắng giữa các khối chữ; trang bố cục tự do (chữ quanh ảnh) vẫn có thể bị sắp sai. Trên 13 trang chuẩn, CER giảm từ 31,3% (Tesseract) xuống 2,9% (LLM đọc ảnh) (mục 4.5); bản chuẩn do Claude chép và người dò lại nên có thể thiên về phía các phương án dùng LLM.
   - Bản AI là do mô hình ngôn ngữ chép lại. Dù đã khóa temperature = 0, bắt chép nguyên văn và loại bản nghi viết lại (độ tương đồng thấp hoặc chất lượng giảm), vẫn không loại trừ hoàn toàn lỗi chép sai hay bỏ sót dòng. Gemini đôi khi từ chối chép nguyên văn (RECITATION, 12 trang trong mẫu hiện tại, chuyển sang chế độ chỉ sửa lỗi ký tự trên bản OCR).
   - 1 BCTN dạng .7z (SHB 2017) không giải nén được.
6. **Dữ liệu giá VN:**
   - Giá điều chỉnh của CafeF có vài bước nhảy nghi chưa điều chỉnh sự kiện doanh nghiệp (MWG −33% ngày 30/08/2021, BSR −41% ngày 20/01/2025, VTP −35% ngày 13/03/2024…). Không bước nhảy nào rơi vào cửa sổ sự kiện; 1 bước (MWG) rơi vào cửa sổ ước lượng của MWG_2021.
   - Lịch sử giá trước khi chuyển sàn được ghép từ endpoint "Lịch sử giá" của CafeF. Tại đoạn chồng lấn, hai nguồn lệch ≤ 0,15% (`data/vn/processed/prices_splice_log.csv`).
7. **Mỹ:**
   - Biến chính chỉ dùng file 10-K chính, không gồm exhibit. Các công ty để MD&A và báo cáo tài chính ở Exhibit 13 (IBM, WFC…) có văn bản ngắn hơn hẳn.
   - V thiếu số cổ phiếu (10 quan sát bị loại khỏi hồi quy).
8. **Kiểm định nhiều lần:** 7 cửa sổ × nhiều mô hình, cộng 4 phân tích bổ sung đăng ký trước (mục 4.8). Kết quả đơn lẻ có ý nghĩa (VN [0,5]) cần được đọc thận trọng: ở bản hiện tại nó qua ngưỡng Bonferroni của 7 cửa sổ (p = 0,0045 so với 0,0071), nhưng p đã dao động quanh ngưỡng qua các bước làm sạch dữ liệu (0,0051 → 0,0077 → 0,0045) và placebo ở mức 10% (p = 0,076, dấu ngược).

---

## 8. Hàm ý

**Nhà đầu tư**
- **Thị trường Mỹ, cổ phiếu lớn:** đọc "độ tiêu cực" của 10-K bằng từ điển **không** tạo ra lợi thế giao dịch ngắn hạn. Thông tin đã vào giá qua thông cáo KQKD. Giá trị của 10-K nằm ở phân tích chiều sâu (rủi ro mới, thay đổi chính sách kế toán), không nằm ở số lượng từ tiêu cực.
- **Thị trường Việt Nam:** thư của lãnh đạo gần như luôn tích cực, nên cần chú ý **độ lệch khỏi mức tích cực thông thường**. Thư nhắc nhiều tới khó khăn, suy giảm, nợ xấu đi kèm CAR thấp hơn trong khoảng 1 tuần sau công bố (hồi quy [0,5]), nhưng không thấy ở [0,3]. Tín hiệu này yếu và chưa vững, nên chỉ dùng để sàng lọc hoặc cảnh báo, không dùng làm chiến lược độc lập.
- **Không dùng từ điển cảm xúc tổng quát** (Harvard GI, VietSentiWordNet) cho văn bản tài chính: 74–92% tín hiệu "tiêu cực" là nhiễu, và có thể cho kết luận sai dấu (M4 ở Mỹ, mức 10%).

**Ngân hàng (thẩm định tín dụng, quản trị rủi ro)**
- Chấm điểm giọng điệu BCTN hoặc thư lãnh đạo bằng **từ điển tài chính tiếng Việt** là cách rẻ để theo dõi hàng loạt khách hàng doanh nghiệp niêm yết. Giai đoạn 2019–2022, tone tiêu cực tăng gần gấp 3 và phản ánh đúng chu kỳ khó khăn. Thước đo này phù hợp làm **chỉ báo cảnh báo sớm**, kết hợp với chỉ tiêu tài chính, hơn là căn cứ ra quyết định.
- Khi áp dụng nội bộ, nên mở rộng và duy trì từ điển theo ngành (ngân hàng: "nợ xấu", "trích lập dự phòng"; bất động sản: "pháp lý dự án"…). Cần duyệt tay như quy trình của LM (2011) và của dự án này, vì khớp nhầm cả một âm tiết như "kiện" có thể làm hỏng toàn bộ một nhóm biến.

---

*Tái lập:* `python run_all.py --market us|vn` (dữ liệu tải về được lưu cache), `pytest -q`, `jupyter nbconvert --execute notebooks/main.ipynb`. Nhật ký sửa đổi đầy đủ: `CHANGELOG_RUN.md`.
