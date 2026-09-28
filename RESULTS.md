# Kết quả – Đồ án 05: Giọng điệu văn bản công bố và phản ứng thị trường (Mỹ + Việt Nam)

**Câu hỏi nghiên cứu:** giọng điệu (tone) của văn bản công bố thông tin tác động tích cực hay tiêu cực lên CAR[T, T+3], tức là văn bản có mang thông tin cho thị trường hay không?

**Tóm tắt**

- **Mỹ (10-K, 2015–2024):** không có bằng chứng cho thấy giọng điệu mang thông tin cho giá.
  - CAR[0,3] không khác 0.
  - Hệ số của tone tiêu cực chuẩn hóa là −0,05 điểm % trên 1 độ lệch chuẩn, không có ý nghĩa.
  - Kết luận giữ nguyên trong mọi phép kiểm định độ vững, với LM tf-idf, MD&A và cả FinBERT.
- **Việt Nam (thông điệp của ban lãnh đạo – chủ yếu Chủ tịch HĐQT – trong BCTN 2016–2025):**
  - Ở cửa sổ chính [0,3], hệ số có dấu âm như kỳ vọng (−0,19 điểm % trên 1 độ lệch chuẩn) nhưng không có ý nghĩa.
  - Ở cửa sổ [0,5] hệ số có ý nghĩa (−0,58 điểm %, p < 0,01), phù hợp với giả thuyết thị trường phản ứng chậm.
  - Bằng chứng này yếu: [0,10] không có ý nghĩa, kết quả [0,5] không qua hiệu chỉnh Bonferroni, và bản thân CAR placebo cũng âm có ý nghĩa.
- **Từ điển tổng quát sai lệch rất nặng trong ngữ cảnh tài chính:**
  - 73,9% số lần Harvard GI gắn nhãn "tiêu cực" rơi vào từ không tiêu cực trong tài chính (TAX, COST, CAPITAL…). Với VietSentiWordNet, tỷ lệ này là 92,9% ("cho", "thương", "bán"…).

