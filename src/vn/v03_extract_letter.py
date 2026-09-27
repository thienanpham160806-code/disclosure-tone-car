"""B3. Trích xuất "Thông điệp của Chủ tịch HĐQT" từ PDF BCTN (Automation + AI + human check).

Vì sao PDF BCTN "khó": (1) thiết kế đồ họa nhiều cột, chữ trên ảnh; (2) một số file là bản scan không có
lớp chữ; (3) một số file có lớp chữ nhưng lỗi font (TCVN3/VNI) → ra ký tự rác. Chiến lược 3 tầng:
  Tầng 1 – text layer (PyMuPDF, sắp xếp theo khối) → nếu trang "sạch" thì dùng luôn.
  Tầng 2 – OCR (render 300 dpi → Tesseract 'vie') cho trang rỗng / trang rác.
  Tầng 3 – (tùy chọn) Claude API: chỉ gửi ~300 ký tự đầu mỗi trang để hỏi "thông điệp ở trang nào"
           → rất ít token; không gửi cả PDF.
Sau đó: human check trên mẫu 10% (file qc_sample.csv để điền tay).
"""
import re, os, json, argparse
import fitz, pytesseract, pandas as pd
from PIL import Image
from tqdm import tqdm
from multiprocessing import Pool
from common import CFG, P, D, norm_vi as norm
V = CFG["vn"]

X = V["extract"]
_WARNED = False
OUT_TXT = D("vn", "interim", "text", "x").parent
VN_CHARS = set("ăâđêôơưáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ")

START = re.compile(r"th[ôo]ng\s*đi[ệe]p|thư\s*(gửi|của)\s*(quý\s*)?(cổ\s*đông|chủ\s*tịch)|lời\s*(ngỏ|mở\s*đầu|chào)"
                   r"|phát\s*biểu\s*của\s*chủ\s*tịch|message\s+from|letter\s+(to|from)|chairman.?s\s+(message|statement|letter)")
END_HEAD = re.compile(r"^(.{0,40})(thông tin chung|tổng quan|giới thiệu|lịch sử hình thành|quá trình hình thành|"
                      r"tình hình hoạt động|báo cáo của ban (giám đốc|tổng giám đốc)|báo cáo của hội đồng quản trị|"
                      r"general information|overview|corporate profile|history|business performance)")
SIGN = re.compile(r"(tm\.?|thay mặt)\s*hội đồng quản trị|trân trọng|on behalf of the board|sincerely|best regards")
TOC = re.compile(r"mục lục|nội dung chính|table of contents|\bcontents\b")


def quality(t):
    letters = [c for c in t.lower() if c.isalpha()]
    if len(letters) < 80:
        return "empty", 0.0
    vn = sum(c in VN_CHARS for c in letters) / len(letters)
    # font lỗi TCVN3/VNI → ký tự Latin-1 lạ (« ¸ µ ®...), vùng Private Use, hoặc "(cid:12)"
    weird = (sum(0xA0 <= ord(c) <= 0xBF or 0xE000 <= ord(c) <= 0xF8FF for c in t) + 5 * t.count("(cid:")) / max(len(t), 1)
    return ("garbled" if weird > 0.02 else "ok"), vn


def page_text(doc, i, lang):
    """Lấy text trang i; tự OCR nếu rỗng/rác. Trả về (text, method)."""
    pg = doc[i]
    blocks = sorted(pg.get_text("blocks"), key=lambda b: (round(b[1] / 20), b[0]))  # trên→dưới, trái→phải
    t = "\n".join(b[4] for b in blocks if b[6] == 0)
    q, vn = quality(t)
    if q == "ok" and (lang == "en" or vn > 0.04):
        return t, "text"
    pix = pg.get_pixmap(dpi=X["ocr_dpi"])
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    ocr_lang = "eng" if lang == "en" else X["ocr_lang"]
    try:
        return pytesseract.image_to_string(img, lang=ocr_lang, config="--psm 3"), "ocr"
    except Exception as e:                  # thiếu gói ngôn ngữ / chưa cài Tesseract → không làm sập cả pipeline
        global _WARNED
        if not _WARNED:
            print(f"  ! OCR lỗi ({e}) – kiểm tra cài đặt Tesseract + gói 'vie'"); _WARNED = True
        return t, "text_ocr_fail"


