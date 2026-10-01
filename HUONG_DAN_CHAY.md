# Hướng dẫn chạy Đồ án 05

Tài liệu này dành cho các thành viên nhóm cần chạy lại đồ án trên máy mình. Máy mẫu dùng **Windows 10/11**; câu lệnh cho macOS/Linux ghi kèm khi khác. Kết quả của lần chạy gốc nằm ở `RESULTS.md`. Mọi thay đổi so với code ban đầu được ghi trong `CHANGELOG_RUN.md`.

Có **hai cách chạy**, bạn chọn một:

| | Cách A – Chạy nhanh | Cách B – Chạy lại toàn bộ |
|---|---|---|
| Làm gì | Tính lại sự kiện, hồi quy, hình và bảng từ dữ liệu đã xử lý có sẵn trong repo | Tải lại 10-K, BCTN, giá; làm sạch văn bản; trích thư; tính tone; rồi phân tích |
| Thời gian | Khoảng 2–5 phút | Khoảng 10–12 giờ, phần lớn là tải BCTN (~4 giờ), OCR (~3 giờ) và tải giá VN (~2 giờ) |
| Cần mạng | Không | Có (SEC, Yahoo Finance, CafeF) |
| Dùng khi | Muốn xem hoặc kiểm tra kết quả, sửa hình, thử mô hình hồi quy khác | Muốn tái lập từ đầu hoặc đổi mẫu, từ điển, cách trích văn bản |

---

## 1. Chuẩn bị máy (làm một lần)