> Mọi con số trong tài liệu này lấy từ file trong `outputs/` (tên file ghi trong ngoặc vuông). Mọi thay đổi code, cấu hình và từ điển trong lần chạy này đều ghi trong `CHANGELOG_RUN.md`. Có ba quyết định phương pháp do nhóm duyệt: danh sách LM theo cờ > 0 (#12), mở rộng `fin_vn.csv` (#21), và chấp nhận thông điệp của **ban lãnh đạo** (Chủ tịch HĐQT, TGĐ, thư chung, HĐQT) khi BCTN không có thư riêng của Chủ tịch (#26). Ngoài ra có ba thay đổi về nguồn dữ liệu hoặc ngày sự kiện: dùng ngày ModDate của PDF làm T=0 (#14); nguồn giá VN là CafeF (#15, #19) do vnstock bị PyPI cách ly (quarantine).

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
| Tìm được thông điệp của ban lãnh đạo | 617 |
|   không có thư (`not_found`) | 195 |
|   loại sau kiểm tra tay | 1 |
| Có ngày sự kiện T=0 hợp lệ | 548 |
| Có CAR (≥ 80 phiên ước lượng) | 517 |
| Có CAR[0,3] | 514 |
| Vào hồi quy M2 | 514 |

Tìm được thư ở 617/813 = 75,9% BCTN. Nguyên nhân chính của phần còn lại là nhiều BCTN, đặc biệt loại lập theo mẫu biểu, **không có** thông điệp của lãnh đạo (ANV, EVF, SJS, VGC, VSC, DSE gần như mọi năm). Những BCTN này bị loại, **không** thay bằng "Báo cáo của HĐQT".

Có 50 văn bản được xác định trang bằng tay (`data/vn/processed/manual_pages.csv`, có ghi chú từng ca), dựa trên text từng trang và **ảnh trang PDF** khi OCR hỏng:
- 49 văn bản được trích lại, 1 văn bản bị loại (CTD 2021).
- 5 văn bản bị font mã hóa sai, được ép OCR (`force_ocr`).
- 1 thư có thật nhưng không đọc được chữ (DCM 2025, chữ trên nền màu) vẫn để ngoài mẫu.

Quy tắc chọn văn bản: ưu tiên thư riêng của Chủ tịch HĐQT; nếu BCTN chỉ có thư chung (Chủ tịch + TGĐ), "Thông điệp Ban lãnh đạo" hoặc thư của TGĐ thì dùng thư đó (VCB, NLG, VIC, POW, BSR…).

### 1.2 Độ phủ theo năm

| Năm tài chính | Mỹ: có tone | Mỹ: có CAR[0,3] | VN: có tone | VN: có CAR[0,3] |
|---|---:|---:|---:|---:|
| 2014 | 36 | 36 | – | – |
| 2015 | 49 | 49 | – | – |
| 2016 | 50 | 50 | 52 | 37 |
| 2017 | 51 | 51 | 54 | 40 |
| 2018 | 50 | 50 | 68 | 53 |
| 2019 | 50 | 50 | 58 | 50 |
| 2020 | 49 | 49 | 49 | 37 |
| 2021 | 50 | 50 | 62 | 56 |
| 2022 | 50 | 50 | 44 | 37 |
| 2023 | 51 | 51 | 69 | 58 |
| 2024 | 14 | 14 | 79 | 72 |
| 2025 | – | – | 82 | 74 |

[`outputs/us/coverage_by_year.csv`, `outputs/vn/coverage_by_year.csv`]

Ở Mỹ, "năm" là năm tài chính: 10-K nộp năm 2015 phần lớn là FY2014. Ở VN, độ phủ năm 2020 và 2022 thấp vì CafeF không có tài liệu nào cho năm đó ở khoảng 30 mã. Độ phủ các năm đầu thấp hơn vì nhiều mã chưa niêm yết.

---

## 2. Mục tiêu 1: Biến văn bản thành biến định lượng

Tone = số từ (âm tiết) thuộc từng nhóm / tổng số từ. Mẫu số ở Mỹ là số từ nằm trong LM Master Dictionary, đúng theo phụ lục của LM (2011). Mọi biến tone được winsorize ở mức 1%/99%.

**Thống kê mô tả (%)** [`outputs/us/tone_descriptive.csv`, `outputs/vn/tone_descriptive.csv`]

| Biến | Mỹ: trung bình | Mỹ: độ lệch chuẩn | VN: trung bình | VN: độ lệch chuẩn |
|---|---:|---:|---:|---:|
| fin_neg (tiêu cực, từ điển tài chính) | 1,905 | 0,489 | 0,519 | 0,474 |
| fin_pos (tích cực) | 0,585 | 0,174 | 3,017 | 1,137 |
| fin_unc (bất định) | 1,607 | 0,335 | 0,258 | 0,239 |
| fin_lit (pháp lý) | 1,301 | 0,433 | 0,002 | 0,010 |
| gen_neg (tiêu cực, từ điển tổng quát) | 2,761 | 0,379 | 2,007 | 0,709 |
| fin_net = (Pos−Neg)/(Pos+Neg) | −0,519 | 0,138 | +0,707 | 0,249 |
| finA_neg (MD&A, chỉ Mỹ) | 1,409 | 0,593 | – | – |

- **Mỹ:** `fin_neg` trung bình 1,9% toàn văn, cùng bậc với con số khoảng 1,4% trong LM (2011). Đối chiếu độc lập với LM 10X Summaries trên 40 hồ sơ ngẫu nhiên cùng phạm vi văn bản cho tương quan N_Negative = 0,989 và N_Positive = 0,991, lệch trung vị +3,5% và −1,2% [`outputs/us/validate_vs_lm_fullsub.csv`]. Khâu làm sạch và đếm từ vì vậy tái lập được kết quả của LM. So với số liệu LM trên toàn bộ hồ sơ, tương quan chỉ 0,66 [`outputs/us/validate_vs_lm.csv`], vì LM đếm cả exhibit (EX-13…) còn biến chính của nhóm chỉ dùng file 10-K chính.
- **Việt Nam:** thư của lãnh đạo **rất tích cực**. Tỷ lệ từ tích cực (~3%) gấp khoảng 6 lần tỷ lệ từ tiêu cực (~0,5%), nên `fin_net` = +0,71, trong khi 10-K Mỹ có `fin_net` = −0,52. `fin_lit` gần 0: thư lãnh đạo hầu như không dùng ngôn ngữ pháp lý.

**Xu hướng theo năm (%)** [`outputs/us/tone_by_year.csv`, `outputs/vn/tone_by_year.csv`; hình `fig1_tone_by_year.png`]

| Năm | Mỹ fin_neg | Mỹ finA_neg (MD&A) | VN fin_neg | VN fin_pos | VN fin_net |
|---|---:|---:|---:|---:|---:|
| 2016 | 1,83 | 1,45 | 0,39 | 2,91 | 0,77 |
| 2017 | 1,82 | 1,40 | 0,30 | 2,96 | 0,82 |
| 2018 | 1,81 | 1,31 | 0,33 | 2,98 | 0,81 |
| 2019 | 1,88 | 1,36 | 0,58 | 2,70 | 0,69 |
| **2020** | **1,93** | **1,48** | **0,89** | 2,85 | **0,54** |
| 2021 | 1,97 | 1,38 | 0,81 | 2,66 | 0,54 |
| 2022 | 2,01 | 1,43 | 0,75 | 2,72 | 0,57 |
| 2023 | 2,08 | 1,47 | 0,62 | 2,74 | 0,63 |
| 2024 | 2,17 | 1,22 | 0,44 | 3,57 | 0,77 |
| 2025 | – | – | 0,30 | 3,61 | 0,83 |

**Năm 2020:**
- **Việt Nam:** 2020 là **đỉnh** tỷ lệ từ tiêu cực, 0,89%, gấp khoảng 3 lần năm 2017 (0,30%). `fin_net` cũng xuống đáy (0,54, 2020–2021). Giọng điệu sau đó hồi dần về mức trước COVID vào 2024–2025.
- **Mỹ:** MD&A có đỉnh cục bộ năm 2020 (1,48% so với 1,36% năm 2019). Tuy vậy, toàn văn 10-K cho thấy xu hướng tiêu cực **tăng liên tục** từ 1,81% (2018) lên 2,17% (2024), không đảo chiều sau COVID. Nguyên nhân phù hợp nhất là 10-K ngày càng dài phần rủi ro (Item 1A) và phần pháp lý.

---

## 3. Mục tiêu 2: Từ điển tổng quát sai lệch trong ngữ cảnh tài chính

**Tỷ lệ nhiễu:** trong tổng số lần từ điển tổng quát gắn nhãn "tiêu cực", tỷ lệ rơi vào từ không nằm trong danh sách tiêu cực tài chính:
- Mỹ (Harvard GI IV-4): **73,9%** [`outputs/us/dictionary_comparison.txt`]
- Việt Nam (VietSentiWordNet 1.3.5): **92,9%** [`outputs/vn/dictionary_comparison.txt`]

Tương quan giữa tỷ lệ từ tiêu cực đo bằng hai từ điển chỉ là 0,570 (Mỹ) và 0,440 (VN), nên hai thước đo đo những thứ khác nhau.

**Các từ bị gán sai hay gặp nhất** [`outputs/us/misclassified_general_neg.csv`, `outputs/vn/misclassified_general_neg.csv`; hình `fig2_misclassified.png`]

| Mỹ – từ | % tần suất | Nghĩa trong tài chính | VN – từ | % tần suất | Nghĩa trong văn bản |
|---|---:|---|---|---:|---|
| TAX | 10,93 | thuế (trung tính, mục bắt buộc) | cho | 26,22 | giới từ "cho, đối với" |
| COST | 5,73 | chi phí, giá vốn | thương | 9,09 | âm tiết trong "thương mại", "thương hiệu" |
| CAPITAL | 5,42 | vốn | bán | 5,52 | "bán hàng", "bán lẻ" – hoạt động kinh doanh |
| FOREIGN | 4,74 | nước ngoài (ngoại tệ, thị trường nước ngoài) | giảm | 4,32 | chiều biến động, không phải giọng điệu (LM cũng không xếp "decrease" vào tiêu cực) |
| EXPENSE | 4,60 | chi phí | hạn | 4,11 | "ngắn hạn", "hạn mức", "kỳ hạn" |
| SERVICE | 4,10 | dịch vụ; "debt service" = trả nợ | mạnh mẽ | 4,04 | mang nghĩa **tích cực** trong thư lãnh đạo |
| LIABILITY | 2,45 | nợ phải trả (khoản mục kế toán) | xanh | 2,67 | "tăng trưởng xanh", "tín dụng xanh" |
| BOARD | 1,74 | hội đồng quản trị | vàng | 1,52 | kim loại vàng, "thời kỳ vàng" |
| VICE | 1,43 | "Vice President" (chức danh) | tệ | 1,09 | âm tiết trong "tiền tệ" |

Từ tiêu cực thật cũng có mặt trong top: LOSS (5,19%), AGAINST, ADVERSE ở Mỹ; "khó khăn" (4,61%) ở VN. Nhưng chúng chỉ chiếm phần nhỏ. Ở VN, nhiễu còn bị khuếch đại vì từ điển tổng quát khớp **từng âm tiết** trong từ ghép ("tệ" trong "tiền tệ"). Khớp cụm dài nhất trong `fin_vn.csv` tránh được lỗi này.

**Mô hình đối đầu M4:** đưa cả hai thước đo vào cùng một hồi quy CAR[0,3], với biến kiểm soát và hiệu ứng cố định (FE) [`outputs/*/regression_main.csv`].

| | fin_neg_z (tài chính) | gen_neg_z (tổng quát) | N |
|---|---|---|---:|
| Mỹ | −0,0024 (0,0019) | **+0,0035\*\* (0,0016)** | 470 |
| VN | −0,0022 (0,0023) | +0,0006 (0,0024) | 514 |

Ở Mỹ, từ điển tổng quát cho hệ số **dương** và có ý nghĩa (M3: +0,0025\*; M4: +0,0035\*\*). Nếu đọc theo nghĩa đen thì "văn bản càng tiêu cực, giá càng tăng", điều vô lý về kinh tế. Giải thích hợp lý là `gen_neg` chủ yếu đo mật độ các từ như TAX, COST, CAPITAL, LIABILITY, tức đặc điểm ngành và cấu trúc 10-K chứ không phải tin xấu. Đây chính là loại suy luận sai mà LM (2011) cảnh báo khi dùng từ điển tổng quát. Từ điển tài chính cho dấu âm như kỳ vọng nhưng không có ý nghĩa. Ở VN, cả hai từ điển đều không có ý nghĩa.

---

## 4. Mục tiêu 3: Tone có mang thông tin cho thị trường không?

Mô hình chuẩn (market model) ước lượng trên [−150, −11] phiên, yêu cầu ≥ 80 phiên. Beta trung vị là 0,94 (Mỹ) và 1,06 (VN); |CAR[0,3]| lớn nhất là 31,6% và 25,5%, không có giá trị vô lý [`outputs/*/event_study_diag.csv`]. Với Mỹ, T=0 là `acceptanceDateTime` (nộp sau 16:00 thì tính là phiên sau). Với VN, T=0 là ngày ModDate của PDF BCTN. Mọi biến tone được chuẩn hóa z, nên hệ số chính là mức thay đổi CAR (theo đơn vị thập phân) khi tone tăng 1 độ lệch chuẩn.

### 4.1 CAR[T, T+3] dương hay âm, có khác 0 không?

[`outputs/*/car_tests.csv`]

| | N | CAR[0,3] trung bình | Trung vị | t (p) | t BMP | p Wilcoxon | % CAR > 0 (p sign test) |
|---|---:|---:|---:|---|---:|---:|---|
| Mỹ | 500 | −0,17% | −0,13% | −1,02 (0,31) | −0,99 | 0,19 | 48,2% (0,45) |
| VN | 514 | −0,30% | −0,24% | −1,42 (0,16) | −0,99 | 0,09 | 46,5% (0,12) |

**Ở cả hai thị trường, CAR[0,3] hơi âm nhưng không khác 0**, theo cả kiểm định tham số lẫn phi tham số.

Ở VN, cửa sổ dài hơn cho CAR âm có ý nghĩa: CAR[0,5] = −0,70% (p = 0,006); CAR[0,10] = −0,98% (p = 0,005). Dạng điều chỉnh theo thị trường (market-adjusted) cho CAR[0,5] = −0,52% (p = 0,045). Tuy nhiên, **CAR placebo [−60] cũng âm và có ý nghĩa**: −0,40% (p = 0,034; Wilcoxon p = 0,019). Như vậy một phần độ trôi âm là đặc điểm chung của giai đoạn tháng 3–5 hoặc của mô hình ước lượng, chưa chắc là phản ứng với BCTN.

Ở Mỹ, CAR placebo **dương** và có ý nghĩa (+0,25%, p = 0,02). Lùi 60 phiên từ ngày nộp 10-K (tháng 2) thì rơi vào mùa công bố KQKD quý 3, thời điểm thường có lợi suất bất thường dương.

### 4.2 Có phân hóa theo tone không (T3 − T1)?

Chia mẫu thành ba nhóm bằng nhau theo `fin_net` [`outputs/*/car_by_tone.csv`; hình `fig3_caar_by_tone.png`]:

| | T1 Tiêu cực | T2 Trung tính | T3 Tích cực | **T3 − T1 (p Welch)** |
|---|---|---|---|---|
| Mỹ | −0,06% (p 0,84) | −0,15% (p 0,53) | −0,26% (p 0,20) | **−0,21 điểm % (0,56)** |
| VN | −0,68% (p 0,081) | −0,23% (p 0,46) | −0,04% (p 0,90) | **+0,64 điểm % (0,22)** |

- **Mỹ:** không có phân hóa; chênh lệch còn ngược dấu kỳ vọng.
- **VN:** đúng hướng kỳ vọng. Nhóm tone tiêu cực nhất có CAR[0,3] −0,68%, có ý nghĩa ở mức 10%, và đường CAAR tiếp tục đi xuống tới khoảng −2,2% ở T+6 (hình 3). Tuy vậy, chênh lệch T3 − T1 chưa đạt mức ý nghĩa thống kê.

### 4.3 Hồi quy: hệ số fin_neg_z và độ lớn kinh tế

OLS gộp, sai số chuẩn cluster theo mã, FE năm (Mỹ thêm FE ngành SIC 2 chữ số). Biến kiểm soát:
- **Mỹ:** log vốn hóa, log B/M, log turnover, pre_alpha, log độ dài văn bản.
- **VN:** log GTGD, pre_ret, log độ dài, dummy VN30, beta.

[`outputs/*/regression_main.csv`, `outputs/*/economic_magnitude.csv`]

| Mô hình | Mỹ: hệ số (SE) | Mỹ: Δ CAR khi +1 SD | VN: hệ số (SE) | VN: Δ CAR khi +1 SD |
|---|---|---:|---|---:|
| **M2 fin_neg_z** | −0,0005 (0,0016) | **−0,05 điểm %** | −0,0019 (0,0020) | **−0,19 điểm %** |
| M5 fin_net_z | −0,0009 (0,0013) | −0,09 | +0,0020 (0,0024) | +0,20 |
| M5 fin_unc_z | −0,0019 (0,0026) | −0,19 | −0,0029 (0,0021) | −0,29 |
| M6 fin_neg_tfidf_z (LM eq. 1) | −0,0013 (0,0039) | −0,13 | −0,0007 (0,0022) | −0,07 |
| M7 finA_neg_z (MD&A) | −0,0006 (0,0021) | −0,06 | – | – |
| M8 finbert_net_z (FinBERT) | −0,0015 (0,0013) | −0,15 | – | – |

1 độ lệch chuẩn của `fin_neg` tương ứng 0,49 điểm % số từ ở Mỹ và 0,47 điểm % số âm tiết ở VN [`outputs/*/tone_descriptive.csv`].

**Câu trả lời trực tiếp:**
- **Mỹ:** tăng 1 độ lệch chuẩn tone tiêu cực làm CAR[0,3] thay đổi −0,05 điểm %. Mức này **không khác 0** về thống kê và rất nhỏ về kinh tế: khoảng 1/75 độ lệch chuẩn của CAR[0,3], vốn là 3,72% [`outputs/us/event_study_diag.csv`]. Không mô hình nào, kể cả FinBERT (tương quan với `fin_net` là 0,44 [`outputs/us/event_study_diag.csv`]), tìm thấy thông tin trong giọng điệu 10-K.
- **VN:** tăng 1 độ lệch chuẩn tone tiêu cực làm CAR[0,3] giảm 0,19 điểm %, khoảng 1/26 độ lệch chuẩn của CAR[0,3] (4,85%). Kết quả đúng dấu kỳ vọng nhưng **không có ý nghĩa** (t ≈ −0,9).

**Fama–MacBeth** [`outputs/*/regression_fama_macbeth.csv`]:
- Mỹ: `fin_neg_z` = −0,0011 (t = −0,98), trên 10 kỳ cắt ngang. Chỉ quý 1 mỗi năm đủ quan sát, vì 10-K tập trung nộp vào tháng 2–3.
- VN: `fin_neg_z` = −0,0008 (t = −0,35), trên 10 năm.

Cả hai đều không có ý nghĩa.

### 4.4 Placebo và độ vững

Hệ số `fin_neg_z`, dùng cùng biến kiểm soát và FE [`outputs/*/regression_robustness.csv`]:

| Biến phụ thuộc | Mỹ | VN |
|---|---|---|
| CAR market-adjusted [0,3] | +0,0005 (0,0018) | −0,0013 (0,0019) |
| BHAR[0,3] (LM 2011) | +0,0006 (0,0018) | −0,0016 (0,0019) |
| **Placebo −60 phiên** | +0,0008 (0,0012) | +0,0021 (0,0016) |
| CAR[0,1] | +0,0002 (0,0014) | +0,0010 (0,0013) |
| CAR[−1,1] | +0,0024 (0,0018) | +0,0013 (0,0016) |
| CAR[0,5] | −0,0005 (0,0018) | **−0,0058\*\*\* (0,0022)** |
| CAR[0,10] | −0,0019 (0,0025) | −0,0044 (0,0031) |

- **Placebo** không có ý nghĩa ở cả hai thị trường, đúng như mong đợi.
- **VN:** kết quả duy nhất có ý nghĩa là **CAR[0,5]**. Tăng 1 độ lệch chuẩn tone tiêu cực đi kèm CAR[0,5] thấp hơn 0,58 điểm % (t ≈ −2,6, p ≈ 0,008). Điều này khớp với hình 3, nơi đường nhóm tiêu cực tách ra rõ nhất ở T+3 đến T+6. Bằng chứng vẫn còn yếu, vì [0,10] không có ý nghĩa (−0,44 điểm %, p ≈ 0,16) và đây là 1 trong 7 cửa sổ được kiểm định. Với hiệu chỉnh Bonferroni cho 7 cửa sổ (α = 0,05/7 ≈ 0,007), kết quả **không qua** ngưỡng.
- **Mỹ, kiểm tra bổ sung** (không thuộc thiết kế gốc) [`outputs/us/earnings_overlap.csv`, `outputs/us/regression_excl_earnings.csv`]:
  - 93/500 hồ sơ 10-K (18,6%) được nộp trong vòng ±3 ngày quanh 8-K công bố KQKD (mục 2.02). Nhóm này có |CAR[0,3]| trung bình 4,65%, so với 1,65% ở nhóm còn lại.
  - Sau khi loại các hồ sơ này, `fin_neg_z` = +0,0011 (0,0017), vẫn không có ý nghĩa.

---

## 5. So sánh Mỹ và Việt Nam

| Khía cạnh | Mỹ | Việt Nam |
|---|---|---|
| Giọng điệu văn bản | Tiêu cực, mang tính pháp lý (fin_net −0,52) | Rất tích cực, mang tính quan hệ cổ đông (fin_net +0,71) |
| CAR[0,3] | ≈ 0 | ≈ 0 (âm nhẹ) |
| Tone → CAR[0,3] | Không | Đúng dấu, không có ý nghĩa |
| Tone → CAR dài hơn | Không | Có ý nghĩa ở [0,5] (không qua Bonferroni), chưa vững |

**Lập luận kinh tế:**
1. **Hiệu quả thông tin và thời điểm:**
   - **Mỹ:** 10-K ra 1–4 tuần **sau** thông cáo KQKD và earnings call. Khi 10-K được nộp, phần lớn thông tin đã vào giá, nên giọng điệu gần như không còn gì mới. Mẫu gồm 50 công ty vốn hóa lớn nhất, được theo dõi sát nhất, càng làm tăng hiệu quả này. Tone 10-K còn phản ánh ngôn ngữ rủi ro soạn theo khuôn mẫu pháp lý, ít thay đổi giữa các năm. Kết quả này khác LM (2011), vốn dùng mẫu 1994–2008 với toàn bộ công ty CRSP, gồm nhiều công ty nhỏ ít được theo dõi.
   - **VN:** BCTN và thư của lãnh đạo là kênh truyền đạt quan điểm của ban lãnh đạo tới nhà đầu tư cá nhân, nhóm chiếm phần lớn giao dịch. Mức độ phân tích và đưa tin về doanh nghiệp thấp hơn Mỹ, nên văn bản có nhiều khả năng còn nội dung mới.
2. **Biên độ giá và thanh khoản:** HOSE giới hạn biên độ ±7%/phiên (UPCOM ±15%). Trong cửa sổ ước lượng, tỷ lệ phiên lợi suất bằng 0 có trung vị 7,9% (p90 = 17,1%), so với 0% ở Mỹ [`outputs/*/event_study_diag.csv`]. Thông tin vì vậy vào giá **chậm** hơn, phù hợp với việc phản ứng chỉ hiện rõ ở [0,5]. `log_tradeval` có hệ số âm ở hầu hết các mô hình VN: cổ phiếu thanh khoản thấp phản ứng khác cổ phiếu thanh khoản cao.
3. **Chất lượng công bố thông tin:** thư lãnh đạo ở VN thiên về "tô hồng": từ tích cực gấp khoảng 6 lần từ tiêu cực. Vì vậy **mức độ tiêu cực tương đối**, tức việc dám nhắc tới "khó khăn", "suy giảm", là tín hiệu hiếm và có thể mang thông tin. Đây là lập luận tín hiệu tốn kém, tương tự tin xấu trong môi trường ít minh bạch. Điều này khớp với việc chỉ nhóm tone tiêu cực nhất (T1) có CAR âm đáng kể.
4. **T=0 kém chính xác ở VN:** nếu ngày ModDate sớm hơn ngày đăng thực tế vài ngày, phản ứng thật sẽ lệch sang cửa sổ muộn hơn. Đây là một cách giải thích thay thế, **thuần kỹ thuật**, cho việc tác động chỉ xuất hiện ở [0,5].

---

## 6. Kiểm định giả định

[`outputs/*/assumption_tests.csv`, tính trên M2]

| Kiểm định | Mỹ | VN | Kết luận và xử lý |
|---|---:|---:|---|
| Breusch–Pagan (p) | 0,000 | 0,0009 | Phương sai sai số thay đổi → toàn bộ hồi quy dùng **sai số chuẩn cluster theo mã** (vững với phương sai thay đổi và tương quan trong cùng công ty); Fama–MacBeth dùng Newey–West |
| Jarque–Bera (p) | 0,000 | 0,000 | Phần dư không chuẩn (đuôi dày, điển hình của lợi suất) → **winsorize 1%/99%** cho CAR và các biến tone; cỡ mẫu 470–514 đủ lớn để suy luận tiệm cận; bổ sung kiểm định **phi tham số** (Wilcoxon, sign test) và t BMP (chuẩn hóa theo phương sai ước lượng) |
| VIF lớn nhất | 2,98 (log_turn); fin_neg_z 2,86 | 2,92 (log_tradeval); fin_neg_z 1,24 | < 5 → không có đa cộng tuyến đáng lo |
| corr(fin_neg, gen_neg) | 0,570 | 0,452 | Đủ thấp để M4 tách được tác động riêng của hai thước đo |

---

## 7. Hạn chế

1. **Survivorship bias:**
   - Mỹ: 50 công ty lớn đang niêm yết.
   - VN: rổ VN30/VN100 **hiện hành** (kỳ 7/2026) dùng cho mọi năm từ 2016; các công ty bị hủy niêm yết hoặc rơi khỏi rổ không có trong mẫu.
   - Mẫu Mỹ lại gồm những công ty được phân tích nhiều nhất, nên thiên về kết quả "không có phản ứng".
2. **Ngày sự kiện ở VN là ước lượng** [`outputs/vn/event_date_check.csv`]:
   - CafeF không còn tin công bố thông tin về BCTN, CDN không gửi Last-Modified, và không có tài liệu ĐHĐCĐ. T=0 vì vậy là ngày ModDate của PDF (548/617 thư).
   - 94,7% ngày T=0 rơi vào tháng 3–5. Ngày ĐHĐCĐ thường niên đến sau T=0 với trung vị 13 ngày (p10 = 3, p90 = 63).
   - ModDate là ngày file được hoàn thiện, nên ngày đăng thật có thể **muộn hơn** vài ngày.
   - 69 thư không có ModDate hợp lệ bị loại khỏi phần nghiên cứu sự kiện.
3. **Từ điển tiếng Việt do nhóm tự xây:**
   - `fin_vn.csv` gồm 201 cụm; bổ sung 9 cụm và bỏ từ đơn "kiện" qua duyệt tay từ `candidate_terms.csv` (CHANGELOG #21).
   - Chưa được kiểm định độc lập kiểu đối chiếu với LM 10X Summaries như ở Mỹ.
   - Chưa tách từ tiếng Việt, chỉ khớp cụm dài nhất theo âm tiết.
4. **Sự kiện trùng thời điểm:**
   - **Mỹ:** 18,6% hồ sơ 10-K trùng KQKD. Đã kiểm tra: loại chúng không đổi kết luận.
   - **VN:** BCTN ra sát ĐHĐCĐ (trung vị 13 ngày) và mùa KQKD quý 1 (tháng 4). Cửa sổ [0,5] và [0,10] có thể lẫn các tin này. CAR placebo VN cũng âm và có ý nghĩa.
5. **Trích văn bản ở VN:**
   - Mẫu QC 10% (`data/vn/processed/qc_sample.csv`, 59 văn bản, đối chiếu đầu/cuối văn bản và ảnh trang): 49 đúng (10 trong số đó lệch biên nhỏ), 10 sai trang. 9 văn bản sai đã sửa trang, 1 đã loại. Tỷ lệ sai trang khoảng 17% gợi ý phần chưa kiểm tra (khoảng 90% mẫu) cũng có tỷ lệ tương tự, chủ yếu là lẫn trang mục lục.
   - Lỗi OCR ước lượng (% âm tiết ngoài từ vựng): trung vị 0,5% với văn bản lấy từ lớp chữ, 1,2% với văn bản OCR.
   - Thư chung Chủ tịch + TGĐ và thư của TGĐ được dùng khi không có thư riêng của Chủ tịch. Người viết khác nhau có thể có giọng điệu khác nhau.
   - OCR có lỗi dấu, và bố cục nhiều cột làm đảo thứ tự câu. Việc đếm từ theo túi từ (bag-of-words) chịu ảnh hưởng ít, nhưng vẫn có sai số đo lường. Sai số này kéo hệ số về 0 (attenuation bias).
   - 1 BCTN dạng .7z (SHB 2017) không giải nén được.
6. **Dữ liệu giá VN:**
   - Giá điều chỉnh của CafeF có vài bước nhảy nghi chưa điều chỉnh sự kiện doanh nghiệp (MWG −33% ngày 30/08/2021, BSR −41% ngày 20/01/2025, VTP −35% ngày 13/03/2024…). Không bước nhảy nào rơi vào cửa sổ sự kiện; 1 bước (MWG) rơi vào cửa sổ ước lượng của MWG_2021.
   - Lịch sử giá trước khi chuyển sàn được ghép từ endpoint "Lịch sử giá" của CafeF. Tại đoạn chồng lấn, hai nguồn lệch ≤ 0,15% (`data/vn/processed/prices_splice_log.csv`).
7. **Mỹ:**
   - Biến chính chỉ dùng file 10-K chính, không gồm exhibit. Các công ty để MD&A và báo cáo tài chính ở Exhibit 13 (IBM, WFC…) có văn bản ngắn hơn hẳn.
   - V thiếu số cổ phiếu (10 quan sát bị loại khỏi hồi quy).
8. **Kiểm định nhiều lần:** 7 cửa sổ × nhiều mô hình. Kết quả đơn lẻ có ý nghĩa (VN [0,5]) cần được đọc thận trọng.

---

## 8. Hàm ý

**Nhà đầu tư**
- **Thị trường Mỹ, cổ phiếu lớn:** đọc "độ tiêu cực" của 10-K bằng từ điển **không** tạo ra lợi thế giao dịch ngắn hạn. Thông tin đã vào giá qua thông cáo KQKD. Giá trị của 10-K nằm ở phân tích chiều sâu (rủi ro mới, thay đổi chính sách kế toán), không nằm ở số lượng từ tiêu cực.
- **Thị trường Việt Nam:** thư của lãnh đạo gần như luôn tích cực, nên cần chú ý **độ lệch khỏi mức tích cực thông thường**. Thư nào nhắc nhiều tới khó khăn, suy giảm, nợ xấu (nhóm T1) đi kèm CAR âm trong khoảng 1 tuần sau công bố. Tín hiệu này yếu và chưa vững, nên chỉ dùng để sàng lọc hoặc cảnh báo, không dùng làm chiến lược độc lập.
- **Không dùng từ điển cảm xúc tổng quát** (Harvard GI, VietSentiWordNet) cho văn bản tài chính: 74–93% tín hiệu "tiêu cực" là nhiễu, và có thể cho kết luận sai dấu (M3/M4 ở Mỹ).

**Ngân hàng (thẩm định tín dụng, quản trị rủi ro)**
- Chấm điểm giọng điệu BCTN hoặc thư lãnh đạo bằng **từ điển tài chính tiếng Việt** là cách rẻ để theo dõi hàng loạt khách hàng doanh nghiệp niêm yết. Giai đoạn 2019–2022, tone tiêu cực tăng gần gấp 3 và phản ánh đúng chu kỳ khó khăn. Thước đo này phù hợp làm **chỉ báo cảnh báo sớm**, kết hợp với chỉ tiêu tài chính, hơn là căn cứ ra quyết định.
- Khi áp dụng nội bộ, nên mở rộng và duy trì từ điển theo ngành (ngân hàng: "nợ xấu", "trích lập dự phòng"; bất động sản: "pháp lý dự án"…). Cần duyệt tay như quy trình của LM (2011) và của dự án này, vì khớp nhầm cả một âm tiết như "kiện" có thể làm hỏng toàn bộ một nhóm biến.

---

*Tái lập:* `python run_all.py --market us|vn` (dữ liệu tải về được lưu cache), `pytest -q`, `jupyter nbconvert --execute notebooks/main.ipynb`. Nhật ký sửa đổi đầy đủ: `CHANGELOG_RUN.md`.
