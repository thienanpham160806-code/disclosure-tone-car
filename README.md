# Đồ án 05 – Phân tích văn bản báo cáo tài chính (Mỹ + Việt Nam)

**Câu hỏi nghiên cứu:** Giọng điệu văn bản công bố có tác động **tích cực hay tiêu cực** lên lợi suất bất thường
tích lũy **CAR[T, T+3]** quanh ngày công bố không, tức là văn bản có mang thông tin cho thị trường không?

> **Mới làm quen với đồ án? Đọc [`HUONG_DAN_CHAY.md`](HUONG_DAN_CHAY.md)** – hướng dẫn từng bước từ cài đặt tới chạy lại toàn bộ kết quả.

| | Mỹ | Việt Nam |
|---|---|---|
| Văn bản | 10-K (toàn văn; MD&A để kiểm tra độ vững) | Thông điệp của ban lãnh đạo trong BCTN (ưu tiên thư Chủ tịch HĐQT; nếu không có thì thư chung Chủ tịch + TGĐ / Ban lãnh đạo / TGĐ) |
| Mẫu | 50 công ty lớn, 10-K nộp 2015–2024 (~500) | Toàn bộ VN30 + VN100, BCTN 2016–2025 |
| Nguồn | SEC EDGAR submissions API + XBRL companyfacts, yfinance | CafeF (PDF BCTN, giá điều chỉnh), `data/vn/tickers.csv` |
| Từ điển tài chính / tổng quát | Loughran–McDonald / Harvard GI IV-4 | `dict/fin_vn.csv` (Việt hóa LM) / VietSentiWordNet |
| T=0 | `acceptanceDateTime` (sau 16:00 ET → phiên sau) | Tin CBTT → Last-Modified → **ModDate trong PDF** (nguồn thực tế dùng được) → tài liệu ĐHĐCĐ |

## Cài đặt
```bash
py -3.11 -m venv .venv && .venv\Scriptsctivate        # (macOS/Linux: python3.11 -m venv .venv && source .venv/bin/activate)
pip install -r requirements.txt
```
1. **Email cho SEC** (bắt buộc trong User-Agent): KHÔNG sửa `config.yaml` (repo công khai). Đặt biến môi trường
   `CONTACT_EMAIL=...` hoặc tạo `config.local.yaml` (đã có trong `.gitignore`) với dòng `contact_email: "..."`.
2. Tải **Loughran–McDonald Master Dictionary** (CSV) tại https://sraf.nd.edu/loughranmcdonald-master-dictionary/
   rồi đặt vào `dict/`. Nên tải thêm **LM 10X Summaries** để chạy bước đối chiếu `u04`. (Link là Google Drive → tải tay.)
3. Nhánh VN cần **Tesseract + gói tiếng Việt** (chỉ dùng cho PDF scan):
   - Windows: bản UB-Mannheim (`winget install UB-Mannheim.TesseractOCR`), tick *Vietnamese*. Không có quyền admin:
     chép `eng/osd.traineddata` + `vie.traineddata` (github.com/tesseract-ocr/tessdata) vào một thư mục riêng, đặt
     `TESSDATA_PREFIX` trỏ tới đó và thêm `C:\Program Files\Tesseract-OCR` vào `PATH`.
   - macOS: `brew install tesseract tesseract-lang`
   - Ubuntu: `sudo apt install tesseract-ocr tesseract-ocr-vie`
4. **vnstock** (ngày 27/09/2026 PyPI để dự án ở trạng thái *quarantined*, không cài được) → pipeline không bắt buộc
   vnstock: tự cung cấp `data/vn/tickers.csv` (`ticker,group`) và dùng `price_source: cafef_hybrid` (mặc định):
   tải 2 file "Đã điều chỉnh – Upto" tại https://cafef.vn/du-lieu/du-lieu-download.chn (`CafeF.SolieuGD.Upto*.zip`,
   `CafeF.Index.Upto*.zip`), giải nén vào `data/vn/raw/prices_cafef/`; lịch sử trước khi chuyển sàn được tự bù từ
   trang "Lịch sử giá" của CafeF. Xem `CHANGELOG_RUN.md` #15, #19.
5. Tùy chọn FinBERT: `pip install torch --index-url https://download.pytorch.org/whl/cpu` + `pip install transformers`.
6. Windows: đặt `PYTHONUTF8=1` (console mặc định cp1252 không in được tiếng Việt).

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

