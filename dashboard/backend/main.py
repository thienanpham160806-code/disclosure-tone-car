"""API cho dashboard Đồ án 05 – chỉ ĐỌC kết quả đã có (outputs/, data/*/processed) và chấm tone bằng đúng bộ đếm của
pipeline (src/textkit/scoring.py). Không gọi LLM, không sửa dữ liệu.

Chạy nhanh nhất:  powershell -ExecutionPolicy Bypass -File dashboard\\run.ps1   (tự build giao diện nếu cần, mở trình duyệt)
Hoặc:            .venv\\Scripts\\python dashboard\\backend\\main.py --open     → http://127.0.0.1:8000
"""
import functools, pathlib, re, sys, unicodedata

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
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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


def analyze(text: str, lang: str):
    text = unicodedata.normalize("NFC", text or "")
    if lang == "vi":
        fin, gen = scorers("vi")
        rf, rg = _spans_vi(text, fin), _spans_vi(text, gen)
    else:
        fin, gen, master = scorers("en")
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
    return {"meta": meta, "available": True, "section": "alt" if name == r.get("text_alt") else "main",
            "analysis": analyze(text, "vi" if mkt == "vn" else "en")}


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
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--open", action="store_true", help="tự mở trình duyệt khi máy chủ sẵn sàng")
    a = ap.parse_args()
    url = f"http://127.0.0.1:{a.port}"
    if not DIST.exists():
        print("Chưa build giao diện (dashboard/frontend/dist). Chạy: npm --prefix dashboard/frontend install && npm --prefix dashboard/frontend run build")
    if a.open:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    print(f"Dashboard: {url}  (Ctrl + C để dừng)")
    uvicorn.run(app, host="127.0.0.1", port=a.port, log_level="warning")
