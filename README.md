# Đề án 05 – Phân tích văn bản báo cáo tài chính (Mỹ + Việt Nam)

**Câu hỏi nghiên cứu:** Giọng điệu văn bản công bố có tác động **tích cực hay tiêu cực** lên lợi suất bất thường
tích lũy **CAR[T, T+3]** quanh ngày công bố không, tức là văn bản có mang thông tin cho thị trường không?

| | Mỹ | Việt Nam |
|---|---|---|
| Văn bản | 10-K (toàn văn; MD&A để kiểm tra độ vững) | Thông điệp Chủ tịch HĐQT trong BCTN |
| Mẫu | 50 công ty lớn, 10-K nộp 2015–2024 (~500) | Toàn bộ VN30 + VN100, BCTN 2016–2025 |
| Nguồn | SEC EDGAR submissions API + XBRL companyfacts, yfinance | CafeF (PDF BCTN + tin công bố thông tin), vnstock |
| Từ điển tài chính / tổng quát | Loughran–McDonald / Harvard GI IV-4 | `dict/fin_vn.csv` (Việt hóa LM) / VietSentiWordNet |
| T=0 | `acceptanceDateTime` (sau 16:00 ET → phiên sau) | Tin CBTT → Last-Modified PDF → tài liệu ĐHĐCĐ |

## Cài đặt
```bash
pip install -r requirements.txt
```
1. Sửa `contact_email` trong `config.yaml`. SEC bắt buộc User-Agent có email.
2. Tải **Loughran–McDonald Master Dictionary** (CSV) tại https://sraf.nd.edu/loughranmcdonald-master-dictionary/
   rồi đặt vào `dict/`. Nên tải thêm **LM 10X Summaries** để chạy bước đối chiếu `u04`.
3. Nhánh VN cần **Tesseract + gói tiếng Việt** (chỉ dùng cho PDF scan):
   - Windows: bản UB-Mannheim, tick *Vietnamese*
   - macOS: `brew install tesseract tesseract-lang`
   - Ubuntu: `sudo apt install tesseract-ocr tesseract-ocr-vie`

## Chạy
```bash
python run_all.py --market us            # Mỹ: tải → làm sạch → giá/XBRL → tone → đối chiếu LM → CAR → hồi quy → hình
python run_all.py --market vn            # VN: rổ mã → crawl BCTN → trích thông điệp → giá → tone → CAR → hồi quy → hình
python run_all.py --market both
python run_all.py --market vn --from 5   # chạy lại từ bước 5 (dữ liệu tải về đã được cache)
python run_all.py --market us --only a03 # chạy riêng một bước
pytest -q                                # kiểm thử các khối lõi (không cần mạng)
jupyter notebook notebooks/main.ipynb    # chạy lại phân tích và xem toàn bộ bảng, hình
```
Tùy chọn: `python src/analysis/a05_finbert.py --market us` chấm tone bằng FinBERT để so với từ điển
(cần `transformers` và `torch`). Bước a03 sẽ tự thêm mô hình M8.

## Cấu trúc
```
src/
  textkit/   us_clean.py (làm sạch 10-K, MD&A, Item 1A) · dictionaries.py · scoring.py (EN/VI, tf-idf)
  us/        edgar_client.py · u01_edgar · u02_text · u03_market · u04_validate_lm
  vn/        http.py · v01_universe · v02_crawl_bctn · v03_extract_letter · v04_prices
  analysis/  a01_tone · a02_event · a03_regress · a04_figures · a05_finbert (tùy chọn)
data/<us|vn>/{raw,interim,processed}/     outputs/<us|vn>/   (bảng .csv + hình .png)
```
Mọi bước phân tích đọc cùng một bảng chuẩn `data/<mkt>/processed/docs.csv`
(doc_id, ticker, year, event_date, after_close, lang, text_main, text_alt, industry, group, flag).
Muốn thêm thị trường mới chỉ cần viết bước tạo `docs.csv` và `prices.csv.gz`.

## Đầu ra theo mục tiêu
| Mục tiêu | File |
|---|---|
| 1. Biến văn bản thành biến định lượng | `tone_panel.csv`, `fig1_tone_by_year.png` |
| 2. Từ điển tổng quát sai lệch | `misclassified_general_neg.csv`, `dictionary_comparison.txt`, `fig2_misclassified.png`, cột M4 trong `regression_main.csv` |
| 3. Tone có mang thông tin | `car_tests.csv`, `car_by_tone.csv`, `regression_main.csv`, `regression_fama_macbeth.csv`, `fig3_caar_by_tone.png` |
| Kiểm định giả định, đối chứng | `assumption_tests.csv`, `regression_robustness.csv` (market-adjusted, BHAR, placebo, các cửa sổ khác) |
| Tái lập, QC | `validate_vs_lm.csv` (Mỹ), `qc_mdna_sample.csv` (Mỹ), `qc_sample.csv` (VN), `pytest` |

## Human-in-the-loop (nhánh VN)
1. `data/vn/processed/qc_sample.csv`: đối chiếu 10% văn bản với PDF gốc.
2. File có `flag = not_found`: ghi trang vào `data/vn/processed/manual_pages.csv` (`ticker,year,start_page,end_page`),
   rồi chạy `python src/vn/v03_extract_letter.py --manual`.
3. `outputs/vn/candidate_terms.csv`: gán nhóm cho các cụm từ hay gặp, chép vào `dict/fin_vn.csv`, rồi chạy lại `--from 5`.

## Hạn chế cần ghi trong báo cáo
- Survivorship bias: danh sách mã là các công ty đang niêm yết.
- Ngày công bố BCTN ở VN là ước lượng; phải kiểm tra `event_src`.
- Biên độ giá và thanh khoản thấp ở VN có thể làm phản ứng giá bị trễ, nên xem thêm cửa sổ [0,5] và [0,10].
- Từ điển tiếng Việt do nhóm tự xây, cần mô tả quy trình duyệt từ.

Nguồn code và giấy phép: xem **CREDITS.md**.
