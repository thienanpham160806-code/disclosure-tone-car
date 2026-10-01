"""V5 (bổ sung). Tin tức CafeF quanh ngày công bố BCTN của từng mã – để mô tả bối cảnh thông tin của mỗi sự kiện.

Nguồn: CafeF (cafef.vn), mục “Tin tức” trên trang dữ liệu doanh nghiệp, API công khai mà chính trang web gọi:
    https://cafef.vn/du-lieu/Ajax/PageNew/News.ashx?Symbol=<MÃ>&NewsType=0&PageIndex=<n>&PageSize=30
    (NewsType 0 = Tất cả; mỗi trang 30 tin, mới nhất trước; robots.txt của cafef.vn: Allow /).
Chỉ lưu TIÊU ĐỀ, THỜI ĐIỂM ĐĂNG và ĐƯỜNG DẪN tới bài gốc trên CafeF (không lưu nội dung bài) + thời điểm thu thập.
Loại tin: đường dẫn “/du-lieu/…” = tin công bố thông tin (CBTT) của doanh nghiệp; còn lại = bài báo của CafeF.

Lịch sự: một tiến trình, nghỉ `vn.sleep` giây giữa các request (vn/http.py), dừng khi đã lùi quá ngày sự kiện sớm nhất
của mã 60 ngày. Phản hồi thô cache ở data/vn/raw/cafef_news/<MÃ>.json (không đưa lên git); chạy lại dùng cache
(--refresh để tải lại).

Đầu ra
  data/vn/processed/news_cafef_events.csv : mỗi tin trong cửa sổ [T−10, T+10] phiên của từng sự kiện (doc_id, offset phiên,
                                           thời điểm đăng, loại, tiêu đề, link CafeF, nhãn chủ đề theo từ khóa)
  outputs/vn/news_event_counts.csv        : số tin theo cửa sổ cho từng sự kiện
  outputs/vn/news_summary.csv             : tổng hợp toàn mẫu
Tin đăng sau 15:00 (giờ Việt Nam) hoặc ngày không giao dịch được tính vào phiên kế tiếp (giống quy tắc T = 0).
Đây là dữ liệu MÔ TẢ – không thay đổi mô hình hồi quy chính.
"""
import sys, pathlib
_SRC = pathlib.Path(__file__).resolve().parents[1]      # bỏ src/vn khỏi sys.path: src/vn/http.py che mất thư viện http chuẩn
sys.path[:] = [str(_SRC)] + [p for p in sys.path if pathlib.Path(p or ".").resolve() != _SRC / "vn"]
import argparse, datetime as dt, json, re
import numpy as np, pandas as pd
from tqdm import tqdm
from common import CFG, D, O
from vn.http import polite_get, session

API = "https://cafef.vn/du-lieu/Ajax/PageNew/News.ashx"
CACHE = D("vn", "raw", "cafef_news", "x").parent
WIN = 10                                    # cửa sổ [−10, +10] phiên
VN_TZ = dt.timezone(dt.timedelta(hours=7))
TOPICS = {                                  # nhãn chủ đề theo từ khóa trong tiêu đề (không phân biệt hoa thường)
    "kqkd": r"kết quả kinh doanh|kqkd|lợi nhuận|doanh thu|báo cáo tài chính|bctc|lãi ròng|lỗ ",
    "dhdcd": r"đại hội|đhđcđ|đhcđ|tài liệu họp|biên bản họp",
    "co_tuc": r"cổ tức|chốt quyền|ngày đăng ký cuối cùng",
    "bctn": r"báo cáo thường niên|bctn",
    "nhan_su": r"bổ nhiệm|miễn nhiệm|từ nhiệm|nhân sự",
    "chung_quyen": r"chứng quyền|^c[a-z]{3}\d{4}",   # tin chứng quyền có bảo đảm trên cổ phiếu (CafeF gộp vào tin của mã)
    "gd_noi_bo": r"đăng ký (?:mua|bán)|giao dịch (?:cổ phiếu|của)|cổ đông lớn|người nội bộ|bán ra|mua vào",
}


def crawl(s, tk, stop_before, refresh=False):
    f = CACHE / f"{tk}.json"
    if f.exists() and not refresh:
        return json.loads(f.read_text(encoding="utf-8"))
    items, seen = [], set()
    for page in range(1, 400):
        r = polite_get(s, API, params=dict(Symbol=tk, NewsType=0, PageIndex=page, PageSize=30))
        data = (r.json().get("Data") or []) if r is not None else []
        new = [x for x in data if x.get("LinkDetail") not in seen]
        if not new:
            break
        for x in new:
            seen.add(x.get("LinkDetail"))
        items += new
        oldest = min(int(re.search(r"\d+", x["DeployDate"]).group()) for x in new) / 1000
        if dt.datetime.fromtimestamp(oldest, VN_TZ).date() < stop_before:
            break
    out = {"ticker": tk, "source": API, "crawled_at": dt.datetime.now(VN_TZ).isoformat(timespec="seconds"),
           "pages": page, "items": items}
    f.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


def tidy(raw):
    rows = []
    for x in raw["items"]:
        ts = dt.datetime.fromtimestamp(int(re.search(r"\d+", x["DeployDate"]).group()) / 1000, VN_TZ)
        link = re.sub(r"\?utm_[^#]*$", "", x.get("LinkDetail") or "")
        rows.append(dict(ticker=raw["ticker"], published_at=ts.strftime("%Y-%m-%d %H:%M"), date=ts.date(),
                         after_close=ts.hour >= 15, kind="cbtt" if link.startswith("/du-lieu/") else "bai_bao",
                         title=(x.get("Title") or "").strip(), url="https://cafef.vn" + link if link.startswith("/") else link,
                         source="CafeF", crawled_at=raw["crawled_at"]))
    return pd.DataFrame(rows)


