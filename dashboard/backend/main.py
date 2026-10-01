"""API cho dashboard Đồ án 05 – chỉ ĐỌC kết quả đã có (outputs/, data/*/processed) và chấm tone bằng đúng bộ đếm của
pipeline (src/textkit/scoring.py). Không gọi LLM, không sửa dữ liệu.

Chạy nhanh nhất:  powershell -ExecutionPolicy Bypass -File dashboard\\run.ps1   (tự build giao diện nếu cần, mở trình duyệt)
Hoặc:            .venv\\Scripts\\python dashboard\\backend\\main.py --open     → http://127.0.0.1:8000
"""
import functools, os, pathlib, re, sys, unicodedata

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from textkit import dictionaries as dct                                  # noqa: E402
from textkit.scoring import NEG_EN, NEG_VI, TOK_VI, EnglishScorer, VietScorer  # noqa: E402
from textkit.us_clean import TOKEN_RE                                   # noqa: E402

MARKETS = ("vn", "us")
DIST = ROOT / "dashboard" / "frontend" / "dist"
app = FastAPI(title="Đồ án 05 – Dashboard API")
# CORS: máy cá nhân (Vite dev/preview) + mọi tên miền *.vercel.app; thêm tên miền riêng qua biến môi trường CORS_ORIGINS
app.add_middleware(CORSMiddleware,
                   allow_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()],
                   allow_origin_regex=r"https://[a-z0-9-]+\.vercel\.app|http://(localhost|127\.0\.0\.1)(:\d+)?",
                   allow_methods=["GET", "POST"], allow_headers=["*"])


# ----------------------------------------------------------------------------- tiện ích đọc file
def _csv(*parts, **kw) -> pd.DataFrame | None:
    p = ROOT.joinpath(*parts)
    return pd.read_csv(p, encoding="utf-8-sig", **kw) if p.exists() else None


def _check(mkt: str):
    if mkt not in MARKETS:
        raise HTTPException(404, "Thị trường phải là 'vn' hoặc 'us'")


def _records(df: pd.DataFrame | None):
    return [] if df is None else df.astype(object).where(df.notna(), None).to_dict(orient="records")


def _stars_to_p(stars: str) -> str:
    return {"***": "p < 0,01", "**": "p < 0,05", "*": "p < 0,1"}.get(stars or "", "không có ý nghĩa (p ≥ 0,1)")


def _noise_pct(mkt: str):
    p = ROOT / "outputs" / mkt / "dictionary_comparison.txt"
    if not p.exists():
        return None
    m = re.search(r"([\d.]+)%", p.read_text(encoding="utf-8"))
    return float(m.group(1)) if m else None


# ----------------------------------------------------------------------------- bộ đếm + vị trí từ khớp
@functools.lru_cache(maxsize=2)
def scorers(lang: str):
    if lang == "vi":
        return VietScorer(dct.load_fin_vn()), VietScorer(dct.load_vswn())
    lm = dct.load_lm(); master = lm.pop("master")
    return EnglishScorer(lm, master), EnglishScorer(dct.load_harvard(), master), master


def _spans_vi(text: str, sc: VietScorer):
    """Khớp cụm dài nhất y như VietScorer.run, nhưng giữ vị trí ký tự để tô màu. Trả (n_token, [[start, end, cats]])."""
    low = text.lower()
    if len(low) != len(text):                       # hiếm: lower() đổi độ dài → không tô màu được, vẫn đếm đúng
        return None
    toks = [(m.start(), m.end(), m.group()) for m in TOK_VI.finditer(low)]
    words, n, i, out = [t[2] for t in toks], len(toks), 0, []
    while i < n:
        for L in range(min(sc.maxn, n - i), 0, -1):
            key = tuple(words[i:i + L])
            if key in sc.map:
                cats = set(sc.map[key])
                if "positive" in cats and NEG_VI & set(words[max(0, i - 3):i]):
                    cats.discard("positive")
                if cats:
                    out.append([toks[i][0], toks[i + L - 1][1], sorted(cats)])
                i += L
                break
        else:
            i += 1
    return n, out


def _spans_en(text: str, sc: EnglishScorer, master: set):
    up = text.upper()
    if len(up) != len(text):
        return None
    toks = [(m.start(), m.end(), m.group()) for m in TOKEN_RE.finditer(up)]
    words, out = [t[2] for t in toks], []
    for i, (s, e, w) in enumerate(toks):
        cats = {c for c, terms in sc.dic.items() if w in terms}
        if "positive" in cats and NEG_EN & set(words[max(0, i - 3):i]):
            cats.discard("positive")
        if cats:
            out.append([s, e, sorted(cats)])
    return sum(w in master for w in words), out


