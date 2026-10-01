"""A10 (VN). Phân tích bổ sung ĐÃ ĐĂNG KÝ TRƯỚC (CHANGELOG_RUN #66) – thiết kế cố định trước khi chạy, báo cáo nguyên vẹn.

  S1  T=0 = ngày CafeF đăng tin công bố thông tin BCTN (thay ngày ModDate của PDF); kèm M2 trên CÙNG tập con với T=0 cũ
  S2  biến tone = thay đổi so với năm trước của chính công ty: Δfin_neg (phụ: Δfin_net); T=0 cũ
  S3  bỏ sự kiện có tin CafeF gắn nhãn KQKD hoặc ĐHĐCĐ (không gắn nhãn BCTN) trong phiên [0,3]; độ nhạy: bỏ thêm sự kiện
      có cửa sổ [−10,+10] chạm tháng kho tin CafeF hổng
  S4  kết hợp S1 + S2 + S3
Biến phụ thuộc chính CAR[0,3]; phụ CAR[0,5] (chỉ mô tả). Kiểm soát, FE năm, winsorize, SE cluster theo mã như M2 (a03).
Kiểm định nhiều lần: 4 kiểm định chính → Bonferroni α = 0,05/4 = 0,0125.

Đầu ra: outputs/vn/extra_results.csv (mọi mô hình), outputs/vn/extra_summary.csv (mẫu, độ khớp ngày),
        outputs/vn/extra_dates.csv (ngày T=0 cũ và ngày CafeF của từng sự kiện)
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import glob, json, re
import numpy as np, pandas as pd
from common import CFG, D, O, K, winsor
from analysis.a02_event import event_row
from analysis.a03_regress import fit
from vn.v05_news import TOPICS, tidy, coverage

E = CFG["event"]
ALPHA = 0.05 / 4
BCTN = re.compile(r"báo cáo thường niên|bctn", re.IGNORECASE)
BAD = re.compile(r"đính chính|tạm hoãn|gia hạn|hoãn", re.IGNORECASE)
YEAR = re.compile(r"(20\d{2})")


def load_news():
    news = pd.concat([tidy(json.load(open(f, encoding="utf-8"))) for f in glob.glob(str(D("vn", "raw", "cafef_news", "*.json")))],
                     ignore_index=True).drop_duplicates(["ticker", "url"])
    news["ts"] = pd.to_datetime(news.published_at)
    news["date"] = news.ts.dt.normalize()
    low = news.title.str.lower()
    for k, pat in TOPICS.items():
        news[k] = low.str.contains(pat, regex=True)
    return news


def session_index(cal, ts):
    """Chỉ số phiên của một thời điểm: sau 15:00 hoặc ngày không giao dịch → phiên kế tiếp (cùng quy tắc với v05/a02)."""
    d = ts.normalize()
    i = cal.searchsorted(d)
    if i < len(cal) and cal[i] == d and ts.hour >= 15:
        i += 1
    return i


def cafef_dates(news, docs):
    """Tin CBTT BCTN sớm nhất có đúng năm tài chính trong tiêu đề, bỏ đính chính / tạm hoãn / gia hạn."""
    b = news[(news.kind == "cbtt") & news.title.str.contains(BCTN) & ~news.title.str.contains(BAD)].copy()
    b["fy"] = b.title.map(lambda t: int(YEAR.findall(t)[-1]) if YEAR.findall(t) else None)
    b = b.dropna(subset=["fy"]).sort_values("ts")
    first = b.groupby(["ticker", "fy"]).first().reset_index()
    first["fy"] = first.fy.astype(int)
    return docs.merge(first[["ticker", "fy", "ts", "title", "url"]], left_on=["ticker", "year"], right_on=["ticker", "fy"], how="left")


def car_table(events, close, ret, rm, vol):
    """CAR + biến kiểm soát cho các sự kiện (doc_id, ticker, i0) – đúng các bước của a02."""
    rows = []
    for e in events.itertuples():
        if e.ticker not in ret or pd.isna(e.i0) or e.i0 >= len(close):
            continue
        i0 = int(e.i0)
        res = event_row(ret[e.ticker], rm, i0)
        if res is None:
            continue
        res.pop("_path", None)
        pc, pv = close[e.ticker].iloc[max(0, i0 - 60):i0], vol[e.ticker].iloc[max(0, i0 - 60):i0]
        tv = (pc * pv).mean()
        res.update(doc_id=e.doc_id, i0=i0, log_tradeval=np.log(tv) if tv > 0 else np.nan)
        rows.append(res)
    return pd.DataFrame(rows)


def contaminated(news, cal, ev, lo=0, hi=3):
    """Sự kiện có tin KQKD/ĐHĐCĐ (không phải tin BCTN) trong các phiên [lo, hi] quanh i0."""
    n = news[(news.kqkd | news.dhdcd) & ~news.bctn]
    sess = {t: g.ts.map(lambda x: session_index(cal, x)).to_numpy() for t, g in n.groupby("ticker")}
    return ev.apply(lambda e: bool(((sess.get(e.ticker, np.array([])) - e.i0 >= lo) & (sess.get(e.ticker, np.array([])) - e.i0 <= hi)).any()), axis=1)


def touches_gap(cal, ev, gap_months, win=10):
    return ev.i0.map(lambda i: bool(set(cal[max(int(i) - win, 0):int(i) + win + 1].to_period("M").astype(str)) & gap_months))


def regress(df, x, y, label, sample):
    d = df.copy()
    for c in [c for c in d if c.startswith(("car_", "carma_", "bhar_"))] + ["pre_ret"]:
        d[c] = winsor(d[c])
    d["log_len"] = np.log(d.n_words.clip(lower=1))
    d["vn30"] = (d.group == "VN30").astype(int)
    d = d.dropna(subset=[x, y])
    d[x + "_z"] = (d[x] - d[x].mean()) / d[x].std()
    ctrl = " + ".join([c for c in ["log_tradeval", "pre_ret", "log_len", "vn30", "beta"] if d[c].notna().mean() > .5] + ["C(year)"])
    m = fit(d, f"{y} ~ {x}_z + {ctrl}")
    b, se, p = m.params[x + "_z"], m.bse[x + "_z"], m.pvalues[x + "_z"]
    return dict(mo_hinh=label, mau=sample, bien=x, bien_phu_thuoc=y, N=int(m.nobs), he_so=round(b, 4), se=round(se, 4),
                p=round(p, 4), diem_pct_khi_tang_1SD=round(100 * b, 2),
                vuot_bonferroni=bool(p < ALPHA) if y == K("car", *E["main_window"]) else None)


def main():
    lo, hi = E["main_window"]
    Y, Y5 = K("car", lo, hi), K("car", 0, 5)
    px = pd.read_csv(D("vn", "processed", "prices.csv.gz"), parse_dates=["date"])
    close = px.pivot_table(index="date", columns="ticker", values="close").sort_index()
    vol = px.pivot_table(index="date", columns="ticker", values="volume").reindex(close.index)
    ret = close.pct_change(fill_method=None); rm = ret[CFG["vn"]["market_symbol"]]
    cal = close.index
    docs = pd.read_csv(D("vn", "processed", "docs.csv"), parse_dates=["event_date"])
    docs = docs[docs.flag.eq("ok")]
    tone = pd.read_csv(D("vn", "processed", "tone_panel.csv"))
    news = load_news()
    cov, _ = coverage(news[["ticker", "date", "crawled_at"]].assign(date=news.date))
    gap = set(cov.loc[cov.hong, "thang"])

    # ---- T=0 cũ (ModDate) và T=0 CafeF
    old = docs.dropna(subset=["event_date"]).copy()
    old["i0"] = [cal.searchsorted(d) + int(bool(a)) for d, a in zip(old.event_date, old.after_close)]
    cf = cafef_dates(news, docs).dropna(subset=["ts"]).copy()
    cf["i0"] = cf.ts.map(lambda t: session_index(cal, t))
    base_old = car_table(old, close, ret, rm, vol).merge(tone, on="doc_id")
    base_cf = car_table(cf, close, ret, rm, vol).merge(tone, on="doc_id")

    dates = old[["doc_id", "ticker", "year", "i0"]].merge(cf[["doc_id", "i0", "ts", "title", "url"]], on="doc_id", how="outer",
                                                          suffixes=("_moddate", "_cafef"))
    dates["lech_phien_cafef_tru_moddate"] = dates.i0_cafef - dates.i0_moddate
    dates["ngay_moddate"] = dates.i0_moddate.map(lambda i: cal[int(i)].date() if pd.notna(i) and i < len(cal) else None)
    dates["ngay_cafef"] = dates.i0_cafef.map(lambda i: cal[int(i)].date() if pd.notna(i) and i < len(cal) else None)
    dates.drop(columns=["i0_moddate", "i0_cafef"]).to_csv(O("vn", "extra_dates.csv"), index=False, encoding="utf-8-sig")

    # ---- Δtone (năm t − năm t−1, cùng mã)
    t = tone.sort_values(["ticker", "year"]).copy()
    prev = t[["ticker", "year", "fin_neg", "fin_net"]].assign(year=lambda x: x.year + 1)
    t = t.merge(prev, on=["ticker", "year"], how="left", suffixes=("", "_prev"))
    t["d_fin_neg"] = t.fin_neg - t.fin_neg_prev
    t["d_fin_net"] = t.fin_net - t.fin_net_prev
    dcols = ["doc_id", "d_fin_neg", "d_fin_net"]

    rows = []
    # Mô hình gốc trên toàn mẫu (đối chiếu, cùng hàm)
    rows.append(regress(base_old, "fin_neg", Y, "Đối chiếu: M2, T=0 ModDate", "toàn mẫu"))
    # S1
    sub = base_old[base_old.doc_id.isin(base_cf.doc_id)]
    rows.append(regress(sub, "fin_neg", Y, "S1 đối chiếu: M2, T=0 ModDate", "chỉ sự kiện có ngày CafeF"))
    rows.append(regress(base_cf, "fin_neg", Y, "S1: M2, T=0 CafeF", "chỉ sự kiện có ngày CafeF"))
    rows.append(regress(base_cf, "fin_neg", Y5, "S1: M2, T=0 CafeF", "chỉ sự kiện có ngày CafeF"))
    # S2
    s2 = base_old.merge(t[dcols], on="doc_id")
    rows.append(regress(s2, "d_fin_neg", Y, "S2: Δfin_neg, T=0 ModDate", "có thư năm trước"))
    rows.append(regress(s2, "d_fin_neg", Y5, "S2: Δfin_neg, T=0 ModDate", "có thư năm trước"))
    rows.append(regress(s2, "d_fin_net", Y, "S2 phụ: Δfin_net, T=0 ModDate", "có thư năm trước"))
    # S3
    ev_old = base_old.merge(docs[["doc_id"]], on="doc_id")
    ev_old["contam"] = contaminated(news, cal, ev_old)
    ev_old["gap"] = touches_gap(cal, ev_old, gap)
    s3 = ev_old[~ev_old.contam]
    rows.append(regress(s3, "fin_neg", Y, "S3: M2, bỏ sự kiện trùng tin KQKD/ĐHĐCĐ", "không trùng tin trong [0,3]"))
    rows.append(regress(s3, "fin_neg", Y5, "S3: M2, bỏ sự kiện trùng tin KQKD/ĐHĐCĐ", "không trùng tin trong [0,3]"))
    rows.append(regress(s3[~s3.gap], "fin_neg", Y, "S3 độ nhạy: bỏ thêm sự kiện chạm tháng hổng", "không trùng tin, không chạm tháng hổng"))
    # S4
    ev_cf = base_cf.copy()
    ev_cf["contam"] = contaminated(news, cal, ev_cf)
    s4 = ev_cf[~ev_cf.contam].merge(t[dcols], on="doc_id")
    rows.append(regress(s4, "d_fin_neg", Y, "S4: Δfin_neg, T=0 CafeF, bỏ trùng tin", "S1 ∩ S2 ∩ S3"))
    rows.append(regress(s4, "d_fin_neg", Y5, "S4: Δfin_neg, T=0 CafeF, bỏ trùng tin", "S1 ∩ S2 ∩ S3"))

    res = pd.DataFrame(rows)
    res.to_csv(O("vn", "extra_results.csv"), index=False, encoding="utf-8-sig")
    lag = dates.lech_phien_cafef_tru_moddate.dropna()
    summ = [("Sự kiện có T=0 ModDate và CAR", len(base_old)), ("Sự kiện có ngày CafeF và CAR", len(base_cf)),
            ("Ngày CafeF − ngày ModDate (phiên): trung vị", lag.median()), ("  p10", lag.quantile(.1)), ("  p90", lag.quantile(.9)),
            ("  trùng phiên (lệch 0)", int((lag == 0).sum())), ("  CafeF muộn hơn", int((lag > 0).sum())),
            ("  CafeF sớm hơn", int((lag < 0).sum())), ("Sự kiện có thư năm trước (Δtone)", int(s2.d_fin_neg.notna().sum())),
            ("Sự kiện trùng tin KQKD/ĐHĐCĐ trong [0,3] (T=0 ModDate)", int(ev_old.contam.sum())),
            ("Sự kiện còn lại sau S3", len(s3)), ("Mẫu S4", int(s4.d_fin_neg.notna().sum())), ("Ngưỡng Bonferroni (4 kiểm định chính)", ALPHA)]
    pd.DataFrame(summ, columns=["chi_so", "gia_tri"]).to_csv(O("vn", "extra_summary.csv"), index=False, encoding="utf-8-sig")
    print(pd.DataFrame(summ, columns=["chi_so", "gia_tri"]).to_string(index=False))
    print(res.to_string(index=False))


if __name__ == "__main__":
    main()
