"""US-3. Giá (yfinance, giá điều chỉnh) + dữ liệu cơ bản từ XBRL companyfacts (miễn phí, thay CRSP/Compustat).

Đầu ra
  data/us/processed/prices.csv.gz   ticker,date,close,volume  (có cả ^GSPC)
  data/us/processed/fundamentals.csv doc_id, shares_out, book_equity
      shares_out  : dei:EntityCommonStockSharesOutstanding có ngày gần nhất ≤ ngày nộp (ghi trên trang bìa 10-K)
      book_equity : us-gaap:StockholdersEquity của kỳ báo cáo gần nhất ≤ ngày nộp
Lưu ý phương pháp: danh sách mã là các công ty đang niêm yết → survivorship bias (ghi vào phần hạn chế).
"""
import json
import pandas as pd
from tqdm import tqdm
from common import CFG, D

C = CFG["us"]


def prices():
    import yfinance as yf
    tks = C["tickers"] + [C["market_symbol"]]
    df = yf.download(tks, start=C["price_start"], auto_adjust=True, progress=False, group_by="ticker", threads=True)
    out = []
    for t in tks:
        if t in df.columns.get_level_values(0):
            x = df[t][["Close", "Volume"]].dropna(subset=["Close"]).reset_index()
            x.columns = ["date", "close", "volume"]; x["ticker"] = t; out.append(x)
    px = pd.concat(out)[["ticker", "date", "close", "volume"]]
    px.to_csv(D("us", "processed", "prices.csv.gz"), index=False)
    print(f"Giá: {px.ticker.nunique()} mã, {px.date.min().date()} → {px.date.max().date()}")


def _facts(js, taxonomy, tag):
    try:
        units = js["facts"][taxonomy][tag]["units"]
    except KeyError:
        return pd.DataFrame(columns=["end", "filed", "val"])
    arr = next(iter(units.values()))
    d = pd.DataFrame(arr)[["end", "filed", "val"]]
    d["end"], d["filed"] = pd.to_datetime(d.end), pd.to_datetime(d.filed)
    return d.sort_values("filed")


def fundamentals():
    docs = pd.read_csv(D("us", "processed", "docs.csv"), parse_dates=["event_date"])
    man = pd.read_csv(D("us", "processed", "manifest.csv"), dtype={"cik": str})[["accession", "cik"]]
    docs = docs.merge(man, left_on="doc_id", right_on="accession")
    rows = []
    for cik, g in tqdm(docs.groupby("cik"), desc="XBRL"):
        f = D("us", "raw", "companyfacts", f"{cik}.json")
        if not f.exists():
            continue
        js = json.loads(f.read_text())
        sh = _facts(js, "dei", "EntityCommonStockSharesOutstanding")
        eq = _facts(js, "us-gaap", "StockholdersEquity")
        for r in g.itertuples():
            s = sh[sh.filed <= r.event_date]; e = eq[(eq.filed <= r.event_date)]
            rows.append(dict(doc_id=r.doc_id, shares_out=s.val.iloc[-1] if len(s) else None,
                             book_equity=e.sort_values("end").val.iloc[-1] if len(e) else None))
    fd = pd.DataFrame(rows)
    fd.to_csv(D("us", "processed", "fundamentals.csv"), index=False)
    print(f"Fundamentals: {fd.shares_out.notna().sum()} có số CP, {fd.book_equity.notna().sum()} có vốn CSH / {len(fd)}")


def main():
    prices(); fundamentals()


if __name__ == "__main__":
    main()