def _summary(n, spans, text):
    cnt = {c: 0 for c in ("negative", "positive", "uncertainty", "litigious")}
    top = {}
    for s, e, cats in spans:
        w = text[s:e].lower()
        for c in cats:
            if c in cnt:
                cnt[c] += 1
                top.setdefault(c, {}).setdefault(w, 0)
                top[c][w] += 1
    pos, neg = cnt["positive"], cnt["negative"]
    return {"n_words": n, "counts": cnt,
            "net": (pos - neg) / (pos + neg) if pos + neg else 0.0,
            "neg_pct": 100 * neg / max(n, 1), "pos_pct": 100 * pos / max(n, 1),
            "top": {c: sorted(d.items(), key=lambda x: -x[1])[:12] for c, d in top.items()},
            "spans": spans}


def _scorers_or_503(lang):
    try:
        return scorers(lang)
    except SystemExit as e:                    # load_lm báo thiếu file bằng SystemExit
        raise HTTPException(503, f"Máy chủ chưa có từ điển: {e}") from None
    except Exception as e:
        raise HTTPException(503, f"Không nạp được từ điển ({type(e).__name__}: {str(e)[:200]})") from None


def analyze(text: str, lang: str):
    text = unicodedata.normalize("NFC", text or "")
    if lang == "vi":
        fin, gen = _scorers_or_503("vi")
        rf, rg = _spans_vi(text, fin), _spans_vi(text, gen)
    else:
        fin, gen, master = _scorers_or_503("en")
        rf, rg = _spans_en(text, fin, master), _spans_en(text, gen, master)
    if rf is None or rg is None:
        raise HTTPException(422, "Không tách được từ để tô màu cho văn bản này")
    F, G = _summary(*rf, text), _summary(*rg, text)
    # "gán sai": từ điển tổng quát gắn TIÊU CỰC nhưng từ điển tài chính không coi là tiêu cực ở cùng vị trí
    fneg = [(s, e) for s, e, c in F["spans"] if "negative" in c]
    mis = [[s, e] for s, e, c in G["spans"] if "negative" in c and not any(s < fe and fs < e for fs, fe in fneg)]
    return {"text": text, "lang": lang, "financial": F, "general": G, "mislabeled": mis,
            "dict_names": {"financial": "fin_vn" if lang == "vi" else "Loughran–McDonald",
                           "general": "VietSentiWordNet" if lang == "vi" else "Harvard GI"}}


# ----------------------------------------------------------------------------- trạng thái máy chủ
@app.api_route("/api/status", methods=["GET", "HEAD"])
def status():
    import glob
    has = lambda pat: bool(glob.glob(str(ROOT / pat)))
    return {"lm_dictionary": has("dict/Loughran*MasterDictionary*.csv"),
            "vswn_dictionary": has("dict/VietSentiWordnet_*.txt"),
            "extracted_text": has("data/vn/interim/text/*.txt") and has("data/us/interim/text/*.gz"),
            "raw_pdf": has("data/vn/raw/bctn/*.pdf"),
            "ai_key": bool(_llm().providers())}        # LLMClient tự nạp .env nếu có


# ----------------------------------------------------------------------------- tổng quan
@app.get("/api/overview")
def overview():
    out = {}
    for mkt in MARKETS:
        em, ct, fn = _csv("outputs", mkt, "economic_magnitude.csv"), _csv("outputs", mkt, "car_tests.csv"), _csv("outputs", mkt, "sample_funnel.csv")
        if em is None:
            continue
        def coef(bang, mo_hinh, bien="fin_neg_z"):
            r = em[(em.bang == bang) & (em.mo_hinh == mo_hinh) & (em.bien == bien)]
            if r.empty:
                return None
            r = r.iloc[0]; st = r.sao if isinstance(r.sao, str) else ""
            return {"coef": r.he_so, "se": r.se, "stars": st, "sig": _stars_to_p(st), "pp_per_sd": r.thay_doi_CAR_diem_pct_khi_tang_1SD}
        car = ct[ct.window == "CAR[0,3]"].iloc[0] if ct is not None else None
        out[mkt] = {
            "main": coef("regression_main.csv", "M2 fin_neg"),
            "car05": coef("regression_robustness.csv", "CAR[0,5]"),
            "car010": coef("regression_robustness.csv", "CAR[0,10]"),
            "gen": coef("regression_main.csv", "M3 gen_neg", "gen_neg_z"),
            "car": None if car is None else {"n": int(car.N), "mean_pct": car.mean_pct, "p": car.p_t},
            "n_reg": int(fn.iloc[-1].so_van_ban) if fn is not None else None,
            "noise_pct": _noise_pct(mkt),
        }
    return out


# ----------------------------------------------------------------------------- Mục tiêu 1–2: giọng điệu
@app.get("/api/{mkt}/tone_by_year")
def tone_by_year(mkt: str):
    _check(mkt)
    df = _csv("outputs", mkt, "tone_by_year.csv")
    return _records(df)


@app.get("/api/{mkt}/misclassified")
def misclassified(mkt: str, top: int = 12):
    _check(mkt)
    df = _csv("outputs", mkt, "misclassified_general_neg.csv")
    if df is None:
        return {"noise_pct": None, "words": []}
    df = df.head(top)[["word", "share_pct", "in_fin_negative"]]
    return {"noise_pct": _noise_pct(mkt), "words": _records(df)}