def find_start(heads):
    """heads: list[(i, text)] – bỏ trang mục lục, chọn trang đầu tiên có tiêu đề thông điệp ở nửa trên."""
    for i, t in heads:
        n = norm(t)
        if TOC.search(n[:400]) or len(re.findall(r"\s\d{1,3}\s", n)) > 15:
            continue
        m = START.search(n)
        if m and m.start() < max(600, len(n) // 2):
            return i
    return None


def llm_locate(heads):
    """Tầng 3: hỏi Claude trang bắt đầu/kết thúc – chỉ gửi 300 ký tự đầu mỗi trang."""
    import anthropic
    snippet = "\n".join(f"[Trang {i+1}] {norm(t)[:300]}" for i, t in heads)
    msg = anthropic.Anthropic().messages.create(
        model="claude-haiku-4-5-20251001", max_tokens=60,
        messages=[{"role": "user", "content": "Đây là đầu các trang của một báo cáo thường niên. Trang nào bắt đầu và "
                   "kết thúc 'Thông điệp của Chủ tịch HĐQT' (thư gửi cổ đông)? Chỉ trả JSON "
                   '{"start":số,"end":số} hoặc {"start":null}.\n' + snippet}])
    j = json.loads(re.search(r"\{.*\}", msg.content[0].text, re.S).group())
    return (None, None) if not j.get("start") else (j["start"] - 1, j.get("end", j["start"]) - 1)


def extract(row):
    f = D("vn", "raw", "bctn", row["file"])
    base = dict(ticker=row["ticker"], year=row["year"], lang=row["lang"], file=row["file"])
    try:
        doc = fitz.open(f)
    except Exception as e:
        return {**base, "flag": f"open_fail:{e}"}
    n = min(len(doc), X["max_scan_pages"])
    cache, methods = {}, []

    def get(i):
        if i not in cache:
            cache[i] = page_text(doc, i, row["lang"])
        return cache[i][0]

    start, end, how = None, None, "regex"
    for i in range(n):                      # quét lần lượt, dừng ngay khi thấy tiêu đề → tiết kiệm OCR
        if find_start([(i, get(i))]) is not None:
            start = i; break
    heads = [(i, cache[i][0]) for i in sorted(cache)]
    if start is None and X.get("use_llm_fallback") and os.getenv("ANTHROPIC_API_KEY"):
        start, end = llm_locate(heads); how = "llm"
    if start is None:
        return {**base, "flag": "not_found", "pages": len(doc)}
    parts = []
    last = min(len(doc) - 1, start + X["max_letter_pages"] - 1) if end is None else end
    for i in range(start, last + 1):
        t = get(i); nt = norm(t)
        if i > start and END_HEAD.search(nt[:200]) and how == "regex":
            break
        parts.append(t); methods.append(cache[i][1])
        if SIGN.search(nt) and how == "regex":
            break
    text = re.sub(r"[ \t]+", " ", "\n".join(parts))
    (OUT_TXT / f"{row['ticker']}_{row['year']}_{row['lang']}.txt").write_text(text, encoding="utf-8")
    nw = len(text.split())
    flag = "too_short" if nw < 250 else ("too_long" if nw > 5000 else "ok")
    return {**base, "start_page": start + 1, "end_page": start + len(parts), "locate": how,
            "method": "ocr" if "ocr" in methods else "text", "n_syllables": nw,
            "vn_ratio": round(quality(text)[1], 3), "flag": flag}


def main(workers=4):
    meta = pd.read_csv(D("vn", "processed", "bctn_meta.csv"))
    meta = meta[meta.status == "ok"]
    # ưu tiên bản ngôn ngữ trong config; nếu không có thì lấy bản còn lại
    meta["pri"] = (meta.lang != V["prefer_lang"]).astype(int)
    meta = meta.sort_values("pri").drop_duplicates(["ticker", "year"])
    with Pool(workers) as pool:
        res = list(tqdm(pool.imap_unordered(extract, meta.to_dict("records")), total=len(meta), desc="Trích xuất"))
    out = pd.DataFrame(res)
    out.to_csv(D("vn", "processed", "letters_meta.csv"), index=False)
    build_docs(out)
    print(out.flag.value_counts().to_string()); print(out.get("method", pd.Series()).value_counts().to_string())
    # Human check: mẫu 10% (tối thiểu 20 văn bản) để đối chiếu tay với PDF gốc
    ok = out[out.flag.isin(["ok", "too_long", "too_short"])]
    qc = ok.sample(n=min(len(ok), max(20, len(ok) // 10)), random_state=CFG["seed"])
    qc.assign(dung_doan_thong_diep="", loi_ocr_moi_100_tu="", ghi_chu="").to_csv(
        D("vn", "processed", "qc_sample.csv"), index=False, encoding="utf-8-sig")
    print(f"→ Điền tay data/vn/processed/qc_sample.csv ({len(qc)} dòng). Dòng flag=not_found: xem PDF và ghi trang vào "
          f"data/vn/processed/manual_pages.csv (ticker,year,start_page,end_page) rồi chạy lại với --manual")


def apply_manual():
    """Human-in-the-loop: trích lại các file đã được người kiểm tra ghi trang thủ công."""
    man = pd.read_csv(D("vn", "processed", "manual_pages.csv"))
    lm = pd.read_csv(D("vn", "processed", "letters_meta.csv"))
    for r in man.itertuples():
        row = lm[(lm.ticker == r.ticker) & (lm.year == r.year)].iloc[0]
        doc = fitz.open(D("vn", "raw", "bctn", row.file))
        txt = "\n".join(page_text(doc, i, row.lang)[0] for i in range(r.start_page - 1, r.end_page))
        (OUT_TXT / f"{r.ticker}_{r.year}_{row.lang}.txt").write_text(txt, encoding="utf-8")
        lm.loc[(lm.ticker == r.ticker) & (lm.year == r.year), ["start_page", "end_page", "locate", "flag", "n_syllables"]] = \
            [r.start_page, r.end_page, "manual", "ok", len(txt.split())]
    lm.to_csv(D("vn", "processed", "letters_meta.csv"), index=False); build_docs(lm)
    print(f"Đã cập nhật {len(man)} văn bản thủ công")


def build_docs(lm):
    """Chuẩn hóa sang bảng docs.csv dùng chung với nhánh Mỹ."""
    meta = pd.read_csv(D("vn", "processed", "bctn_meta.csv"))[["ticker", "year", "group", "event_date", "event_src"]]
    d = lm.merge(meta.drop_duplicates(["ticker", "year"]), on=["ticker", "year"], how="left")
    docs = pd.DataFrame({"doc_id": d.ticker + "_" + d.year.astype(str), "ticker": d.ticker, "year": d.year,
                         "event_date": d.event_date, "after_close": False, "lang": d.lang,
                         "text_main": d.ticker + "_" + d.year.astype(str) + "_" + d.lang + ".txt",
                         "text_alt": None, "industry": "", "group": d.group,
                         "flag": d.flag.where(d.flag != "too_long", "ok"), "event_src": d.event_src})
    docs.to_csv(D("vn", "processed", "docs.csv"), index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4); ap.add_argument("--manual", action="store_true")
    a = ap.parse_args()
    apply_manual() if a.manual else main(a.workers)
