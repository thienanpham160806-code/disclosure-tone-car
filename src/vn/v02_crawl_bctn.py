"""B2. Crawl toàn bộ Báo cáo thường niên (BCTN) của VN30 + VN100 từ CafeF + ứng viên ngày công bố.

Endpoint CafeF (đã kiểm tra 27/09/2026):
  https://cafef.vn/du-lieu/Ajax/PageNew/FileBCTC.ashx?Symbol=VNM&Type=3&Year=0
    → Type=3: tài liệu doanh nghiệp (BCTN, điều lệ), trường Time dạng "CN/2024" (KHÔNG có ngày)
  ...&Type=4 → công bố thông tin có ngày (Time = dd-mm-yyyy): nghị quyết, tài liệu ĐHĐCĐ...
JSON: {"Data":[{id,Type,Quarter,Year,Time,Name,IconFile,Link}], "Success":..., "Message":...}

Ngày sự kiện (T=0) – thứ tự ưu tiên, lưu hết để kiểm tra tay:
  d_cbtt   : ngày tin CBTT có chữ "báo cáo thường niên" trên CafeF Type=4 (năm Y+1)
  d_lastmod: header Last-Modified của file PDF BCTN (ngày upload lên CDN) nếu rơi vào 01/01–31/07 năm Y+1
  d_agm_doc: ngày sớm nhất của tài liệu/thông báo họp ĐHĐCĐ thường niên năm Y+1 (BCTN thường nằm trong bộ tài liệu này)
Chạy lại an toàn: file đã tải sẽ bỏ qua (cache).
"""
import re, json, argparse
import pandas as pd
from tqdm import tqdm
from email.utils import parsedate_to_datetime
from common import CFG, P, D, norm_vi as norm
from vn.http import session, polite_get
V = CFG["vn"]

API = "https://cafef.vn/du-lieu/Ajax/PageNew/FileBCTC.ashx"
RAW = D("vn", "raw", "bctn", "x").parent
CACHE = D("vn", "raw", "cafef_json", "x").parent


def list_docs(s, tk, typ):
    f = CACHE / f"{tk}_t{typ}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    r = polite_get(s, API, params={"Symbol": tk, "Type": typ, "Year": 0})
    data = (r.json().get("Data") if r is not None else None) or []
    f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def lang_of(name):
    n = norm(name)
    return "en" if re.search(r"tiếng anh|english|\(en\)|\ben\b", n) else "vi"


def pick_dates(t4, year):
    """Các ứng viên ngày công bố BCTN năm `year` từ danh sách CBTT (Type=4)."""
    rows = []
    for d in t4:
        try:
            dt = pd.to_datetime(d.get("Time"), format="%d-%m-%Y")
        except Exception:
            continue
        if dt.year != year + 1:
            continue
        rows.append((dt, norm(d.get("Name", ""))))
    cbtt = [dt for dt, n in rows if "thường niên" in n and "báo cáo" in n]
    agm = [dt for dt, n in rows if re.search(r"(đại hội|đhđcđ|đhcđ).*thường niên|thường niên.*(đại hội|đhđcđ|đhcđ)", n)
           and re.search(r"tài liệu|mời họp|thông báo|chương trình", n)]
    return (min(cbtt) if cbtt else pd.NaT), (min(agm) if agm else pd.NaT)


def main(limit=None):
    s = session()
    tickers = pd.read_csv(P(V["tickers_file"]))
    if limit: tickers = tickers.head(limit)
    y0, y1 = V["years"]
    rows = []
    for tk, grp in tqdm(tickers[["ticker", "group"]].itertuples(index=False), total=len(tickers), desc="Mã"):
        t3, t4 = list_docs(s, tk, 3), list_docs(s, tk, 4)
        for d in t3:
            name, link = d.get("Name", ""), d.get("Link", "")
            if "thường niên" not in norm(name) or not link.lower().endswith(".pdf"):
                continue
            yr = int(d.get("Year") or 0)
            if not (y0 <= yr <= y1):
                continue
            lg = lang_of(name)
            f = RAW / f"{tk}_{yr}_{lg}.pdf"
            lastmod = pd.NaT
            if not f.exists():
                r = polite_get(s, link)
                if r is None or not r.content.startswith(b"%PDF"):
                    rows.append(dict(ticker=tk, group=grp, year=yr, lang=lg, url=link, file=None, status="download_fail")); continue
                f.write_bytes(r.content)
                lm = r.headers.get("Last-Modified")
                if lm: lastmod = pd.Timestamp(parsedate_to_datetime(lm)).tz_localize(None).normalize()
            d_cbtt, d_agm = pick_dates(t4, yr)
            rows.append(dict(ticker=tk, group=grp, year=yr, lang=lg, name=name, url=link, file=f.name,
                             size_mb=round(f.stat().st_size / 1e6, 2), d_cbtt=d_cbtt, d_lastmod=lastmod,
                             d_agm_doc=d_agm, status="ok"))
    meta = pd.DataFrame(rows)
    old = D("vn", "processed", "bctn_meta.csv")
    if old.exists():  # giữ Last-Modified đã ghi ở lần chạy trước
        prev = pd.read_csv(old, parse_dates=["d_lastmod"])[["file", "d_lastmod"]].dropna()
        meta = meta.merge(prev, on="file", how="left", suffixes=("", "_old"))
        meta["d_lastmod"] = meta["d_lastmod"].fillna(meta.pop("d_lastmod_old"))
    # chọn ngày sự kiện theo thứ tự ưu tiên
    ok_lm = meta.d_lastmod.where((meta.d_lastmod.dt.year == meta.year + 1) & (meta.d_lastmod.dt.month <= 7))
    meta["event_date"] = meta.d_cbtt.fillna(ok_lm).fillna(meta.d_agm_doc)
    meta["event_src"] = (meta.d_cbtt.notna().map({True: "cbtt"}).fillna(ok_lm.notna().map({True: "lastmod"}))
                         .fillna(meta.d_agm_doc.notna().map({True: "agm_doc", False: "missing"})))
    meta.to_csv(old, index=False)
    print(meta.groupby(["status", "lang"]).size().to_string())
    print("Nguồn ngày sự kiện:\n", meta.event_src.value_counts().to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--limit", type=int, help="chạy thử N mã đầu")
    main(ap.parse_args().limit)