# ----------------------------------------------------------------------------- Mục tiêu 3: phản ứng thị trường
@app.get("/api/{mkt}/caar")
def caar(mkt: str):
    _check(mkt)
    df = _csv("outputs", mkt, "caar_by_tone.csv")
    if df is None:
        return {"groups": [], "rows": []}
    groups = []
    for col, key in zip(df.columns[1:], ("T1", "T2", "T3")):
        m = re.search(r"n=(\d+)", col)
        groups.append({"key": key, "label": col.split(" (")[0], "n": int(m.group(1)) if m else None})
    df.columns = ["phien", "T1", "T2", "T3"]
    return {"groups": groups, "rows": _records(df)}


@app.get("/api/{mkt}/car_by_tone")
def car_by_tone(mkt: str):
    _check(mkt)
    return _records(_csv("outputs", mkt, "car_by_tone.csv"))


WINDOWS = [("regression_robustness.csv", "CAR[-1,1]", "CAR[−1,1]"), ("regression_robustness.csv", "CAR[0,1]", "CAR[0,1]"),
           ("regression_main.csv", "M2 fin_neg", "CAR[0,3] – chính"), ("regression_robustness.csv", "CAR[0,5]", "CAR[0,5]"),
           ("regression_robustness.csv", "CAR[0,10]", "CAR[0,10]"), ("regression_robustness.csv", "Market-adjusted", "Market-adjusted [0,3]"),
           ("regression_robustness.csv", "BHAR (LM 2011)", "BHAR [0,3]"), ("regression_robustness.csv", "Placebo −60 phiên", "Placebo (lùi 60 phiên)")]


@app.get("/api/{mkt}/coefficients")
def coefficients(mkt: str):
    """Hệ số fin_neg_z (+1 độ lệch chuẩn tone tiêu cực) theo từng biến phụ thuộc, kèm khoảng tin cậy 95%."""
    _check(mkt)
    em = _csv("outputs", mkt, "economic_magnitude.csv")
    rows = []
    for bang, mo_hinh, label in WINDOWS:
        r = em[(em.bang == bang) & (em.mo_hinh == mo_hinh) & (em.bien == "fin_neg_z")] if em is not None else []
        if len(r):
            r = r.iloc[0]; st = r.sao if isinstance(r.sao, str) else ""
            rows.append({"label": label, "coef_pp": 100 * r.he_so, "lo_pp": 100 * (r.he_so - 1.96 * r.se),
                         "hi_pp": 100 * (r.he_so + 1.96 * r.se), "stars": st, "sig": _stars_to_p(st), "main": "chính" in label,
                         "placebo": "Placebo" in label})
    return rows


# ----------------------------------------------------------------------------- tra cứu văn bản
@functools.lru_cache(maxsize=2)
def _documents(mkt: str) -> pd.DataFrame:
    docs = _csv("data", mkt, "processed", "docs.csv")
    tone = _csv("data", mkt, "processed", "tone_panel.csv", dtype={"industry": str})
    ap = _csv("data", mkt, "processed", "analysis_panel.csv", usecols=lambda c: c in ("doc_id", "car_0_3", "car_0_5", "tone_grp"))
    df = docs[docs.flag.eq("ok")].merge(tone[["doc_id", "fin_neg", "fin_pos", "fin_net", "gen_neg", "n_words"]], on="doc_id")
    df = df.merge(ap, on="doc_id", how="left")
    df["net_pct_rank"] = 100 * df.fin_net.rank(pct=True)
    if mkt == "vn":
        lm = _csv("data", "vn", "processed", "letters_meta.csv")
        if lm is not None:
            lm["doc_id"] = lm.ticker + "_" + lm.year.astype(str)
            keep = [c for c in ("doc_id", "start_page", "end_page", "method", "locate", "ocr_quality_before", "ocr_quality_after") if c in lm]
            df = df.merge(lm[keep], on="doc_id", how="left")
    return df.sort_values(["ticker", "year"], ascending=[True, False]).reset_index(drop=True)


@app.get("/api/{mkt}/documents")
def documents(mkt: str):
    _check(mkt)
    df = _documents(mkt)
    cols = [c for c in ("doc_id", "ticker", "year", "group", "event_date", "fin_net", "fin_neg", "tone_grp", "car_0_3") if c in df]
    return _records(df[cols])


# ----------------------------------------------------------------------------- "Bản đọc": chỉ đổi cách HIỂN THỊ văn bản
# Giữ nguyên độ dài và vị trí ký tự của văn bản đã chấm (để vị trí tô màu không lệch): xuống dòng giữa câu → khoảng
# trắng; khối rác → trả về dưới dạng khoảng ẩn [đầu, cuối, nhãn] để giao diện thu gọn. Số đếm vẫn tính trên văn bản đầy đủ.
XBRL_TOK = re.compile(r"(?:\d{10}|\d{4}-\d{2}-\d{2}|--\d{2}-\d{2}|[A-Z][A-Z0-9_\-]*:[A-Z0-9_\-\.]+)$", re.IGNORECASE)
WORD2 = re.compile(r"[^\W\d_]{2,}")
LINE_END = re.compile(r"[.!?:;…”\"»)]\s*$")
LINE_START = re.compile(r"\s*[A-ZÀ-Ỹ0-9\-–•*(“\"+]")