def main(refresh=False, only=None):
    docs = pd.read_csv(D("vn", "processed", "docs.csv"))
    car = pd.read_csv(D("vn", "processed", "car.csv"), usecols=["doc_id", "day0"], parse_dates=["day0"])
    ev = docs[docs.flag.eq("ok")].merge(car, on="doc_id")
    if only:
        ev = ev[ev.ticker.isin(only)]
    px = pd.read_csv(D("vn", "processed", "prices.csv.gz"), usecols=["ticker", "date"], parse_dates=["date"])
    mk = CFG["vn"]["market_symbol"]
    cal = pd.DatetimeIndex(sorted(px.loc[px.ticker == mk, "date"].unique() if (px.ticker == mk).any() else px.date.unique()))

    s = session()
    frames = []
    for tk, g in tqdm(ev.groupby("ticker"), desc="Tin CafeF"):
        stop = (g.day0.min() - pd.Timedelta(days=60)).date()
        frames.append(tidy(crawl(s, tk, stop, refresh)))
    news = pd.concat(frames, ignore_index=True).drop_duplicates(["ticker", "url"])
    news["date"] = pd.to_datetime(news.date)
    # phiên giao dịch của tin: sau 15:00 hoặc ngày nghỉ → phiên kế tiếp
    news["session"] = cal[np.minimum(cal.searchsorted(news.date) + (news.after_close & news.date.isin(cal)).astype(int), len(cal) - 1)]
    pos = pd.Series(np.arange(len(cal)), index=cal)
    for k, pat in TOPICS.items():
        news[k] = news.title.str.lower().str.contains(pat, regex=True)

    rows = []
    for e in ev.itertuples():
        n = news[news.ticker == e.ticker]
        off = n.session.map(pos) - pos[e.day0]
        w = n.assign(offset=off)[(off >= -WIN) & (off <= WIN)]
        rows.append(w.assign(doc_id=e.doc_id, year=e.year, day0=e.day0.date()))
    win = pd.concat(rows, ignore_index=True)
    cols = ["doc_id", "ticker", "year", "day0", "offset", "published_at", "kind", "title", "url", "source", "crawled_at"] + list(TOPICS)
    win = win[cols].sort_values(["doc_id", "offset", "published_at"])
    win.to_csv(D("vn", "processed", "news_cafef_events.csv"), index=False, encoding="utf-8-sig")

    def cnt(df, lo, hi, extra=None):
        m = (df.offset >= lo) & (df.offset <= hi) & (True if extra is None else extra(df))
        return df[m].groupby("doc_id").size()
    base = ev[["doc_id", "ticker", "year"]].set_index("doc_id")
    for name, lo, hi in [("pre_m10_m1", -WIN, -1), ("w0_3", 0, 3), ("w0_5", 0, 5), ("w0_10", 0, WIN)]:
        base[f"n_{name}"] = cnt(win, lo, hi)
        base[f"n_cbtt_{name}"] = cnt(win, lo, hi, lambda d: d.kind == "cbtt")
    for k in TOPICS:
        base[f"{k}_w0_5"] = cnt(win, 0, 5, lambda d, k=k: d[k]) > 0
    base = base.fillna(0)
    for c in [c for c in base if c.startswith("n_")]:
        base[c] = base[c].astype(int)
    for k in TOPICS:
        base[f"{k}_w0_5"] = base[f"{k}_w0_5"].astype(bool)
    base.reset_index().to_csv(O("vn", "news_event_counts.csv"), index=False, encoding="utf-8-sig")

    summ = [("Sự kiện (BCTN có T = 0 và CAR)", len(base)), ("Mã có tin trên CafeF", int(news.ticker.nunique())),
            ("Tin thu thập (toàn bộ, đã bỏ trùng)", len(news)), ("Tin trong cửa sổ [−10, +10] phiên", len(win)),
            ("  trong đó tin công bố thông tin (CBTT)", int((win.kind == "cbtt").sum())),
            ("Sự kiện có ≥ 1 tin trong [0, 3]", int((base.n_w0_3 > 0).sum())),
            ("Số tin trung bình / sự kiện trong [0, 3]", round(base.n_w0_3.mean(), 2)),
            ("Số tin trung bình / sự kiện trong [−10, −1]", round(base.n_pre_m10_m1.mean(), 2))]
    summ += [(f"Sự kiện có tin '{k}' trong [0, 5]", int(base[f"{k}_w0_5"].sum())) for k in TOPICS]
    summ += [("Tin cũ nhất thu thập được", str(news.date.min().date())), ("Tin mới nhất", str(news.date.max().date())),
             ("Thời điểm thu thập", f"{news.crawled_at.min()} → {news.crawled_at.max()}"), ("Nguồn", f"CafeF – {API}")]
    pd.DataFrame(summ, columns=["chi_so", "gia_tri"]).to_csv(O("vn", "news_summary.csv"), index=False, encoding="utf-8-sig")
    print(pd.DataFrame(summ, columns=["chi_so", "gia_tri"]).to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="tải lại thay vì dùng cache data/vn/raw/cafef_news")
    ap.add_argument("--only", help="chỉ các mã này, vd MWG,FPT")
    a = ap.parse_args()
    main(a.refresh, a.only.split(",") if a.only else None)
