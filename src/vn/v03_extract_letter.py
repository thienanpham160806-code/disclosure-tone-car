"""B3. Trích xuất "Thông điệp của Chủ tịch HĐQT" từ PDF BCTN (Automation + AI + human check).

Vì sao PDF BCTN "khó": (1) thiết kế đồ họa nhiều cột, chữ trên ảnh; (2) một số file là bản scan không có
lớp chữ; (3) một số file có lớp chữ nhưng lỗi font (TCVN3/VNI) → ra ký tự rác. Chiến lược nhiều tầng:
  Tầng 1 – text layer (PyMuPDF, sắp xếp theo khối) → nếu trang "sạch" thì dùng luôn.
  Tầng 2 – OCR (render 300 dpi → Tesseract 'vie') cho trang rỗng / trang rác.
  Tầng 3 – AI (Gemini mặc định, Claude dự phòng; src/textkit/llm_client.py), bật/tắt ở vn.extract.llm:
     a) ĐỊNH VỊ: regex không thấy thư → gửi ~300 ký tự đầu mỗi trang, hỏi trang bắt đầu/kết thúc (không gửi cả PDF).
     b) SỬA TRANG CHẤT LƯỢNG THẤP: mỗi trang của thư được chấm quality_score (textkit/ocr_quality.py); trang dưới
        quality_threshold → gửi ẢNH trang (mode vision: chép nguyên văn) hoặc text OCR + ảnh (mode text_fix: chỉ sửa lỗi
        ký tự/dấu). Chỉ nhận bản AI khi chất lượng không giảm (và text_fix: tương đồng với OCR ≥ similarity_min).
        LLM chỉ được CHÉP NGUYÊN VĂN – không diễn đạt lại (đề tài đo giọng điệu). Mọi phản hồi được cache.
     Nguồn gốc ghi ở letters_meta.csv: method ∈ {text, ocr, ocr+llm_fix, llm_vision, manual}, llm_provider, llm_model,
     ocr_quality_before/after; chi tiết từng trang ở data/vn/processed/llm_pages.csv.
Sau đó: human check trên mẫu 10% (file qc_sample.csv để điền tay).
  python src/vn/v03_extract_letter.py              # trích toàn bộ (+ tầng AI nếu bật)
  python src/vn/v03_extract_letter.py --manual     # áp trang thủ công (manual_pages.csv) (+ tầng AI cho các văn bản đó)
  python src/vn/v03_extract_letter.py --llm        # chỉ chạy tầng AI trên các thư đã trích (không OCR lại toàn bộ PDF)
  python src/vn/v03_extract_letter.py --llm-dry    # chỉ chấm chất lượng từng trang, báo số trang sẽ gửi AI (không gọi API)
"""
import sys, pathlib
_SRC = pathlib.Path(__file__).resolve().parents[1]   # chạy trực tiếp: thêm src/, bỏ src/vn (vn/http.py che module http chuẩn)
sys.path[:] = [str(_SRC)] + [p for p in sys.path if pathlib.Path(p or ".").resolve() != _SRC / "vn"]
import re, os, json, argparse, unicodedata
import fitz, pytesseract, pandas as pd
from PIL import Image
from tqdm import tqdm
from multiprocessing import Pool
from common import CFG, P, D, norm_vi as norm
from textkit.ocr_quality import quality_score
V = CFG["vn"]

X = V["extract"]
L = X.get("llm", {})
_WARNED = False
OUT_TXT = D("vn", "interim", "text", "x").parent
VN_CHARS = set("ăâđêôơưáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ")

# So khớp trên văn bản ĐÃ BỎ DẤU (fold): OCR hay đọc sai dấu thanh ("phát biếu của chủ tịch hội đòng", "quý cô đông")
# → regex có dấu bỏ sót trang tiêu đề (CHANGELOG_RUN #16). Nội dung mẫu giữ nguyên, chỉ viết dạng không dấu.
START = re.compile(r"\bthong\s*diep\b|\bthu\s*(gui|cua)\s*(quy\s*)?(co\s*dong|chu\s*tich)|\bloi\s*(ngo|mo\s*dau|chao)\b"
                   r"|\bphat\s*bieu\s*cua\s*chu\s*tich|message\s+from|letter\s+(to|from)|chairman.?s\s+(message|statement|letter)")
END_HEAD = re.compile(r"^(.{0,40})(thong tin chung|tong quan|gioi thieu|lich su hinh thanh|qua trinh hinh thanh|"
                      r"tinh hinh hoat dong|bao cao cua ban (giam doc|tong giam doc)|bao cao cua hoi dong quan tri|"
                      r"general information|overview|corporate profile|history|business performance)")