def _xbrl_ranges(text):
    """Khối context XBRL lọt vào văn bản 10-K (mã CIK, ngày, US-GAAP:…MEMBER): ≥ 20 mục liền nhau."""
    toks = [(m.start(), m.end(), m.group()) for m in re.finditer(r"\S+", text)]
    out, i = [], 0
    while i < len(toks):
        if not XBRL_TOK.match(toks[i][2]):
            i += 1
            continue
        j, last, miss, k = i, i, 0, 1
        while j + 1 < len(toks) and miss <= 2:
            j += 1
            if XBRL_TOK.match(toks[j][2]):
                last, miss, k = j, 0, k + 1
            else:
                miss += 1
        if k >= 20:
            out.append([toks[i][0], toks[last][1], f"khối dữ liệu máy XBRL ({k:,} mục)".replace(",", ".")])
        i = last + 1
    return out


def _junk_line(s: str) -> bool:
    """Dòng rác OCR: không có từ nào ≥ 2 chữ cái (ký tự lẻ, số trang, mảnh logo/khung hình)."""
    return bool(s.strip()) and not WORD2.search(s)


def readable_view(text: str, lang: str):
    hidden = _xbrl_ranges(text) if lang == "en" else []
    chars, scrambled = list(text), False
    if lang == "vi":
        pos, lines = 0, []
        for ln in text.split("\n"):
            lines.append((pos, pos + len(ln), ln)); pos += len(ln) + 1
        run = []
        for s, e, ln in lines + [(len(text), len(text), "x" * 3)]:          # dòng gác cuối để đóng cụm
            if _junk_line(ln):
                run.append((s, e))
            elif ln.strip() and run:
                hidden.append([run[0][0], min(run[-1][1] + 1, len(text)), f"{len(run)} dòng nhiễu OCR"])
                run = []
        # PDF nhiều cột: lớp chữ đọc theo hàng ngang nên dòng của các cột xen kẽ nhau → nhiều "đoạn" bắt đầu bằng chữ thường.
        paras = [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) > 20]
        low = sum(bool(re.match(r"[a-zà-ỹđ]", p)) for p in paras) / max(len(paras), 1)
        scrambled = len(paras) >= 8 and low > 0.3
        # nối dòng bị ngắt giữa câu: giữ xuống dòng sau dấu kết câu + dòng sau viết hoa, và sau dòng tiêu đề in hoa.
        # Dòng cách nhau bởi dòng trống chỉ nối khi dòng sau bắt đầu bằng chữ thường (và văn bản không bị xen cột).
        body = [(s, e, ln) for s, e, ln in lines if ln.strip() and not _junk_line(ln)]
        for (s1, e1, a), (s2, e2, b) in zip(body, body[1:]):
            heading = a.strip().upper() == a.strip() and len(WORD2.findall(a)) <= 12
            if heading or (LINE_END.search(a) and LINE_START.match(b)):
                continue
            gap = text[e1:s2]
            if gap.count("\n") == 1 or (not scrambled and re.match(r"\s*[a-zà-ỹđ]", b)):
                for k in range(e1, s2):
                    chars[k] = " "
    hidden.sort()
    return {"text": "".join(chars), "hidden": hidden, "scrambled": scrambled}


def _read_text(mkt, name):
    p = ROOT / "data" / mkt / "interim" / "text" / str(name)
    if not name or not isinstance(name, str) or not p.exists():
        return None
    import gzip
    return gzip.open(p, "rt", encoding="utf-8").read() if p.suffix == ".gz" else p.read_text(encoding="utf-8")


@app.get("/api/{mkt}/document")
def document(mkt: str, doc_id: str = Query(...), section: str = Query("main")):
    _check(mkt)
    df = _documents(mkt)
    hit = df[df.doc_id == doc_id]
    if hit.empty:
        raise HTTPException(404, "Không có văn bản này trong mẫu")
    r = hit.iloc[0]
    meta = {k: (None if pd.isna(v) else v) for k, v in r.to_dict().items()}
    meta["has_alt"] = isinstance(r.get("text_alt"), str)
    name = r.text_alt if section == "alt" and meta["has_alt"] else r.text_main
    text = _read_text(mkt, name)
    if text is None:
        return {"meta": meta, "available": False, "analysis": None}
    try:
        analysis, err = analyze(text, "vi" if mkt == "vn" else "en"), None
        analysis["readable"] = readable_view(analysis["text"], analysis["lang"])
    except HTTPException as e:
        analysis, err = None, e.detail
    return {"meta": meta, "available": True, "section": "alt" if name == r.get("text_alt") else "main",
            "analysis": analysis, "error": err}


class AnalyzeRequest(BaseModel):
    text: str
    lang: str = "vi"          # 'vi' | 'en'


