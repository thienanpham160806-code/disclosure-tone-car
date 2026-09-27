"""US-1. Danh mục 10-K (submissions API) + tải file HTML chính + XBRL companyfacts.

Điểm cải tiến so với repo tham khảo:
  • lm2011-replication dựng manifest từ master index theo quý (cần tải cả chục GB). Ta dùng
    submissions API theo CIK → chỉ tải đúng 10-K của mẫu, có sẵn acceptanceDateTime để xác định T=0.
  • Nhớ đọc cả các trang lịch sử filings.files[] – với ngân hàng lớn (JPM, GS) phần "recent"
    chỉ phủ vài tháng do nộp rất nhiều hồ sơ 424B2.
  • companyfacts (XBRL) thay cho CRSP/Compustat: số cổ phiếu lưu hành (dei:EntityCommonStockSharesOutstanding,
    ghi trên trang bìa 10-K) và vốn chủ sở hữu (us-gaap:StockholdersEquity) → vốn hóa, B/M miễn phí.
Cache: file đã có sẽ không tải lại.
"""
import json
import pandas as pd
from tqdm import tqdm
from common import CFG, D
from us.edgar_client import get

C = CFG["us"]


def cik_map():
    f = D("us", "raw", "company_tickers.json")
    if not f.exists():
        f.write_text(get("https://www.sec.gov/files/company_tickers.json").text)
    js = json.loads(f.read_text())
    return {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in js.values()}


def submissions(cik):
    f = D("us", "raw", "submissions", f"{cik}.json")
    if f.exists():
        return json.loads(f.read_text())
    js = get(f"https://data.sec.gov/submissions/CIK{cik}.json").json()
    pages = [js["filings"]["recent"]]
    for extra in js["filings"].get("files", []):
        pages.append(get(f"https://data.sec.gov/submissions/{extra['name']}").json())
    keys = ["accessionNumber", "form", "filingDate", "acceptanceDateTime", "primaryDocument", "reportDate"]
    merged = {k: sum((p.get(k, []) for p in pages), []) for k in keys}
    out = {"cik": cik, "sic": js.get("sic"), "sicDescription": js.get("sicDescription"),
           "exchanges": js.get("exchanges"), "filings": merged}
    f.write_text(json.dumps(out))
    return out


def companyfacts(cik):
    f = D("us", "raw", "companyfacts", f"{cik}.json")
    if not f.exists():
        try:
            f.write_text(get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json").text)
        except Exception as e:
            print(f"  ! companyfacts {cik}: {e}"); return
    return f


def main():
    cm = cik_map(); y0, y1 = C["filing_years"]; rows = []
    for tk in tqdm(C["tickers"], desc="Submissions"):
        cik = cm.get(tk.upper().replace(".", "-"))
        if not cik:
            print(f"  ! không tìm thấy CIK cho {tk}"); continue
        s = submissions(cik); fl = s["filings"]
        for acc, form, fd, acpt, doc, rd in zip(*[fl[k] for k in ["accessionNumber", "form", "filingDate",
                                                                    "acceptanceDateTime", "primaryDocument", "reportDate"]]):
            if form in C["forms"] and y0 <= int(fd[:4]) <= y1 and doc:
                a = acc.replace("-", "")
                rows.append(dict(ticker=tk, cik=cik, sic=s["sic"], accession=acc, form=form, filing_date=fd,
                                 acceptance=acpt, period=rd, file=f"{tk}_{a}.htm",
                                 url=f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{a}/{doc}"))
        companyfacts(cik)
    man = pd.DataFrame(rows).drop_duplicates("accession")
    raw = D("us", "raw", "10k", "x").parent
    ok = []
    for r in tqdm(man.itertuples(), total=len(man), desc="Tải 10-K"):
        f = raw / r.file
        if not f.exists():
            try:
                f.write_bytes(get(r.url).content)
            except Exception as e:
                print(f"  ! {r.file}: {e}"); ok.append(False); continue
        ok.append(True)
    man["downloaded"] = ok
    man.to_csv(D("us", "processed", "manifest.csv"), index=False)
    print(f"{man.downloaded.sum()} / {len(man)} 10-K đã tải; {man.ticker.nunique()} công ty")


if __name__ == "__main__":
    main()
