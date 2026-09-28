"""Tiện ích dùng chung: cấu hình, đường dẫn theo thị trường, tên cột CAR, winsorize."""
import os, pathlib, re, unicodedata, yaml
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG = yaml.safe_load(open(ROOT / "config.yaml", encoding="utf-8"))
# Email KHÔNG ghi vào repo: ưu tiên biến môi trường CONTACT_EMAIL, rồi config.local.yaml (nằm trong .gitignore)
_local = ROOT / "config.local.yaml"
if _local.exists():
    CFG.update(yaml.safe_load(open(_local, encoding="utf-8")) or {})
if os.getenv("CONTACT_EMAIL"):
    CFG["contact_email"] = os.environ["CONTACT_EMAIL"]


def P(*a) -> pathlib.Path:
    p = ROOT.joinpath(*a)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def D(mkt: str, *a) -> pathlib.Path:
    """Đường dẫn dữ liệu theo thị trường: D('us','processed','x.csv') → data/us/processed/x.csv"""
    return P("data", mkt, *a)


def O(mkt: str, *a) -> pathlib.Path:
    return P("outputs", mkt, *a)


def K(prefix, lo, hi):
    """Tên cột hợp lệ cho công thức hồi quy: CAR[-1,+1] → car_m1_1."""
    f = lambda x: f"m{-x}" if x < 0 else str(x)
    return f"{prefix}_{f(lo)}_{f(hi)}"


def winsor(s: pd.Series, lo=.01, hi=.99) -> pd.Series:
    q = s.quantile([lo, hi])
    return s.clip(q.iloc[0], q.iloc[1])


def norm_vi(t: str) -> str:
    """Chuẩn hóa Unicode tiếng Việt (NFC), chữ thường, gộp khoảng trắng."""
    t = unicodedata.normalize("NFC", t or "").lower()
    return re.sub(r"\s+", " ", t).strip()