SIGN = re.compile(r"(tm\.?|thay mat)\s*hoi dong quan tri|tran trong|on behalf of the board|sincerely|best regards")
TOC = re.compile(r"muc luc|noi dung chinh|table of contents|\bcontents\b")


def fold(t):
    """norm_vi + bỏ dấu tiếng Việt (đ→d) để so khớp tiêu đề chịu được lỗi dấu của OCR."""
    t = unicodedata.normalize("NFD", norm(t).replace("đ", "d"))
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def quality(t):
    letters = [c for c in t.lower() if c.isalpha()]
    if len(letters) < 80:
        return "empty", 0.0
    vn = sum(c in VN_CHARS for c in letters) / len(letters)
    # font lỗi TCVN3/VNI → ký tự Latin-1 lạ (« ¸ µ ®...), vùng Private Use, hoặc "(cid:12)"
    weird = (sum(0xA0 <= ord(c) <= 0xBF or 0xE000 <= ord(c) <= 0xF8FF for c in t) + 5 * t.count("(cid:")) / max(len(t), 1)
    return ("garbled" if weird > 0.02 else "ok"), vn


def page_text(doc, i, lang, force_ocr=False):
    """Lấy text trang i; tự OCR nếu rỗng/rác. Trả về (text, method)."""
    pg = doc[i]
    blocks = sorted(pg.get_text("blocks"), key=lambda b: (round(b[1] / 20), b[0]))  # trên→dưới, trái→phải
    t = "\n".join(b[4] for b in blocks if b[6] == 0)
    q, vn = quality(t)
    if q == "ok" and (lang == "en" or vn > 0.04) and not force_ocr:
        return t, "text"
    # trang khổ rất lớn (poster, trang đôi) ở 300 dpi → ảnh khổng lồ, tesseract gần như treo (CHANGELOG_RUN #20)
    dpi = X["ocr_dpi"]; area = pg.rect.width * pg.rect.height / 72 ** 2          # inch²
    if area * dpi ** 2 > 40e6:
        dpi = max(100, int((40e6 / area) ** .5))
    pix = pg.get_pixmap(dpi=dpi)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    ocr_lang = "eng" if lang == "en" else X["ocr_lang"]
    try:
        return pytesseract.image_to_string(img, lang=ocr_lang, config="--psm 3", timeout=180), "ocr"
    except Exception as e:                  # thiếu gói ngôn ngữ / chưa cài Tesseract → không làm sập cả pipeline
        global _WARNED
        if not _WARNED:
            print(f"  ! OCR lỗi ({e}) – kiểm tra cài đặt Tesseract + gói 'vie'"); _WARNED = True
        return t, "text_ocr_fail"


