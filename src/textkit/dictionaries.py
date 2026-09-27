"""Nạp 4 từ điển, cùng một định dạng đầu ra: dict[category] -> set(term).

Tiếng Anh (Mỹ)
  • Loughran–McDonald Master Dictionary (SRAF, Notre Dame) – từ điển TÀI CHÍNH.
    Quy tắc chọn cờ theo lm2011-replication (MIT): "nonzero" (mặc định) hoặc "positive"
    (loại các từ bị LM gỡ năm 2020, khớp với LM 10X Summaries). master = mọi từ trong từ điển,
    dùng làm mẫu số N_words đúng phụ lục LM (không đếm tên riêng, mã, lỗi chính tả).
  • Harvard General Inquirer IV-4 – từ điển TỔNG QUÁT (đối chứng ở Mục tiêu 2), lấy file tĩnh
    HIV-4.csv đóng gói trong thư viện pysentiment2 (pip install pysentiment2).
Tiếng Việt
  • dict/fin_vn.csv – từ điển tài chính tiếng Việt do nhóm Việt hóa theo logic LM.
  • VietSentiWordNet 1.3.5 (Vu & Park 2014) – từ điển TỔNG QUÁT tiếng Việt.
"""
from __future__ import annotations
import glob, re
import pandas as pd, requests
from common import P, norm_vi

CATS = ["negative", "positive", "uncertainty", "litigious"]
VSWN_URL = ("https://raw.githubusercontent.com/sonvx/VietSentiWordNet/master/"
            "VietSentiWordNet/dicts/VietSentiWordnet_Ver1.3.5.txt")


def load_lm(rule: str = "nonzero") -> dict[str, set]:
    fs = sorted(glob.glob(str(P("dict", "Loughran-McDonald_MasterDictionary*.csv"))) +
                glob.glob(str(P("dict", "LoughranMcDonald_MasterDictionary*.csv"))))
    if not fs:
        raise SystemExit("Thiếu từ điển LM: tải CSV tại https://sraf.nd.edu/loughranmcdonald-master-dictionary/ "
                         "và đặt vào thư mục dict/")
    d = pd.read_csv(fs[-1])
    d["Word"] = d["Word"].astype(str).str.upper()
    out = {"master": set(d.Word)}
    for c in CATS:
        col = c.capitalize()
        flag = (d[col] != 0) if rule == "nonzero" else (d[col] > 0)
        out[c] = set(d.loc[flag, "Word"])
    return out


def load_harvard() -> dict[str, set]:
    try:
        import pysentiment2, os
        f = os.path.join(os.path.dirname(pysentiment2.__file__), "static", "HIV-4.csv")
    except ImportError:
        f = str(P("dict", "HIV-4.csv"))
    d = pd.read_csv(f, low_memory=False)
    first = lambda s: str(s).split("#")[0].upper()
    return {"negative": set(d.loc[d.Negativ.notna(), "Entry"].map(first)),
            "positive": set(d.loc[d.Positiv.notna(), "Entry"].map(first))}


def load_fin_vn() -> dict[str, set]:
    d = pd.read_csv(P("dict", "fin_vn.csv"))
    return {c: set(d.loc[d.category == c, "word"].map(norm_vi)) for c in CATS}


def load_vswn(thr: float = 0.5) -> dict[str, set]:
    f = P("dict", "VietSentiWordnet_Ver1.3.5.txt")
    if not f.exists():
        f.write_text(requests.get(VSWN_URL, timeout=60).text, encoding="utf-8")
    out = {"negative": set(), "positive": set()}
    for line in f.read_text(encoding="utf-8").splitlines():
        c = line.split("\t")
        if line.startswith("#") or len(c) < 5:
            continue
        ps, ns = float(c[2] or 0), float(c[3] or 0)
        cat = "negative" if ns >= thr and ns > ps else "positive" if ps >= thr and ps > ns else None
        if cat:  # SynsetTerms dạng "bất_lợi#1 không có lợi#2" → tách theo "#số"
            for term in re.split(r"#\d+", c[4]):
                term = norm_vi(term.replace("_", " "))
                if term:
                    out[cat].add(term)
    return out
