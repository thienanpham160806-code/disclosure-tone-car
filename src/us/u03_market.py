"""US-3. Giá (yfinance, giá điều chỉnh) + dữ liệu cơ bản từ XBRL companyfacts (miễn phí, thay CRSP/Compustat).

Đầu ra
  data/us/processed/prices.csv.gz   ticker,date,close,volume,close_split,split  (có cả ^GSPC)
  data/us/processed/fundamentals.csv doc_id, shares_out, shares_adj (quy theo chia tách sau ngày nộp), book_equity
      shares_out  : dei:EntityCommonStockSharesOutstanding có ngày gần nhất ≤ ngày nộp (ghi trên trang bìa 10-K);
                    dự phòng cho công ty nhiều lớp CP: us-gaap WeightedAverageNumberOfSharesOutstandingBasic (năm)
      book_equity : us-gaap:StockholdersEquity của kỳ báo cáo gần nhất ≤ ngày nộp (dự phòng: vốn gồm NCI − NCI)
      Chỉ nhận số liệu có kỳ kết thúc trong 400 ngày trước ngày nộp.
Lưu ý phương pháp: danh sách mã là các công ty đang niêm yết → survivorship bias (ghi vào phần hạn chế).
"""
import json
import pandas as pd
from tqdm import tqdm
from common import CFG, D

C = CFG["us"]


def prices():
    """close = giá điều chỉnh cổ tức + chia tách (tính lợi suất); close_split = giá chỉ điều chỉnh chia tách
    (Yahoo 'Close') và split = tỷ lệ chia tách trong ngày → dùng tính vốn hóa/turnover cho đúng (CHANGELOG_RUN #8)."""
    import yfinance as yf
    tks = C["tickers"] + [C["market_symbol"]]
    df = yf.download(tks, start=C["price_start"], auto_adjust=False, actions=True, progress=False,
                     group_by="ticker", threads=True)
    out = []
    for t in tks:
        if t in df.columns.get_level_values(0):
            x = df[t].reindex(columns=["Adj Close", "Volume", "Close", "Stock Splits"]).dropna(subset=["Adj Close"]).reset_index()
            x.columns = ["date", "close", "volume", "close_split", "split"]; x["ticker"] = t; out.append(x)
    px = pd.concat(out)[["ticker", "date", "close", "volume", "close_split", "split"]]
    px.to_csv(D("us", "processed", "prices.csv.gz"), index=False)
    print(f"Giá: {px.ticker.nunique()} mã, {px.date.min().date()} → {px.date.max().date()}")


def _facts(js, taxonomy, tag):
    try:
        units = js["facts"][taxonomy][tag]["units"]
    except KeyError:
        return pd.DataFrame({c: pd.Series(dtype="datetime64[ns]") for c in ["start", "end", "filed"]} | {"val": pd.Series(dtype=float)})
    arr = next(iter(units.values()))
    d = pd.DataFrame(arr)
    d["start"] = pd.to_datetime(d["start"]) if "start" in d else pd.NaT
    d["end"], d["filed"] = pd.to_datetime(d.end), pd.to_datetime(d.filed)
    return d[["start", "end", "filed", "val"]].sort_values("filed")


FRESH = pd.Timedelta(days=400)   # chỉ nhận số liệu có kỳ kết thúc ≤ 400 ngày trước ngày nộp (tránh dùng số cũ nhiều năm)


def _latest(d, day, annual=False, with_end=False):
    """Giá trị đã công bố đến ngày `day` (kể cả số liệu của chính 10-K này: 'filed' của XBRL có thể là ngày làm việc
    kế tiếp khi hồ sơ được chấp nhận sau giờ), kỳ kết thúc gần nhất và không quá cũ. annual=True: chỉ kỳ ~1 năm."""
    d = d[(d.filed <= day + pd.Timedelta(days=3)) & (d.end <= day) & (d.end > day - FRESH)]
    if annual:
        d = d[(d.end - d.start).dt.days.between(350, 380)]
    r = d.sort_values(["end", "filed"]).iloc[-1] if len(d) else None
    val = None if r is None else r.val
    return (val, None if r is None else r.end) if with_end else val


def fundamentals():
    docs = pd.read_csv(D("us", "processed", "docs.csv"), parse_dates=["event_date"])
    man = pd.read_csv(D("us", "processed", "manifest.csv"), dtype={"cik": str})[["accession", "cik"]]
    docs = docs.merge(man, left_on="doc_id", right_on="accession")
    px = pd.read_csv(D("us", "processed", "prices.csv.gz"), parse_dates=["date"])
    splits = px[px.split.fillna(0) > 0]
    rows = []
    for cik, g in tqdm(docs.groupby("cik"), desc="XBRL"):
        f = D("us", "raw", "companyfacts", f"{cik}.json")
        if not f.exists():
            continue
        js = json.loads(f.read_text())
        sh = _facts(js, "dei", "EntityCommonStockSharesOutstanding")          # trang bìa 10-K
        wa = _facts(js, "us-gaap", "WeightedAverageNumberOfSharesOutstandingBasic")
        cs = _facts(js, "us-gaap", "CommonStockSharesOutstanding")
        eq = _facts(js, "us-gaap", "StockholdersEquity")
        eqn = _facts(js, "us-gaap", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest")
        mi = _facts(js, "us-gaap", "MinorityInterest")
        for r in g.itertuples():
            day = r.event_date
            # Công ty nhiều lớp CP (GOOGL, META, MA, NKE, CMCSA, UPS...) không có dei không-chiều cho các năm gần đây
            # → dự phòng: bình quân gia quyền CP cơ bản của năm tài chính, rồi CP lưu hành trên bảng CĐKT.
            (s, s_end), src = _latest(sh, day, with_end=True), "dei"
            if s is None:
                (s, s_end), src = _latest(wa, day, annual=True, with_end=True), "wavg_basic"
            if s is None:
                (s, s_end), src = _latest(cs, day, with_end=True), "bs_shares"
            # Vốn CSH công ty mẹ; CAT, PG, T, VZ chỉ khai thẻ gồm NCI → trừ lợi ích CĐ không kiểm soát cùng kỳ.
            b, bsrc = _latest(eq, day), "se"
            if b is None:
                b = _latest(eqn, day)
                if b is not None:
                    m = _latest(mi, day); b, bsrc = b - (m or 0), "se_incl_nci_minus_mi"
            # quy số CP về gốc chia tách hiện nay: nhân các lần chia tách SAU ngày của số liệu CP
            sf = splits[(splits.ticker == r.ticker) & (splits.date > (s_end if s is not None else day))].split.prod()
            rows.append(dict(doc_id=r.doc_id, shares_out=s, shares_src=src if s is not None else None,
                             split_factor=sf, shares_adj=s * sf if s is not None else None,
                             book_equity=b, equity_src=bsrc if b is not None else None))
    fd = pd.DataFrame(rows)
    fd.to_csv(D("us", "processed", "fundamentals.csv"), index=False)
    print(f"Fundamentals: {fd.shares_out.notna().sum()} có số CP, {fd.book_equity.notna().sum()} có vốn CSH / {len(fd)}")
    print("Nguồn số CP:", fd.shares_src.value_counts(dropna=False).to_dict(), "| nguồn vốn CSH:",
          fd.equity_src.value_counts(dropna=False).to_dict())


def main():
    prices(); fundamentals()


if __name__ == "__main__":
    main()