@app.post("/api/analyze")
def analyze_text(req: AnalyzeRequest):
    if not req.text.strip():
        raise HTTPException(400, "Hãy nhập văn bản")
    if req.lang not in ("vi", "en"):
        raise HTTPException(400, "Ngôn ngữ phải là 'vi' hoặc 'en'")
    if len(req.text) > 200_000:
        raise HTTPException(413, "Văn bản quá dài (tối đa 200.000 ký tự)")
    return analyze(req.text, req.lang)


# ----------------------------------------------------------------------------- tin tức CafeF quanh ngày công bố (v05_news.py)
@functools.lru_cache(maxsize=1)
def _news():
    df = _csv("data", "vn", "processed", "news_cafef_events.csv")
    return df if df is not None else pd.DataFrame()


@app.get("/api/vn/news")
def news(doc_id: str = Query(...)):
    df = _news()
    if df.empty:
        return {"available": False, "items": []}
    d = df[df.doc_id == doc_id]
    topics = [c for c in ("kqkd", "dhdcd", "co_tuc", "bctn", "nhan_su", "gd_noi_bo", "chung_quyen") if c in df]
    items = [{"offset": int(r.offset), "published_at": r.published_at, "kind": r.kind, "title": r.title, "url": r.url,
              "topics": [t for t in topics if bool(getattr(r, t))]} for r in d.itertuples()]
    ev = _csv("outputs", "vn", "news_event_counts.csv")
    hit = ev[ev.doc_id == doc_id] if ev is not None and "cafef_gap" in ev else pd.DataFrame()
    cov = _csv("outputs", "vn", "news_coverage_monthly.csv")
    gaps = cov.loc[cov.hong.astype(bool), "thang"].tolist() if cov is not None else []
    return {"available": True, "items": items, "day0": None if d.empty else str(d.day0.iloc[0]),
            "event": not hit.empty, "cafef_gap": bool(hit.iloc[0].cafef_gap) if not hit.empty else False, "gap_months": gaps,
            "crawled_at": None if df.empty else str(df.crawled_at.max()), "source": "CafeF – cafef.vn (mục Tin tức của mã)"}


# ----------------------------------------------------------------------------- sửa OCR bằng AI (tầng AI của pipeline)
def _tesseract_env():
    """Dashboard chạy độc lập với PowerShell của người dùng → tự tìm Tesseract và gói tiếng Việt nếu chưa cấu hình."""
    import os, shutil
    exe = pathlib.Path(r"C:\Program Files\Tesseract-OCR")
    if not shutil.which("tesseract") and (exe / "tesseract.exe").exists():
        os.environ["PATH"] = f"{exe}{os.pathsep}{os.environ.get('PATH', '')}"
    if not os.environ.get("TESSDATA_PREFIX"):
        for d in (pathlib.Path.home() / "tessdata", exe / "tessdata"):
            if (d / "vie.traineddata").exists():
                os.environ["TESSDATA_PREFIX"] = str(d)
                break


@functools.lru_cache(maxsize=1)
def _v03():
    _tesseract_env()
    from vn import v03_extract_letter as v03          # page_text, render_png, cấu hình vn.extract
    return v03


@functools.lru_cache(maxsize=1)
def _llm():
    from common import CFG
    from textkit.llm_client import LLMClient
    return LLMClient(CFG["vn"]["extract"]["llm"])      # 1 client cho cả phiên: cache, trần lượt gọi, nhịp gọi dùng chung


def _letter(doc_id: str):
    lm = _csv("data", "vn", "processed", "letters_meta.csv")
    lm["doc_id"] = lm.ticker + "_" + lm.year.astype(str)
    hit = lm[(lm.doc_id == doc_id) & lm.flag.isin(["ok", "too_long", "too_short"])]
    if hit.empty or pd.isna(hit.iloc[0].start_page):
        raise HTTPException(404, "Không có thư này trong mẫu")
    return hit.iloc[0]


def _forced_ocr(ticker, year) -> bool:
    mp = _csv("data", "vn", "processed", "manual_pages.csv")
    if mp is None or "force_ocr" not in mp:
        return False
    r = mp[(mp.ticker == ticker) & (mp.year == year)]
    return bool(len(r) and r.iloc[0].force_ocr == 1)


REASON_VI = {
    "accepted": "Nhận bản AI: chất lượng chữ không giảm",
    "quality_not_improved": "Giữ bản cũ: chất lượng chữ của bản AI không cao hơn",
    "rewrite_suspected": "Giữ bản cũ: bản AI khác bản OCR quá nhiều (nghi AI viết lại)",
    "llm_empty": "Giữ bản cũ: AI trả về rỗng",
}


def _reason_vi(reason):
    if not isinstance(reason, str):
        return None
    for k, v in REASON_VI.items():
        if reason.startswith(k):
            return v
    return reason


