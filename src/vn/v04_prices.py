"""B5. Giá đóng cửa điều chỉnh + khối lượng cho các mã và VN-Index.
price_source = vnstock  : vnstock Quote(...).history (nguồn VCI)
price_source = cafef_csv: file CSV CafeF <Ticker>,<DTYYYYMMDD>,<Open>,<High>,<Low>,<Close>,<Volume>
                          (có BOM, CRLF, không sắp xếp theo ngày, có dòng trùng → xử lý bên dưới)
Đầu ra: data/processed/prices.csv.gz (ticker,date,close,volume)
"""
import glob
import pandas as pd
from tqdm import tqdm
from common import CFG, P, D
V = CFG["vn"]


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
    fs = glob.glob(str(P(V["cafef_csv_dir"], "*.csv")))
    df = pd.concat(pd.read_csv(f, encoding="utf-8-sig") for f in fs)
    df.columns = [c.strip("<>").lower() for c in df.columns]
    df = df.rename(columns={"dtyyyymmdd": "date"})
    df["date"] = pd.to_datetime(df.date.astype(str), format="%Y%m%d")
    return df[df.ticker.isin(tickers)][["ticker", "date", "close", "volume"]]


def main():
    tickers = pd.read_csv(P(V["tickers_file"])).ticker.tolist() + [V["market_symbol"]]
    df = from_vnstock(tickers) if V["price_source"] == "vnstock" else from_cafef(tickers)
    df["date"] = pd.to_datetime(df.date).dt.normalize()
    df = df.drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"])
    df.to_csv(D("vn", "processed", "prices.csv.gz"), index=False)
    print(f"{df.ticker.nunique()} mã, {len(df):,} dòng, {df.date.min().date()} → {df.date.max().date()}")


if __name__ == "__main__":
    main()
