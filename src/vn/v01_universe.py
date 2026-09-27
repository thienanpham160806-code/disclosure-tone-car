"""B1. Danh sách mã VN30 + VN100 (VN100 đã bao gồm VN30).
Nguồn: vnstock (Listing.symbols_by_group). Nếu lỗi mạng/phiên bản → tự tạo data/tickers.csv (cột ticker,group).
Lưu ý phương pháp: dùng rổ HIỆN TẠI cho mọi năm → có survivorship bias, ghi vào phần hạn chế.
"""
import pandas as pd
from common import CFG, P
V = CFG["vn"]


def main():
    out = P(V["tickers_file"])
    if out.exists():
        df = pd.read_csv(out)
        print(f"Đã có {out.name}: {len(df)} mã"); return df
    try:
        from vnstock import Listing
        lst = Listing()
        vn30 = set(map(str, lst.symbols_by_group("VN30")))
        vn100 = set(map(str, lst.symbols_by_group("VN100")))
    except Exception as e:
        raise SystemExit(f"Không lấy được rổ chỉ số qua vnstock ({e}).\n"
                         f"→ Tự tạo {out} với 2 cột: ticker,group (group = VN30 hoặc VN100).")
    df = pd.DataFrame({"ticker": sorted(vn30 | vn100)})
    df["group"] = df.ticker.map(lambda t: "VN30" if t in vn30 else "VN100")
    df.to_csv(out, index=False)
    print(f"Lưu {len(df)} mã ({(df.group=='VN30').sum()} VN30) → {out}")
    return df


if __name__ == "__main__":
    main()