1. **Python 3.11**: tải tại https://www.python.org/downloads/, khi cài nhớ tick *Add python.exe to PATH*. Kiểm tra bằng `py -3.11 --version`.
2. **Git**: https://git-scm.com/download/win.
3. **Tesseract OCR + tiếng Việt**. Chỉ cần cho Cách B, nhánh Việt Nam.
   - Cài bằng `winget install UB-Mannheim.TesseractOCR`, hoặc tải bộ cài UB-Mannheim và tick *Vietnamese* khi cài.
   - Kiểm tra: `"C:\Program Files\Tesseract-OCR\tesseract.exe" --list-langs` phải có dòng `vie`.
   - Nếu **không có quyền admin** để thêm gói `vie`:
     - Tạo thư mục `C:\Users\<tên bạn>\tessdata`.
     - Chép `eng.traineddata`, `osd.traineddata` từ `C:\Program Files\Tesseract-OCR\tessdata\` vào đó.
     - Tải thêm `vie.traineddata` từ https://github.com/tesseract-ocr/tessdata vào cùng thư mục.
     - Khi chạy, đặt `TESSDATA_PREFIX` trỏ tới thư mục này (xem mục 4).
   - macOS: `brew install tesseract tesseract-lang`. Ubuntu: `sudo apt install tesseract-ocr tesseract-ocr-vie`.
4. **Ổ đĩa trống**: Cách B cần khoảng 15 GB (riêng PDF BCTN khoảng 8 GB).
5. **Tắt chế độ ngủ** khi chạy Cách B: Settings → System → Power → Sleep: *Never*. Máy ngủ giữa chừng sẽ làm các bước tải kéo dài hàng giờ.

## 2. Lấy code và cài thư viện

Mở **PowerShell** trong thư mục bạn muốn để đồ án:

```powershell
git clone https://github.com/thienanpham160806-code/disclosure-tone-car.git
cd disclosure-tone-car
git checkout results          # nhánh chứa kết quả; bỏ qua dòng này nếu đã merge vào main

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1   # macOS/Linux: source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
```

Nếu PowerShell báo lỗi *running scripts is disabled*, chạy một lần lệnh `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` rồi activate lại.

`vnstock` **không** nằm trong danh sách cài: từ 27/09/2026 PyPI cách ly (quarantine) gói này, và pipeline không cần nó (danh sách mã có sẵn trong `data/vn/tickers.csv`, giá lấy từ CafeF).

## 3. Cấu hình (làm một lần)

1. **Email cho SEC** (bắt buộc cho Cách B, nhánh Mỹ). SEC yêu cầu User-Agent có email. **Không** ghi email vào `config.yaml`, vì repo công khai. Tạo file `config.local.yaml` ở thư mục gốc (đã nằm trong `.gitignore`):
   ```yaml
   contact_email: "email_cua_ban@example.com"
   ```
   Hoặc đặt biến môi trường `CONTACT_EMAIL`.
2. **Từ điển Loughran–McDonald** (bắt buộc cho nhánh Mỹ). SRAF chỉ để link Google Drive nên phải tải tay, rồi đặt vào thư mục `dict/` và giữ nguyên tên file:
   - Master Dictionary (CSV): https://sraf.nd.edu/loughranmcdonald-master-dictionary/ → `Loughran-McDonald_MasterDictionary_1993-2025.csv`
   - 10X Summaries (188 MB, chỉ cần cho bước đối chiếu `u04`): https://sraf.nd.edu/sec-edgar-data/lm_10x_summaries/ → `Loughran-McDonald_10X_Summaries_1993-2025.csv`
3. **VietSentiWordNet** tự tải từ GitHub khi chạy bước tone VN, không cần làm gì.

## 4. Mỗi lần mở PowerShell mới

```powershell
cd <đường dẫn>\disclosure-tone-car
.\.venv\Scripts\Activate.ps1
$env:PYTHONUTF8 = "1"                                   # console Windows mặc định không in được tiếng Việt
# Chỉ cần cho nhánh VN (OCR):
$env:PATH = "C:\Program Files\Tesseract-OCR;" + $env:PATH
$env:TESSDATA_PREFIX = "C:\Users\<tên bạn>\tessdata"   # chỉ khi dùng thư mục tessdata riêng (mục 1.3)
```

Kiểm tra nhanh: `pytest -q` phải báo tất cả test đều `passed`.

---

## 5. Cách A – Chạy nhanh từ dữ liệu có sẵn

Repo đã có sẵn dữ liệu đã xử lý (`data/us/processed`, `data/vn/processed`: danh mục văn bản, tone, giá, CAR…). Văn bản thô và văn bản đã trích (`data/*/raw`, `data/*/interim`) **không** có trong git vì quá lớn. Vì vậy Cách A **bỏ qua bước a01 (chấm tone)** và dùng `tone_panel.csv` có sẵn.

```powershell
python run_all.py --market us --from 6    # a02 sự kiện → a03 hồi quy → a04 hình → a06 bảng tổng hợp
python run_all.py --market vn --from 6
```

Hoặc chạy notebook. Notebook tự bỏ qua a01 khi chưa có văn bản đã trích:
```powershell
jupyter notebook notebooks/main.ipynb      # mở trên trình duyệt, chọn Run All
# hoặc chạy không giao diện, ghi kết quả vào chính notebook:
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 notebooks/main.ipynb
```
Nếu notebook báo `ModuleNotFoundError`, tức kernel đang dùng Python toàn cục thay vì `.venv`. Hãy activate `.venv` trước khi gọi `jupyter`, hoặc đăng ký kernel riêng:
`python -m ipykernel install --user --name=doan05 --display-name "Python (Đồ án 05)"` rồi chọn kernel đó trong notebook.

Kết quả sẽ nằm ở `outputs/us/` và `outputs/vn/` (xem mục 8).

---

## 6. Cách B – Chạy lại toàn bộ

Thứ tự các bước (`python run_all.py --market <us|vn> --only <tên>` chạy riêng từng bước; `--from N` chạy từ bước N trở đi):

| # | Mỹ (`--market us`) | Thời gian | Việt Nam (`--market vn`) | Thời gian |
|---|---|---|---|---|
| 1 | `u01` tải 10-K (SEC ≤ 8 request/giây) | ~5 phút | `v01` đọc `data/vn/tickers.csv` | < 1 giây |
| 2 | `u02` làm sạch 10-K, cắt MD&A | ~1 phút | `v02` tải BCTN từ CafeF | ~4 giờ |
| 3 | `u03` giá (Yahoo) + XBRL | ~15 giây | `v03` trích thông điệp lãnh đạo (OCR) | ~3 giờ |
| 4 | `a01` chấm tone | ~1 phút | `v04` giá CafeF | ~2 giờ |
| 5 | `u04` đối chiếu với LM | ~1,5 phút | `a01` chấm tone | ~15 giây |
| 6 | `a02` nghiên cứu sự kiện | ~20 giây | `a02` | ~20 giây |
| 7 | `a03` hồi quy | vài giây | `a03` | vài giây |
| 8 | `a04` hình | vài giây | `a04` | vài giây |
| 9 | `a06` bảng tổng hợp | vài giây | `a06` | vài giây |

Mọi file tải về đều được **lưu cache**. Nếu bị ngắt giữa chừng, chỉ cần chạy lại cùng lệnh: file nào đã có sẽ được bỏ qua.

### 6.1 Nhánh Mỹ
```powershell
python run_all.py --market us
```

### 6.2 Nhánh Việt Nam

**Bước chuẩn bị giá:**
1. Vào https://cafef.vn/du-lieu/du-lieu-download.chn, tải 2 file mới nhất thuộc nhóm **"Đã điều chỉnh"**: `CafeF.SolieuGD.Upto<ngày>.zip` và `CafeF.Index.Upto<ngày>.zip`. **Không** lấy file có chữ `Raw`.
2. Giải nén vào `data/vn/raw/prices_cafef/`. Để các file CSV trong thư mục con cũng được.
3. Danh sách mã `data/vn/tickers.csv` (100 mã VN30 + VN100, rổ kỳ 7/2026) đã có trong repo.

**Chạy lần lượt:**
```powershell
python run_all.py --market vn --only v01
python src/vn/v02_crawl_bctn.py --limit 3        # chạy thử 3 mã; kiểm tra rồi mới chạy toàn bộ
python run_all.py --market vn --only v02
python run_all.py --market vn --only v03
python src/vn/v03_extract_letter.py --manual     # áp các trang đã kiểm tra tay (manual_pages.csv)
python run_all.py --market vn --only v04
python run_all.py --market vn --from 5           # a01 → a06
```

**Bước kiểm tra tay (human-in-the-loop).** Cần đọc kỹ trước khi dùng kết quả:
- `data/vn/processed/manual_pages.csv` đã chứa 144 văn bản được xác định trang bằng tay (50 ca đợt đầu + 80 thư bị bước trích tự động cắt ở trần 6 trang + 24 thư không có lời chào/câu kết), có ghi chú từng ca. `--manual` áp lại các trang này sau `v03`. Để thêm ca mới, ghi thêm dòng `ticker,year,start_page,end_page,force_ocr,ghi_chu`:
  - `force_ocr = 1` khi lớp chữ PDF bị lỗi font.
  - `start_page = 0` khi xác nhận BCTN không có thư của ban lãnh đạo (văn bản sẽ bị loại).
- `data/vn/processed/qc_sample.csv` là mẫu 10% đã đối chiếu (49/59 đúng). Nếu chạy lại `v03` toàn bộ, file này bị tạo lại và phải điền lại. Để chỉ trích các BCTN mới mà giữ kết quả cũ, dùng `python src/vn/v03_extract_letter.py --new`.
- Sau lần chạy `a01` đầu tiên, `outputs/vn/candidate_terms.csv` liệt kê các cụm từ hay gặp chưa có trong từ điển. Muốn mở rộng `dict/fin_vn.csv` thì duyệt tay, thêm vào, rồi chạy lại `--from 5`. Lần chạy gốc đã làm việc này (xem `outputs/vn/fin_vn_de_xuat.csv`).

### 6.3 Tùy chọn: FinBERT (mô hình M8 của nhánh Mỹ)
```powershell
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install "transformers>=4.40"
python -c "import sys; sys.path.insert(0,'src'); from analysis import a05_finbert as f; f.main('us', max_sentences=100)"
python run_all.py --market us --only a03         # a03 tự thêm M8 khi có data/us/processed/finbert.csv
```
Trên CPU, bước này mất nhiều giờ.

### 6.4 Tùy chọn: tầng AI sửa OCR (nhánh VN)
1. Lấy key Gemini miễn phí tại https://aistudio.google.com/apikey (đăng nhập Google → *Create API key*).
2. Tạo file `.env` ở thư mục gốc repo (cùng chỗ với `config.yaml`), nội dung một dòng:
   ```
   GEMINI_API_KEY=dán_key_vào_đây
   ```
   File này đã bị `.gitignore` bỏ qua. **Không dán key vào code, notebook hay tin nhắn.**
3. Khi `enabled: true` và có key, `v03` và `--manual` tự chạy tầng AI. Để chạy riêng trên các thư đã trích
   (sau `v03` và `--manual`, trước `v04`):
   ```powershell
   python src/vn/v03_extract_letter.py --llm-dry     # xem có bao nhiêu trang sẽ gửi AI, không tốn lượt gọi
   python src/vn/v03_extract_letter.py --llm         # gửi các trang OCR xấu cho AI, ghi lại văn bản thư
   python run_all.py --market vn --from 5            # tính lại tone → CAR → hồi quy
   ```
   Chạy lại `--llm` lần hai gần như không tốn lượt gọi vì phản hồi đã được cache.
4. Muốn tắt: đặt `enabled: false` ở khối `vn.extract.llm` trong `config.yaml`.
5. Đánh giá độ chính xác: `python src/vn/v03b_eval_ocr.py` lần đầu sẽ chọn 15 trang và xuất ảnh vào
   `data/vn/interim/gold_png/`. Gõ tay nguyên văn từng trang vào `data/vn/processed/gold/<MÃ>_<NĂM>_p<TRANG>.txt`
   rồi chạy lại để có CER/WER trước/sau (`outputs/vn/ocr_eval.csv`).

---

## 7. Đọc và kiểm tra kết quả

- **`RESULTS.md`**: báo cáo kết quả đầy đủ, mỗi con số ghi rõ file nguồn.
- `outputs/<us|vn>/`:

| File | Nội dung |
|---|---|
| `sample_funnel.csv`, `coverage_by_year.csv` | Phễu mẫu, độ phủ theo năm |
| `tone_descriptive.csv`, `tone_by_year.csv`, `fig1_tone_by_year.png` | Mục tiêu 1 – thống kê tone |
| `dictionary_comparison.txt`, `misclassified_general_neg.csv`, `fig2_misclassified.png` | Mục tiêu 2 – từ điển tổng quát gán sai |
| `car_tests.csv`, `car_by_tone.csv`, `fig3_caar_by_tone.png` | Mục tiêu 3 – CAR khác 0 không, phân hóa theo tone |
| `regression_main.csv`, `economic_magnitude.csv`, `regression_fama_macbeth.csv`, `regression_robustness.csv` | Hồi quy, độ lớn kinh tế, độ vững |
| `assumption_tests.csv` | Breusch–Pagan, Jarque–Bera, VIF |
| (Mỹ) `validate_vs_lm*.csv`, `earnings_overlap.csv` | Đối chiếu với LM; hồ sơ trùng ngày công bố KQKD |
| (VN) `event_date_check.csv` | Kiểm tra ngày sự kiện T=0 |

- Nếu chạy lại mà ra số khác `RESULTS.md`, hãy kiểm tra: phiên bản từ điển LM, file giá CafeF (ngày "Upto" khác nhau thì giá điều chỉnh có thể khác chút ít), và `manual_pages.csv`.

## 8. Lỗi thường gặp

| Lỗi | Cách xử lý |
|---|---|
| `UnicodeEncodeError: 'charmap' codec…` | Chưa đặt `$env:PYTHONUTF8 = "1"` |
| `Sửa contact_email…` (SEC) | Chưa tạo `config.local.yaml` hoặc chưa đặt `CONTACT_EMAIL` (mục 3.1) |
| `Thiếu từ điển LM` | Chưa đặt file Master Dictionary vào `dict/` (mục 3.2) |
| `ModuleNotFoundError: common` khi chạy `python src/vn/...` | Chạy lệnh từ **thư mục gốc** của repo |
| `OCR lỗi (TesseractNotFoundError…)` | Chưa thêm Tesseract vào `PATH` hoặc thiếu `vie` (mục 1.3, 4) |
| Tải CafeF báo 404 | Code đã tự thử host cũ `cafef1.mediacdn.vn`. Nếu vẫn lỗi, file đã bị gỡ khỏi CafeF |
| Bước tải đứng yên rất lâu | Kiểm tra mạng và chế độ ngủ của máy, rồi chạy lại (có cache) |
| Notebook: `ModuleNotFoundError: tqdm` | Kernel không dùng `.venv` (xem cuối mục 5) |

## 9. Quy ước khi đóng góp

- Không commit dữ liệu thô (`data/*/raw`, `data/*/interim`), email, file `.env` hay API key. `.gitignore` đã chặn sẵn.
- Mỗi lần sửa code, cấu hình hoặc từ điển, ghi một dòng vào `CHANGELOG_RUN.md`: sửa gì, vì sao, ảnh hưởng gì.
- Làm trên nhánh riêng rồi tạo pull request, không push thẳng `main`.

## 10. Demo trực tiếp cho giảng viên

Toàn bộ kịch bản dưới đây chạy trên máy đã có dữ liệu (máy chạy gốc), **không cần mạng**, mất khoảng 10–15 phút.

**Chuẩn bị trước buổi (tối hôm trước, khoảng 15 phút):**
1. Mở PowerShell, làm đủ các bước ở mục 4 (activate `.venv`, `PYTHONUTF8`, Tesseract).
2. `git checkout feat/llm-ocr` (hoặc `main` nếu đã merge), rồi `pytest -q`: mọi test phải `passed`.
3. Chạy thử một lượt kịch bản bên dưới. Mở sẵn `RESULTS.md` và 3 hình trong `outputs/vn/`.
4. Tắt chế độ ngủ của máy, cắm sạc.

**Dashboard (giao diện web, nên dùng khi trình bày):** `powershell -ExecutionPolicy Bypass -File dashboard
un.ps1` – tự mở trình duyệt; chọn **Giao diện → Sáng** khi chiếu. Các trang Tổng quan → Giọng điệu → Phản ứng thị trường → Tra cứu văn bản → Thử một câu đi đúng thứ tự kịch bản dưới đây (xem `dashboard/README.md`).

**Cách chạy trên terminal:** `powershell -ExecutionPolicy Bypass -File demo.ps1`. Script chạy lần lượt các bước dưới đây, mỗi bước dừng chờ Enter, tự mở PDF/hình khi cần và có chỗ mời thầy tự gõ câu. Muốn kiểm tra trước buổi mà không phải bấm Enter: `$env:DEMO_AUTO = "1"` rồi chạy lệnh trên.

**Kịch bản:**

| Bước | Nói gì | Lệnh / thao tác |
|---|---|---|
| 1. Bài toán | Câu hỏi nghiên cứu, hai mẫu Mỹ – VN, T=0, CAR[T,T+3] | Mở `README.md` (bảng đầu trang) |
| 2. Đo giọng điệu (Mục tiêu 1–2) | Đếm từ theo từ điển tài chính vs từ điển tổng quát; từ điển tổng quát gắn nhãn sai | `python demo_tone.py "Năm 2023 ngân hàng gặp nhiều khó khăn, nợ xấu tăng và lợi nhuận suy giảm; tuy vậy chúng tôi vẫn tăng trưởng bền vững nhờ mảng thương mại và bán lẻ."` → VietSentiWordNet đếm "thương", "bán" là tiêu cực. Tiếng Anh: `python demo_tone.py --en "The company reported a net loss, higher tax expense and may face adverse litigation."` → Harvard GI đếm TAX, EXPENSE. Có thể mời thầy tự gõ câu |
| 3. Từ PDF đến văn bản | Trích thư lãnh đạo từ BCTN; OCR; tầng AI chỉ chép lại trang OCR xấu | Mở PDF MWG 2019 (`data/vn/raw/bctn/`) ở trang thư, rồi `python demo_tone.py --file data/vn/interim/text/MWG_2019_vi.txt`. Tầng AI: `python src/vn/v03_extract_letter.py --llm --only MWG_2019` (dùng cache, vài giây, không tốn lượt gọi); nhật ký từng trang ở `data/vn/processed/llm_pages.csv` |
| 4. Nghiên cứu sự kiện + hồi quy (Mục tiêu 3) | Market model, CAR, kiểm định, hồi quy cluster theo mã | `python run_all.py --market vn --from 6` (a02 → a06, khoảng 15 giây). Bảng CAR theo nhóm tone và hồi quy in ngay trên màn hình |
| 5. Kết quả | Hình CAAR theo tone, hệ số và độ lớn kinh tế, so Mỹ – VN | Mở `outputs/vn/fig3_caar_by_tone.png`, `outputs/vn/regression_main.csv`, rồi `RESULTS.md` mục Tóm tắt và 4.3–4.6 |
| 6. (Tùy chọn) Notebook | Mọi bảng và hình trong một chỗ | `jupyter notebook notebooks/main.ipynb` → Kernel → Change kernel → **Python (Đồ án 05)**. Notebook đã lưu sẵn kết quả, chỉ cần cuộn xem; không bấm Run All trong buổi demo (chạy cả nhánh Mỹ, lâu hơn) |

**Nếu được hỏi:**
- *Chạy lại từ đầu mất bao lâu?* Cách B, 10–12 giờ, chủ yếu là tải dữ liệu. Mọi thứ tải về đều được cache (mục 6).
- *Kết quả có tái lập được không?* `seed: 42`, cache, `CHANGELOG_RUN.md` ghi mọi thay đổi, `RESULTS.md` ghi file nguồn cho từng con số.
- *AI có sửa nội dung không?* Chỉ chép nguyên văn (temperature = 0). Bản AI bị loại nếu chất lượng giảm hoặc khác xa bản OCR. Mọi quyết định ghi ở `llm_pages.csv`. So sánh hệ số trước/sau ở `RESULTS.md` mục 4.5.
- *Sao biết đúng trang thư?* Mẫu QC 10% và danh sách kiểm tra tay trong `data/vn/processed/manual_pages.csv` (mỗi dòng có ghi chú lý do).