def find_start(heads):
    """heads: list[(i, text)] – bỏ trang mục lục, chọn trang đầu tiên có tiêu đề thông điệp ở nửa trên."""
    for i, t in heads:
        n = fold(t)
        if TOC.search(n[:400]) or len(re.findall(r"\s\d{1,3}\s", n)) > 15:
            continue
        m = START.search(n)
        if m and m.start() < max(600, len(n) // 2):
            return i
    return None


def llm_locate(heads, client):
    """Tầng 3a: hỏi LLM (Gemini/Claude, qua LLMClient) trang bắt đầu/kết thúc – chỉ gửi 300 ký tự đầu mỗi trang."""
    snippet = "\n".join(f"[Trang {i+1}] {norm(t)[:300]}" for i, t in heads)
    j = client.locate(snippet)
    if not j.get("start"):
        return None, None
    s = int(j["start"]) - 1
    e = int(j.get("end") or j["start"]) - 1
    return s, max(s, min(e, s + X["max_letter_pages"] - 1))


def render_png(pg, dpi):
    """Ảnh PNG của trang để gửi AI (giới hạn ~25 triệu điểm ảnh cho trang khổ lớn)."""
    area = pg.rect.width * pg.rect.height / 72 ** 2
    if area * dpi ** 2 > 25e6:
        dpi = max(100, int((25e6 / area) ** .5))
    return pg.get_pixmap(dpi=dpi).tobytes("png")


def _tok_mean(scores, texts):
    w = [max(len(t.split()), 1) for t in texts]
    return round(sum(s * k for s, k in zip(scores, w)) / sum(w), 4) if w else None


def refine_doc(row, client, force_ocr=False, dry=False, page_log=None):
    """Tầng 3b: rà từng trang của thư (start_page..end_page); trang có quality_score < ngưỡng → LLM.
    Ghi lại văn bản thư (đã thay các trang được AI sửa) và trả về các cột nguồn gốc cho letters_meta."""
    doc = fitz.open(D("vn", "raw", "bctn", row["file"]))
    thr, mode = L.get("quality_threshold", 0.85), L.get("mode", "vision")
    texts, q_b, q_a, methods, provs, notes, sent = [], [], [], [], [], [], 0
    for i in range(int(row["start_page"]) - 1, int(row["end_page"])):
        t, how = page_text(doc, i, row["lang"], force_ocr=force_ocr)
        qb = quality_score(t); new, qa, m = t, qb, how
        rec = dict(ticker=row["ticker"], year=row["year"], page=i + 1, source=how, q_before=qb, mode=mode)
        if qb < thr and sent < L.get("max_pages_per_doc", 6):
            sent += 1
            if dry:
                rec["decision"] = "would_send"
            elif client is None:
                rec["decision"] = "no_client"
            else:
                png, use_mode = render_png(doc[i], L.get("dpi", 200)), mode
                try:
                    try:
                        out = client.transcribe_page(png, t, mode)
                    except Exception as e:
                        # Gemini chặn chép nguyên văn (RECITATION) → thử một lần chế độ text_fix trên bản OCR
                        if mode == "vision" and "RECITATION" in str(e) and L.get("recitation_fallback") == "text_fix" and t.strip():
                            use_mode = "text_fix"; rec["mode"] = "text_fix(recitation)"
                            out = client.transcribe_page(png, t, "text_fix")
                        else:
                            raise
                except Exception as e:                       # BudgetExceeded / LLMError → giữ bản cũ, ghi lý do
                    rec.update(decision="error", reason=f"{type(e).__name__}: {str(e)[:160]}")
                else:
                    from textkit.llm_client import decide, similarity
                    q2 = quality_score(out["page_text"])
                    ok, why = decide(use_mode, t, out["page_text"], qb, q2, L)
                    rec.update(q_llm=q2, decision="accepted" if ok else "rejected", reason=why,
                               provider=out.get("provider"), model=out.get("model"), cached=out.get("cached"),
                               is_chairman_letter=out.get("is_chairman_letter"), confidence=out.get("confidence"),
                               sim_to_source=round(similarity(t, out["page_text"]), 3))
                    if ok:
                        new, qa = out["page_text"], q2
                        m = "llm_vision" if use_mode == "vision" else "ocr+llm_fix"
                        provs.append((out.get("provider"), out.get("model")))
                    elif why.startswith("rewrite_suspected"):
                        notes.append(f"p{i+1}:{why}")
        rec["q_after"] = qa
        if page_log is not None:
            page_log.append(rec)
        texts.append(new); q_b.append(qb); q_a.append(qa); methods.append(m)
    res = dict(ocr_quality_before=_tok_mean(q_b, texts), ocr_quality_after=_tok_mean(q_a, texts), llm_pages_sent=sent,
               llm_pages_used=len(provs), llm_note=";".join(notes) or None)
    if dry:
        return res
    text = re.sub(r"[ \t]+", " ", "\n".join(texts))
    (OUT_TXT / f"{row['ticker']}_{row['year']}_{row['lang']}.txt").write_text(text, encoding="utf-8")
    if provs:
        method = "llm_vision" if "llm_vision" in methods else "ocr+llm_fix"
    elif row.get("locate") == "manual":
        method = "manual"
    else:
        method = "ocr" if "ocr" in methods else "text"
    res.update(method=method, n_syllables=len(text.split()),
               llm_provider=";".join(sorted({p for p, _ in provs})) or None,
               llm_model=";".join(sorted({m for _, m in provs})) or None)
    return res


def make_client():
    if not L.get("enabled"):
        return None
    from textkit.llm_client import LLMClient
    c = LLMClient(L)
    if not c.providers():
        print("  ! tầng AI bật nhưng không có GEMINI_API_KEY / ANTHROPIC_API_KEY (biến môi trường hoặc .env) → bỏ qua")
        return None
    return c


def llm_pass(lm, only=None, dry=False):
    """Chạy tầng 3b trên các thư đã trích (flag ok/too_long/too_short). only: tập (ticker, year) cần chạy."""
    client = None if dry else make_client()
    if client is None and not dry:
        return lm
    force = set()
    mp = D("vn", "processed", "manual_pages.csv")
    if mp.exists():
        m = pd.read_csv(mp)
        if "force_ocr" in m:
            force = set(zip(m.ticker[m.force_ocr == 1], m.year[m.force_ocr == 1]))
    todo = lm[lm.flag.isin(["ok", "too_long", "too_short"]) & lm.start_page.notna()]
    if only:
        todo = todo[[(t, y) in only for t, y in zip(todo.ticker, todo.year)]]
    pages = []
    for idx, r in tqdm(list(todo.iterrows()), desc="Tầng AI" + (" (dry)" if dry else "")):
        res = refine_doc(r.to_dict(), client, force_ocr=(r.ticker, r.year) in force, dry=dry, page_log=pages)
        for k, v in res.items():
            if k not in lm:
                lm[k] = None
            if isinstance(v, str) and lm[k].dtype != object:   # cột đọc từ CSV toàn NaN → float64
                lm[k] = lm[k].astype(object)
            lm.at[idx, k] = v
        if not dry:
            nw = res["n_syllables"]
            lm.at[idx, "flag"] = "too_short" if nw < 250 else ("too_long" if nw > 5000 else "ok")
    pl = pd.DataFrame(pages)
    out = D("vn", "processed", "llm_pages_dry.csv" if dry else "llm_pages.csv")
    if not dry and out.exists() and only:          # chạy một phần → giữ log các văn bản khác (bỏ văn bản đã bị loại)
        old = pd.read_csv(out)
        keep = set(zip(lm.ticker[lm.flag.isin(["ok", "too_long", "too_short"])], lm.year[lm.flag.isin(["ok", "too_long", "too_short"])]))
        old = old[[(t, y) not in only and (t, y) in keep for t, y in zip(old.ticker, old.year)]]
        pl = pd.concat([old, pl], ignore_index=True)
    pl.to_csv(out, index=False, encoding="utf-8-sig")
    n_low = int((pl.q_before < L.get("quality_threshold", 0.85)).sum()) if len(pl) else 0
    print(f"Trang thuộc thư: {len(pl)} | dưới ngưỡng {L.get('quality_threshold')}: {n_low}")
    if not dry and client is not None:
        acc = int((pl.get("decision") == "accepted").sum()) if len(pl) else 0
        print(f"Lượt gọi API thật: {client.calls} | cache: {client.cache_hits} | trang nhận bản AI: {acc} | token: {dict(client.usage)}")
    return lm


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
    if start is None:   # định vị bằng AI (nếu bật) làm ở tiến trình chính – trả kèm 300 ký tự đầu mỗi trang đã đọc
        heads = [(i, cache[i][0][:300]) for i in sorted(cache)]
        return {**base, "flag": "not_found", "pages": len(doc), "_heads": json.dumps(heads, ensure_ascii=False)}
    parts = []
    last = min(len(doc) - 1, start + X["max_letter_pages"] - 1) if end is None else end
    for i in range(start, last + 1):
        t = get(i); nt = fold(t)
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


def locate_pass(out):
    """Tầng 3a: regex không thấy thư → hỏi AI (chỉ 300 ký tự đầu mỗi trang). Kết quả gắn locate = 'llm'."""
    if not (L.get("enabled") and L.get("locate")) or "_heads" not in out:
        return out
    client = make_client()
    if client is None:
        return out
    for idx, r in out[out.flag.eq("not_found") & out._heads.notna()].iterrows():
        heads = [tuple(h) for h in json.loads(r._heads)]
        try:
            s, e = llm_locate(heads, client)
        except Exception as ex:
            print(f"  ! AI định vị {r.ticker} {r.year}: {ex}"); continue
        if s is None:
            continue
        doc = fitz.open(D("vn", "raw", "bctn", r.file))
        e = min(e, len(doc) - 1)
        txt = re.sub(r"[ \t]+", " ", "\n".join(page_text(doc, i, r.lang)[0] for i in range(s, e + 1)))
        (OUT_TXT / f"{r.ticker}_{r.year}_{r.lang}.txt").write_text(txt, encoding="utf-8")
        nw = len(txt.split())
        out.loc[idx, ["start_page", "end_page", "locate", "n_syllables", "flag"]] = \
            [s + 1, e + 1, "llm", nw, "too_short" if nw < 250 else ("too_long" if nw > 5000 else "ok")]
    return out


def main(workers=4, only_new=False):
    meta = pd.read_csv(D("vn", "processed", "bctn_meta.csv"))
    meta = meta[meta.status == "ok"]
    # ưu tiên bản ngôn ngữ trong config; nếu không có thì lấy bản còn lại
    meta["pri"] = (meta.lang != V["prefer_lang"]).astype(int)
    meta = meta.sort_values("pri").drop_duplicates(["ticker", "year"])
    old = D("vn", "processed", "letters_meta.csv")
    if only_new and old.exists():   # --new: chỉ trích mã–năm chưa có, giữ kết quả cũ + QC đã điền (CHANGELOG_RUN #27)
        prev = pd.read_csv(old)
        meta = meta[~meta.set_index(["ticker", "year"]).index.isin(prev.set_index(["ticker", "year"]).index)]
        print(f"--new: {len(meta)} văn bản mới")
    with Pool(workers) as pool:
        res = list(tqdm(pool.imap_unordered(extract, meta.to_dict("records")), total=len(meta), desc="Trích xuất"))
    out = pd.DataFrame(res)
    out = locate_pass(out)                              # tầng 3a (nếu bật): AI định vị thư cho các file not_found
    out = out.drop(columns=["_heads"], errors="ignore")
    out = llm_pass(out, only=set(zip(out.ticker, out.year)))   # tầng 3b (nếu bật): AI sửa trang chất lượng thấp
    if only_new and old.exists():
        out = pd.concat([prev, out], ignore_index=True)
    out.to_csv(old, index=False)
    build_docs(out)
    print(out.flag.value_counts().to_string()); print(out.get("method", pd.Series()).value_counts().to_string())
    if only_new:
        return
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
    if "force_ocr" not in man:        # cột tùy chọn: 1 = bỏ lớp chữ (font mã hóa sai một phần), OCR lại (CHANGELOG_RUN #26)
        man["force_ocr"] = 0
    lm = pd.read_csv(D("vn", "processed", "letters_meta.csv"))
    for r in man.itertuples():
        row = lm[(lm.ticker == r.ticker) & (lm.year == r.year)].iloc[0]
        if r.start_page == 0:         # người kiểm tra xác nhận KHÔNG có thư của ban lãnh đạo → loại
            lm.loc[(lm.ticker == r.ticker) & (lm.year == r.year), ["locate", "flag"]] = ["manual", "excluded_manual"]
            continue
        doc = fitz.open(D("vn", "raw", "bctn", row.file))
        txt = "\n".join(page_text(doc, i, row.lang, force_ocr=r.force_ocr == 1)[0] for i in range(r.start_page - 1, r.end_page))
        (OUT_TXT / f"{r.ticker}_{r.year}_{row.lang}.txt").write_text(txt, encoding="utf-8")
        lm.loc[(lm.ticker == r.ticker) & (lm.year == r.year), ["start_page", "end_page", "locate", "flag", "n_syllables"]] = \
            [r.start_page, r.end_page, "manual", "ok", len(txt.split())]
    lm = llm_pass(lm, only=set(zip(man.ticker[man.start_page > 0], man.year[man.start_page > 0])))   # tầng AI (nếu bật)
    lm.to_csv(D("vn", "processed", "letters_meta.csv"), index=False); build_docs(lm)
    print(f"Đã cập nhật {len(man)} văn bản thủ công")


def run_llm(dry=False, only=None):
    """--llm / --llm-dry: tầng AI trên các thư đã trích trong letters_meta.csv (không OCR lại toàn bộ PDF)."""
    lm = pd.read_csv(D("vn", "processed", "letters_meta.csv"))
    lm = llm_pass(lm, only=only, dry=dry)
    if not dry:
        lm.to_csv(D("vn", "processed", "letters_meta.csv"), index=False); build_docs(lm)


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
    ap.add_argument("--new", action="store_true", help="chỉ trích các BCTN chưa có trong letters_meta.csv")
    ap.add_argument("--llm", action="store_true", help="chỉ chạy tầng AI trên các thư đã trích")
    ap.add_argument("--llm-dry", action="store_true", help="chấm chất lượng từng trang, không gọi API")
    ap.add_argument("--only", help="danh sách TICKER_NĂM, phân cách bởi dấu phẩy (vd VIC_2025,HDB_2019)")
    a = ap.parse_args()
    only = {(s.split("_")[0], int(s.split("_")[1])) for s in a.only.split(",")} if a.only else None
    if a.llm or a.llm_dry:
        run_llm(dry=a.llm_dry, only=only)
    else:
        apply_manual() if a.manual else main(a.workers, a.new)