@app.get("/api/vn/pages")
def letter_pages(doc_id: str = Query(...)):
    """Các trang của thư + quyết định của tầng AI trong lần chạy pipeline gần nhất (llm_pages.csv)."""
    from common import CFG
    L = CFG["vn"]["extract"]["llm"]
    r = _letter(doc_id)
    log = _csv("data", "vn", "processed", "llm_pages.csv")
    log = log[(log.ticker == r.ticker) & (log.year == r.year)] if log is not None else pd.DataFrame()
    pages = []
    for p in range(int(r.start_page), int(r.end_page) + 1):
        row = log[log.page == p]
        g = (lambda k: None if row.empty or pd.isna(row.iloc[0].get(k)) else row.iloc[0].get(k))
        pages.append({"page": p, "source": g("source"), "q_before": g("q_before"), "q_after": g("q_after"),
                      "sent": g("decision") is not None, "decision": g("decision"), "reason": _reason_vi(g("reason")),
                      "mode": g("mode")})
    pdf_ok = (ROOT / "data" / "vn" / "raw" / "bctn" / str(r.file)).exists()
    return {"doc_id": doc_id, "pdf_available": pdf_ok, "threshold": L.get("quality_threshold", 0.85), "enabled": bool(L.get("enabled")),
            "has_key": bool(_llm().providers()), "provider": L.get("provider"), "model": L.get(f"model_{L.get('provider')}"),
            "pages": pages}


@functools.lru_cache(maxsize=64)
def _page_png(doc_id: str, page: int, dpi: int) -> bytes:
    r = _letter(doc_id)
    pdf = ROOT / "data" / "vn" / "raw" / "bctn" / r.file
    if not pdf.exists():
        raise HTTPException(404, "Máy chủ này không có PDF gốc (data/vn/raw không đưa lên git)")
    import fitz                                        # chỉ cần khi có PDF (máy chủ online không cài PyMuPDF)
    doc = fitz.open(pdf)
    if not 1 <= page <= doc.page_count:
        raise HTTPException(404, "Trang không tồn tại")
    import io
    from PIL import Image
    pg = doc[page - 1]
    pix = pg.get_pixmap(dpi=min(dpi, int(1600 / (pg.rect.width / 72))))          # rộng tối đa ~1.600 px
    buf = io.BytesIO()
    Image.frombytes("RGB", (pix.width, pix.height), pix.samples).save(buf, "JPEG", quality=82)
    return buf.getvalue()


@app.get("/api/vn/page_image")
def page_image(doc_id: str = Query(...), page: int = Query(...)):
    from fastapi.responses import Response
    return Response(_page_png(doc_id, page, 150), media_type="image/jpeg", headers={"Cache-Control": "max-age=3600"})


def _diff(a: str, b: str):
    """So sánh theo từ: trả 2 danh sách đoạn [chữ, loại] cho bản cũ (same/del) và bản AI (same/ins)."""
    import difflib
    ta, tb = re.findall(r"\S+|\s+", a), re.findall(r"\S+|\s+", b)
    wa, wb = [t for t in ta if not t.isspace()], [t for t in tb if not t.isspace()]
    sm = difflib.SequenceMatcher(None, [w.lower() for w in wa], [w.lower() for w in wb], autojunk=False)
    mark_a, mark_b = ["same"] * len(wa), ["same"] * len(wb)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != "equal":
            for i in range(i1, i2): mark_a[i] = "del"
            for j in range(j1, j2): mark_b[j] = "ins"

    def build(tokens, marks):
        # loại của từng token; khoảng trắng nằm giữa hai từ cùng loại nhận loại đó (để gộp thành một đoạn)
        kinds, k = [], 0
        for t in tokens:
            kinds.append(None if t.isspace() else marks[k]); k += 0 if t.isspace() else 1
        for i, t in enumerate(kinds):
            if t is None:
                prev = next((x for x in reversed(kinds[:i]) if x), "same")
                nxt = next((x for x in kinds[i + 1:] if x), "same")
                kinds[i] = prev if prev == nxt else "same"
        out = []
        for t, kind in zip(tokens, kinds):
            if out and out[-1][1] == kind:
                out[-1][0] += t
            else:
                out.append([t, kind])
        return out
    return build(ta, mark_a), build(tb, mark_b)


class OcrFixRequest(BaseModel):
    doc_id: str
    page: int
    mode: str = "vision"       # 'vision' | 'text_fix'


