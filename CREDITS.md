# Nguồn tham khảo và giấy phép

Bản giấy phép MIT gốc nằm trong `third_party_licenses/`.

Repo này gom điểm mạnh của các dự án mã nguồn mở dưới đây. Code được **chép** chỉ từ repo có giấy phép cho phép
(MIT). Với repo GPL hoặc không ghi giấy phép, nhóm **chỉ học ý tưởng và tự viết lại**.

| Repo | Giấy phép | Lấy gì | Ở đâu trong repo này |
|---|---|---|---|
| [m4a1ak471994/lm2011-replication](https://github.com/m4a1ak471994/lm2011-replication) | MIT | **Chép code**: làm sạch 10-K theo phụ lục LM (bỏ bảng >25% chữ số, `ix:hidden`, gạch nối), trích MD&A nhiều tầng duyệt từ cuối lên, tách từ LM; EDGAR client token-bucket + retry. **Ý tưởng**: mẫu số = từ trong LM master, tf-idf eq.(1), BHAR[0,3], Fama–MacBeth theo quý, đối chiếu với LM 10X Summaries, QC mẫu MD&A | `src/textkit/us_clean.py`, `src/us/edgar_client.py`, `src/textkit/scoring.py`, `src/analysis/a02_event.py`, `a03_regress.py`, `src/us/u04_validate_lm.py` |
| [lefterisloukas/edgar-crawler](https://github.com/lefterisloukas/edgar-crawler) (WWW 2025) | GPL-3.0 | Ý tưởng: gỡ `<span>` inline để không cắt đôi từ trong 10-K iXBRL hiện đại | `clean_primary_html()` |
| [nickderobertis/pysentiment](https://github.com/nickderobertis/pysentiment) (`pysentiment2`) | GPL-2.0 | Dùng như **thư viện phụ thuộc** để đọc file Harvard IV-4 (không chép code) | `src/textkit/dictionaries.py` |
| [rj694/earnings-sentiment](https://github.com/rj694/earnings-sentiment) | không ghi | Ý tưởng: so sánh từ điển LM với FinBERT; cảnh báo cỡ mẫu nhỏ | `src/analysis/a05_finbert.py` |
| [Ernest717/covid-event-study-african-markets](https://github.com/Ernest717/covid-event-study-african-markets) | không ghi | Ý tưởng: tách market model / event window / kiểm định; vẽ đường CAAR | `a02_event.py`, `a04_figures.py` |
| [sonvx/VietSentiWordNet](https://github.com/sonvx/VietSentiWordNet) | — | Dữ liệu từ điển tổng quát tiếng Việt, tải lúc chạy (không phân phối lại) | `load_vswn()` |
| [thinh-vu/vnstock](https://github.com/thinh-vu/vnstock) | giấy phép riêng (phi thương mại) | Thư viện phụ thuộc: rổ VN30/VN100, giá | `src/vn/v01_universe.py`, `v04_prices.py` |
| Notre Dame SRAF | dùng cho nghiên cứu, trích dẫn LM (2011) | Loughran–McDonald Master Dictionary, 10X Summaries | `dict/` (tự tải) |
| [googleapis/python-genai](https://github.com/googleapis/python-genai) (`google-genai`) | Apache-2.0 | Thư viện phụ thuộc: gọi Gemini API (tầng AI đọc ảnh trang / sửa lỗi OCR, định vị thư, thước đo tone đối chứng) | `src/textkit/llm_client.py` |
| [anthropics/anthropic-sdk-python](https://github.com/anthropics/anthropic-sdk-python) (`anthropic`) | MIT | Thư viện phụ thuộc: Claude API (provider dự phòng của tầng AI) | `src/textkit/llm_client.py` |
| [rapidfuzz/RapidFuzz](https://github.com/rapidfuzz/RapidFuzz) | MIT | Thư viện phụ thuộc: độ tương đồng ký tự (kiểm tra LLM không "viết lại"), khoảng cách Levenshtein cho CER/WER | `llm_client.similarity`, `src/vn/v03b_eval_ocr.py` |
| [theskumar/python-dotenv](https://github.com/theskumar/python-dotenv) | BSD-3-Clause | Thư viện phụ thuộc: đọc API key từ `.env` | `src/textkit/llm_client.py` |
| Google Gemini API / Anthropic Claude API | điều khoản dịch vụ của nhà cung cấp | Dịch vụ: chỉ nhận ẢNH hoặc TEXT của từng trang thư lãnh đạo cần sửa (không gửi cả PDF); mọi phản hồi được cache trong `data/vn/interim/llm_cache/` | `src/vn/v03_extract_letter.py` (`--llm`) |

## Điểm nhóm tự bổ sung (không có trong các repo trên)
1. **Hai thị trường, một pipeline**: bảng `docs.csv` chuẩn hóa → mọi bước phân tích dùng chung cho Mỹ và Việt Nam.
2. **Không cần WRDS**: vốn hóa, B/M, turnover lấy từ SEC XBRL `companyfacts` + yfinance (lm2011-replication cần CRSP/Compustat trả phí).
3. **Submissions API** thay master index (chỉ tải đúng 10-K cần), đọc cả trang lịch sử cho ngân hàng lớn; T=0 theo `acceptanceDateTime` (sau 16:00 ET → phiên sau).
4. **Nhánh Việt Nam**: crawl BCTN VN30+VN100 từ CafeF, 3 nguồn ngày công bố, trích Thông điệp HĐQT 3 tầng (text layer → OCR → LLM ít token), human-in-the-loop (QC 10%, trang thủ công).
5. **Tiếng Việt**: từ điển tài chính Việt hóa theo LM, khớp cụm dài nhất ("nợ xấu" ≠ "nợ"), phủ định, file gợi ý mở rộng từ điển; đối chứng VietSentiWordNet.
6. **Suy luận đầy đủ cho câu hỏi CAR[T,T+3]**: t, BMP, Wilcoxon, sign test; nhóm tone T3−T1; OLS cluster + Fama–MacBeth; placebo; market-adjusted và BHAR; kiểm định giả định (BP, JB, VIF).
7. **Tái lập**: `run_all.py`, cache mọi tải xuống, `pytest` cho các khối lõi, notebook chạy trọn từ dữ liệu đã xử lý.
8. **Tầng AI có kiểm soát cho OCR tiếng Việt**: chấm chất lượng từng trang (âm tiết hợp lệ, ký tự rác, token đứt), chỉ gửi trang dưới ngưỡng cho LLM với yêu cầu chép NGUYÊN VĂN, temperature 0, cache, trần lượt gọi, nhật ký nguồn gốc từng trang, đánh giá CER/WER so với trang chuẩn gõ tay.