## Mẫu thực tế và thời gian chạy (lần chạy 27–28/09/2026)
Kết quả đầy đủ: **`RESULTS.md`**; nhật ký sửa code/cấu hình/từ điển: **`CHANGELOG_RUN.md`**.

| | Mỹ | Việt Nam |
|---|---|---|
| Văn bản | 500 10-K (50 công ty × 10 năm nộp 2015–2024), 457 có MD&A | 813 BCTN (mã–năm) → 617 thông điệp ban lãnh đạo |
| Có CAR[0,3] | 500 | 514 (548 có ngày T=0 = ModDate PDF) |
| Hồi quy chính | N = 470 | N = 514 |

Thời gian (laptop 12 luồng, Windows; bước tải phụ thuộc mạng, lần chạy lại dùng cache):

| Bước | Mỹ | | Bước | Việt Nam |
|---|---|---|---|---|
| u01_edgar | ~5 phút (cache: 10 giây) | | v01_universe | < 1 giây (`tickers.csv` có sẵn) |
| u02_text | ~1 phút | | v02_crawl_bctn | ~4 giờ (≈ 8 GB PDF; 3,5 giờ + 40 phút tải bù từ host cũ) |
| u03_market | ~15 giây | | v03_extract_letter | ~3 giờ (OCR, 4 tiến trình) + rà trang thủ công |
| a01_tone | ~1 phút | | v04_prices | ~2 giờ (55 mã cần bù lịch sử từ web; cache: 2 phút) |
| u04_validate_lm | ~1,5 phút (40 hồ sơ .txt đầy đủ) | | a01_tone | ~15 giây |
| a02_event / a03 / a04 / a06 | ~20 giây / 2 / 2 / 5 giây | | a02 / a03 / a04 / a06 | ~20 giây / 2 / 2 / 5 giây |
| a05_finbert (tùy chọn, CPU, 100 câu/văn bản) | nhiều giờ (lần chạy này ~14 giờ, tranh CPU với OCR) | | notebook `main.ipynb` | ~2 phút (cả 2 thị trường) |

## Cấu trúc
```
src/
  textkit/   us_clean.py (làm sạch 10-K, MD&A, Item 1A) · dictionaries.py · scoring.py (EN/VI, tf-idf)
  us/        edgar_client.py · u01_edgar · u02_text · u03_market · u04_validate_lm
  vn/        http.py · v01_universe · v02_crawl_bctn · v03_extract_letter · v04_prices
  analysis/  a01_tone · a02_event · a03_regress · a04_figures · a05_finbert (tùy chọn) · a06_summary
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
1. `data/vn/processed/qc_sample.csv`: đối chiếu 10% văn bản với PDF gốc (đã điền: 49/59 đúng, 10 sai đã sửa).
2. File có `flag = not_found` hoặc cắt sai trang: ghi vào `data/vn/processed/manual_pages.csv`
   (`ticker,year,start_page,end_page,force_ocr,ghi_chu`), rồi chạy `python src/vn/v03_extract_letter.py --manual`.
   - `force_ocr = 1`: bỏ lớp chữ của PDF (font mã hóa sai) và OCR lại trang.
   - `start_page = 0`: xác nhận KHÔNG có thư của ban lãnh đạo → loại văn bản (`flag = excluded_manual`).
   - `python src/vn/v03_extract_letter.py --new`: chỉ trích các BCTN mới (chưa có trong `letters_meta.csv`),
     giữ nguyên kết quả cũ và file QC đã điền.
3. `outputs/vn/candidate_terms.csv`: gán nhóm cho các cụm từ hay gặp, chép vào `dict/fin_vn.csv`, rồi chạy lại `--from 5`.

## Hạn chế cần ghi trong báo cáo
- Survivorship bias: danh sách mã là các công ty đang niêm yết.
- Ngày công bố BCTN ở VN là ước lượng; phải kiểm tra `event_src`.
- Biên độ giá và thanh khoản thấp ở VN có thể làm phản ứng giá bị trễ, nên xem thêm cửa sổ [0,5] và [0,10].
- Từ điển tiếng Việt do nhóm tự xây, cần mô tả quy trình duyệt từ.

Nguồn code và giấy phép: xem **CREDITS.md**.