@app.post("/api/vn/ocr_fix")
def ocr_fix(req: OcrFixRequest):
    """Chạy đúng tầng AI của pipeline cho 1 trang: chép nguyên văn (temperature 0, có cache), chấm chất lượng trước/sau,
    áp quy tắc decide(). CHỈ ĐỂ XEM – không ghi đè văn bản đã trích; muốn áp vào dữ liệu: v03_extract_letter.py --llm."""
    from common import CFG
    from textkit.llm_client import BudgetExceeded, decide, similarity
    from textkit.ocr_quality import quality_score
    if req.mode not in ("vision", "text_fix"):
        raise HTTPException(400, "Chế độ phải là 'vision' hoặc 'text_fix'")
    L = CFG["vn"]["extract"]["llm"]
    r = _letter(req.doc_id)
    if not int(r.start_page) <= req.page <= int(r.end_page):
        raise HTTPException(400, "Trang không thuộc thư")
    pdf = ROOT / "data" / "vn" / "raw" / "bctn" / r.file
    if not pdf.exists():
        raise HTTPException(503, "Máy chủ này không có PDF gốc (data/vn/raw, ~11 GB, không đưa lên git) nên không chạy được AI. "
                                 "Dùng tính năng này trên máy có dữ liệu: powershell -ExecutionPolicy Bypass -File dashboard\\run.ps1")
    client = _llm()
    if not client.providers():
        raise HTTPException(400, "Chưa có API key. Tạo file .env ở thư mục gốc repo với dòng GEMINI_API_KEY=... "
                                 "(lấy miễn phí tại https://aistudio.google.com/apikey) rồi khởi động lại dashboard.")
    import fitz
    v03 = _v03()
    doc = fitz.open(pdf)
    before, source = v03.page_text(doc, req.page - 1, r.lang, force_ocr=_forced_ocr(r.ticker, r.year))
    if source == "text_ocr_fail":
        raise HTTPException(500, "Không chạy được Tesseract để lấy bản OCR của trang (kiểm tra cài đặt Tesseract + gói 'vie').")
    q_before = quality_score(before)
    png = v03.render_png(doc[req.page - 1], L.get("dpi", 200))
    mode, note = req.mode, None
    try:
        try:
            out = client.transcribe_page(png, before, mode)
        except Exception as e:
            if mode == "vision" and "RECITATION" in str(e) and L.get("recitation_fallback") == "text_fix" and before.strip():
                mode, note = "text_fix", "Gemini từ chối chép nguyên văn (RECITATION) → đã chuyển sang chế độ sửa lỗi ký tự trên bản OCR."
                out = client.transcribe_page(png, before, mode)
            else:
                raise
    except BudgetExceeded as e:
        raise HTTPException(429, f"Đã chạm trần số lượt gọi của phiên ({e}). Khởi động lại dashboard để đặt lại.")
    except Exception as e:
        raise HTTPException(502, f"Gọi AI không thành công: {str(e)[:300]}")
    ai = out["page_text"]
    q_ai = quality_score(ai)
    ok, why = decide(mode, before, ai, q_before, q_ai, L)
    d_before, d_ai = _diff(before, ai)
    return {"page": req.page, "mode": mode, "note": note, "source": source,
            "before": d_before, "ai": d_ai, "q_before": q_before, "q_ai": q_ai,
            "similarity": similarity(before, ai), "accepted": ok, "reason": _reason_vi(why),
            "threshold": L.get("quality_threshold", 0.85), "provider": out.get("provider"), "model": out.get("model"),
            "cached": bool(out.get("cached")), "is_letter_page": out.get("is_chairman_letter"),
            "calls_this_session": client.calls}


# ----------------------------------------------------------------------------- dữ liệu & chất lượng
@app.get("/api/quality")
def quality():
    funnels = {m: _records(_csv("outputs", m, "sample_funnel.csv")) for m in MARKETS}
    ev = _csv("outputs", "vn", "ocr_eval.csv")
    pooled = _records(ev[ev.page.astype(str).str.startswith("GỘP")]) if ev is not None else []
    llm = _csv("outputs", "vn", "llm_ocr_summary.csv")
    llm_map = dict(zip(llm.chi_so.str.strip(), llm.gia_tri)) if llm is not None else {}
    pick = lambda prefix: next((v for k, v in llm_map.items() if k.startswith(prefix)), None)
    return {"funnels": funnels, "ocr_eval": pooled,
            "llm": {"pages_total": pick("Trang thuộc thư"), "pages_sent": pick("Trang gửi AI"),
                    "pages_used": pick("Trang nhận bản AI"), "docs_used": pick("Văn bản có ≥ 1 trang"),
                    "cost_usd": pick("Tổng chi phí")}}


# ----------------------------------------------------------------------------- trang Báo cáo: gom số liệu từ outputs/
def _kv(*parts) -> dict:
    """File 2 cột (chỉ số, giá trị) → dict; khóa đã bỏ khoảng trắng đầu dòng."""
    df = _csv(*parts)
    if df is None:
        return {}
    df.columns = ["k", "v"]
    out = {}
    for k, v in zip(df.k.astype(str).str.strip(), df.v):
        try:
            out[k] = float(v)
        except (TypeError, ValueError):
            out[k] = v
    return out


def _coef_cell(s):
    """'−0.0005 (0.0016)' / '0.0025* (0.0015)' → {coef, se, stars}."""
    m = re.match(r"\s*(-?[\d.]+)(\**)\s*\((-?[\d.]+)\)", str(s))
    return {"coef": float(m.group(1)), "stars": m.group(2), "se": float(m.group(3))} if m else None


def _corr(mkt):
    p = ROOT / "outputs" / mkt / "dictionary_comparison.txt"
    m = re.search(r"fin_neg\s+1\.000\s+([\d.]+)", p.read_text(encoding="utf-8")) if p.exists() else None
    return float(m.group(1)) if m else None


