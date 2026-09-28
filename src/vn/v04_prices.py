"""B5. Giá đóng cửa điều chỉnh + khối lượng cho các mã và VN-Index.
price_source = vnstock  : vnstock Quote(...).history (nguồn VCI)
price_source = cafef_csv: file CSV CafeF <Ticker>,<DTYYYYMMDD>,<Open>,<High>,<Low>,<Close>,<Volume>
                          (có BOM, CRLF, không sắp xếp theo ngày, có dòng trùng → xử lý bên dưới)
                          CẢNH BÁO: file AmiBroker chỉ chứa lịch sử trên SÀN HIỆN TẠI → mất dữ liệu trước khi chuyển
                          sàn (48/100 mã phủ <90% phiên từ 2016) – xem CHANGELOG_RUN #15
price_source = cafef_hybrid: cafef_csv + lấp lịch sử trước khi chuyển sàn bằng endpoint "Lịch sử giá" của CafeF
                          (GiaDieuChinh, KhoiLuongKhopLenh; 20 dòng/trang, ~3 tháng/lần gọi), cache data/vn/raw/prices_web/
Đầu ra: data/processed/prices.csv.gz (ticker,date,close,volume)
"""
import glob
import pandas as pd
from tqdm import tqdm
from common import CFG, P, D
V = CFG["vn"]
HIST = "https://cafef.vn/du-lieu/Ajax/PageNew/DataHistory/PriceHistory.ashx"


def from_vnstock(tickers):
    from vnstock import Quote
    out = []
    for tk in tqdm(tickers, desc="Giá"):
        try:
            df = Quote(symbol=tk, source="VCI").history(start=V["price_start"],
                                                          end=pd.Timestamp.today().strftime("%Y-%m-%d"), interval="1D")
            out.append(df.rename(columns={"time": "date"})[["date", "close", "volume"]].assign(ticker=tk))
        except Exception as e:
            print(f"  ! {tk}: {e}")
    return pd.concat(out)


def from_cafef(tickers):
    fs = glob.glob(str(P(V["cafef_csv_dir"], "x").parent / "**" / "*.csv"), recursive=True)   # file giải nén có thể nằm trong thư mục con
    df = pd.concat(pd.read_csv(f, encoding="utf-8-sig") for f in fs)
    df.columns = [c.strip("<>").lower() for c in df.columns]
    df = df.rename(columns={"dtyyyymmdd": "date"})
    df["date"] = pd.to_datetime(df.date.astype(str), format="%Y%m%d")
    return df[df.ticker.isin(tickers)][["ticker", "date", "close", "volume"]]


def _web_range(s, tk, a, b, months=2):
    """Giá điều chỉnh của `tk` trong [a, b] từ endpoint Lịch sử giá: API chỉ phủ ~3 tháng/lần gọi và trả
    20 dòng/trang (bỏ qua PageSize) → cửa sổ `months` tháng + phân trang. Trả (DataFrame, danh sách lỗi)."""
    from vn.http import polite_get
    rows, bad = [], []
    for a0 in pd.date_range(a.to_period("M").to_timestamp(), b, freq=f"{months}MS"):
        b0 = min(a0 + pd.DateOffset(months=months) - pd.Timedelta(days=1), b)
        page, got = 1, []
        while True:
            r = polite_get(s, HIST, params=dict(Symbol=tk, StartDate=a0.strftime("%m/%d/%Y"), EndDate=b0.strftime("%m/%d/%Y"),
                                                PageIndex=page, PageSize=20))
            js = (r.json().get("Data") or {}) if r is not None else None
            if js is None:
                bad.append((tk, a0.date(), "request_fail")); break
            data = js.get("Data") or []; got += data; total = js.get("TotalCount", 0)
            if not data or len(got) >= total:
                break
            page += 1
        if len(got) != total:
            bad.append((tk, a0.date(), f"count {len(got)}≠{total}"))
        rows += [dict(date=pd.to_datetime(x["Ngay"], format="%d/%m/%Y"), close=x["GiaDieuChinh"], volume=x["KhoiLuongKhopLenh"])
                 for x in got]
    return pd.DataFrame(rows, columns=["date", "close", "volume"]).assign(ticker=tk), bad


def from_cafef_hybrid(tickers):
    """File AmiBroker (cafef_csv) + lấp phần lịch sử trước khi chuyển sàn bằng endpoint Lịch sử giá (CHANGELOG_RUN #19).
    Hai nguồn trùng khớp khi cùng ngày (kiểm tra ACB/VNM/VNINDEX: lệch ≤ 0,035%, KL bằng nhau). Với mỗi mã:
    cont_start = đầu đoạn dữ liệu AmiBroker LIÊN TỤC cuối cùng (khoảng trống > 15 ngày lịch coi là đứt đoạn);
    nếu cont_start > price_start + 15 ngày → tải web [price_start, cont_start + 1 tháng], dùng web cho ngày < cont_start."""
    from vn.http import session
    ami = from_cafef(tickers)
    ami["date"] = pd.to_datetime(ami.date)
    s, out, bad, log = session(), [], [], []
    p0 = pd.Timestamp(V["price_start"])
    for tk in tqdm(tickers, desc="Giá (AmiBroker + web)"):
        a = ami[ami.ticker == tk].sort_values("date")
        gaps = a.date.diff().dt.days
        cont = a.date[gaps > 15].max() if (gaps > 15).any() else (a.date.min() if len(a) else pd.Timestamp.today())
        if len(a) and cont <= p0 + pd.Timedelta(days=15):
            out.append(a); continue
        f = D("vn", "raw", "prices_web", f"{tk}.csv")
        if f.exists():
            w = pd.read_csv(f, parse_dates=["date"])
        else:
            w, b = _web_range(s, tk, p0, cont + pd.DateOffset(months=1)); bad += b
            if not b:
                w.to_csv(f, index=False)
        ov = w.merge(a, on="date", suffixes=("_w", "_a"))
        dev = (ov.close_w / ov.close_a - 1).abs().max() if len(ov) else float("nan")
        log.append(dict(ticker=tk, ami_rows=len(a), cont_start=cont.date(), web_rows=len(w), overlap=len(ov), max_dev=dev))
        out.append(pd.concat([w[w.date < cont].assign(ticker=tk), a[a.date >= cont]]))
    lg = pd.DataFrame(log); lg.to_csv(D("vn", "processed", "prices_splice_log.csv"), index=False)
    print(f"Lấp lịch sử cho {len(lg)} mã; lệch giá tại đoạn chồng lấn: max {lg.max_dev.max():.4%}, "
          f"số mã lệch > 0,5%: {(lg.max_dev > .005).sum()}")
    if bad:
        print(f"  ! {len(bad)} cửa sổ lỗi, ví dụ: {bad[:5]}")
        pd.DataFrame(bad, columns=["ticker", "window_start", "issue"]).to_csv(D("vn", "processed", "prices_web_issues.csv"), index=False)
    return pd.concat(out)


def main():
    tickers = pd.read_csv(P(V["tickers_file"])).ticker.tolist() + [V["market_symbol"]]
    src = {"vnstock": from_vnstock, "cafef_csv": from_cafef, "cafef_hybrid": from_cafef_hybrid}[V["price_source"]]
    df = src(tickers)
    df["date"] = pd.to_datetime(df.date).dt.normalize()
    df = df.drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"])
    df[["ticker", "date", "close", "volume"]].to_csv(D("vn", "processed", "prices.csv.gz"), index=False)
    print(f"{df.ticker.nunique()} mã, {len(df):,} dòng, {df.date.min().date()} → {df.date.max().date()}")


if __name__ == "__main__":
    main()