def _effect(name):
    """outputs/vn/{llm_ocr_effect,page_fix_effect}.csv: hệ số trước/sau cho các mô hình chính."""
    df = _csv("outputs", "vn", name)
    if df is None:
        return []
    keep = [("M2 fin_neg", "fin_neg_z"), ("M3 gen_neg", "gen_neg_z"), ("M5 net+unc", "fin_unc_z"), ("CAR[0,5]", "fin_neg_z"),
            ("CAR[0,10]", "fin_neg_z"), ("Placebo −60 phiên", "fin_neg_z")]
    rows = [df[(df.mo_hinh == m) & (df.bien == b)] for m, b in keep]
    return _records(pd.concat([r for r in rows if len(r)]))


@app.get("/api/report")
def report():
    """Mọi con số cho trang Báo cáo – đọc từ outputs/ (cùng nguồn với RESULTS.md), không tính lại kết quả."""
    out = {"overview": overview(), "markets": {}}
    for mkt in MARKETS:
        desc = _csv("outputs", mkt, "tone_descriptive.csv")
        desc = {r[0]: {"mean": r.mean, "std": r.std} for r in desc.rename(columns={desc.columns[0]: "v"}).itertuples(index=False)} if desc is not None else {}
        em = _csv("outputs", mkt, "economic_magnitude.csv")
        m4 = {}
        if em is not None:
            for r in em[em.mo_hinh == "M4 đối đầu"].itertuples():
                m4[r.bien] = {"coef": r.he_so, "se": r.se, "stars": r.sao if isinstance(r.sao, str) else ""}
        ct = _csv("outputs", mkt, "car_tests.csv")
        asm = _kv("outputs", mkt, "assumption_tests.csv")
        out["markets"][mkt] = {
            "funnel": _records(_csv("outputs", mkt, "sample_funnel.csv")),
            "coverage": _records(_csv("outputs", mkt, "coverage_by_year.csv")),
            "tone_desc": desc,
            "tone_by_year": _records(_csv("outputs", mkt, "tone_by_year.csv")),
            "noise_pct": _noise_pct(mkt), "corr_fin_gen": _corr(mkt),
            "misclassified": _records(_csv("outputs", mkt, "misclassified_general_neg.csv").head(10)[["word", "share_pct", "in_fin_negative"]]),
            "m4": m4,
            "n_reg": overview().get(mkt, {}).get("n_reg"),
            "car_tests": _records(ct),
            "car_by_tone": car_by_tone(mkt),
            "caar": caar(mkt),
            "coefficients": coefficients(mkt),
            "diag": _kv("outputs", mkt, "event_study_diag.csv"),
            "assumptions": asm,
        }
    # Mỹ: 10-K trùng công bố KQKD (kiểm tra bổ sung)
    eo = _csv("outputs", "us", "earnings_overlap.csv")
    rx = _csv("outputs", "us", "regression_excl_earnings.csv")
    if eo is not None:
        ov = eo.overlap.astype(bool)
        out["markets"]["us"]["earnings"] = {
            "n": int(len(eo)), "n_overlap": int(ov.sum()),
            "abs_car_overlap_pct": 100 * eo.car_0_3[ov].abs().mean(), "abs_car_other_pct": 100 * eo.car_0_3[~ov].abs().mean(),
            "excl": _coef_cell(rx.set_index(rx.columns[0]).loc["fin_neg_z"].iloc[2]) if rx is not None else None}
    # VN: tầng AI sửa OCR, rà trang, độ chính xác OCR, tin tức CafeF
    ev = _csv("outputs", "vn", "ocr_eval.csv")
    tone_dev = _csv("outputs", "vn", "ocr_eval_tone.csv")
    out["vn_extra"] = {
        "llm": _kv("outputs", "vn", "llm_ocr_summary.csv"),
        "ocr_eval": _records(ev[ev.page.astype(str).str.startswith("GỘP")]) if ev is not None else [],
        "ocr_tone": _records(tone_dev[tone_dev.mae_fin_net.notna()][["method", "mae_fin_net", "n_pages"]]) if tone_dev is not None else [],
        "llm_effect": _effect("llm_ocr_effect.csv"),
        "page_fix": _effect("page_fix_effect.csv"),
        "news": _kv("outputs", "vn", "news_summary.csv"),
        "news_monthly": _records(_csv("outputs", "vn", "news_coverage_monthly.csv")),
    }
    return out


# ----------------------------------------------------------------------------- phục vụ giao diện đã build
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = DIST / path
        return FileResponse(f if path and f.is_file() else DIST / "index.html")


if __name__ == "__main__":
    import argparse, threading, webbrowser
    import uvicorn
    ap = argparse.ArgumentParser(description="Dashboard Đồ án 05")
    ap.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.getenv("PORT", 8000)))
    ap.add_argument("--open", action="store_true", help="tự mở trình duyệt khi máy chủ sẵn sàng")
    a = ap.parse_args()
    url = f"http://127.0.0.1:{a.port}"
    if not DIST.exists():
        print("Chưa build giao diện (dashboard/frontend/dist). Chạy: npm --prefix dashboard/frontend install && npm --prefix dashboard/frontend run build")
    if a.open:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    print(f"Dashboard: {url}  (Ctrl + C để dừng)")
    uvicorn.run(app, host=a.host, port=a.port, log_level="warning")
