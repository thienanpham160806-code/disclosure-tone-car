"""A2. Nghiên cứu sự kiện quanh ngày công bố – dùng chung US/VN.

T=0: phiên đầu tiên ≥ ngày công bố; nếu công bố sau 16:00 (10-K có acceptanceDateTime) → phiên kế tiếp.
Hai thước đo lợi suất bất thường (kết quả chính + đối chứng):
  • CAR theo market model  – ước lượng [-150,-11], ≥80 phiên có giao dịch (MacKinlay 1997)
  • BHAR[0,3] = Π(1+R_i) − Π(1+R_m) – đúng định nghĩa "excess return" của LM (2011), theo lm2011-replication
Placebo: dời T=0 về −60 phiên. Đường CAAR [-10,+10] lưu để vẽ hình theo nhóm tone.
Biến kiểm soát từ giá: beta, pre_alpha (hệ số chặn [-252,-6], thay FF-alpha của LM), pre_ret CAR[-30,-2],
  log_tradeval (GTGD bình quân 60 phiên), turnover (Mỹ: KL/số CP lưu hành), log_mcap, bm (Mỹ, từ XBRL).
Kiểm định CAR ≠ 0: t, BMP (Boehmer–Musumeci–Poulsen 1991), Wilcoxon, sign test.
"""
import argparse
import numpy as np, pandas as pd, statsmodels.api as sm
from scipy import stats
from common import CFG, D, O, K

E = CFG["event"]


def mm_fit(y, x):
    ok = y.notna() & x.notna() & (y != 0)
    if ok.sum() < E["min_est_obs"]:
        return None
    m = sm.OLS(y[ok], sm.add_constant(x[ok])).fit()
    return m.params.iloc[0], m.params.iloc[1], np.sqrt(m.scale)


def event_row(r, rm, i0):
    a, b = E["est_window"]
    if i0 + a < 0 or i0 + max(w[1] for w in E["windows"]) >= len(r):
        return None
    fit = mm_fit(r.iloc[i0 + a:i0 + b + 1], rm.iloc[i0 + a:i0 + b + 1])
    if fit is None:
        return None
    al, be, sig = fit
    out = dict(alpha=al, beta=be, sigma=sig, zero_ret_share=float((r.iloc[i0 + a:i0 + b + 1] == 0).mean()))
    for lo, hi in E["windows"]:
        w = slice(i0 + lo, i0 + hi + 1)
        ar = r.iloc[w] - (al + be * rm.iloc[w])
        if ar.isna().any():
            continue
        out[K("car", lo, hi)] = ar.sum()
        out[K("scar", lo, hi)] = ar.sum() / (sig * np.sqrt(hi - lo + 1))
        out[K("carma", lo, hi)] = (r.iloc[w] - rm.iloc[w]).sum()
    lo, hi = E["main_window"]; w = slice(i0 + lo, i0 + hi + 1)
    out[K("bhar", lo, hi)] = np.prod(1 + r.iloc[w]) - np.prod(1 + rm.iloc[w])
    pre = slice(max(0, i0 - 30), i0 - 1)
    out["pre_ret"] = (r.iloc[pre] - rm.iloc[pre]).sum()
    pf = mm_fit(r.iloc[max(0, i0 - 252):i0 - 5], rm.iloc[max(0, i0 - 252):i0 - 5])
    out["pre_alpha"] = pf[0] if pf else np.nan
    p0, p1 = E["caar_path"]
    if i0 + p0 >= 0 and i0 + p1 < len(r):
        wp = slice(i0 + p0, i0 + p1 + 1)
        out["_path"] = (r.iloc[wp] - (al + be * rm.iloc[wp])).to_numpy()
    return out


def tests(x, label):
    x = pd.Series(x).dropna()
    if len(x) < 5:
        return None
    return dict(window=label, N=len(x), mean_pct=100 * x.mean(), median_pct=100 * x.median(),
                t=stats.ttest_1samp(x, 0).statistic, p_t=stats.ttest_1samp(x, 0).pvalue,
                p_wilcoxon=stats.wilcoxon(x).pvalue, pct_positive=100 * (x > 0).mean(),
                p_sign=stats.binomtest(int((x > 0).sum()), len(x)).pvalue)


def main(mkt):
    C = CFG[mkt]
    px = pd.read_csv(D(mkt, "processed", "prices.csv.gz"), parse_dates=["date"])
    close = px.pivot_table(index="date", columns="ticker", values="close").sort_index()
    vol = px.pivot_table(index="date", columns="ticker", values="volume").reindex(close.index)
    # vốn hóa = giá CHỈ điều chỉnh chia tách × số CP quy về cùng gốc chia tách (Mỹ; CHANGELOG_RUN #8)
    pxm = (px.pivot_table(index="date", columns="ticker", values="close_split").reindex(close.index)
           if "close_split" in px else close)
    ret = close.pct_change(fill_method=None); rm = ret[C["market_symbol"]]
    docs = pd.read_csv(D(mkt, "processed", "docs.csv"), parse_dates=["event_date"])
    docs = docs[docs.flag.eq("ok") & docs.event_date.notna()]
    fund = D(mkt, "processed", "fundamentals.csv")
    fund = pd.read_csv(fund).set_index("doc_id") if fund.exists() else None
    rows, paths = [], []
    lo, hi = E["main_window"]
    for d in docs.itertuples():
        if d.ticker not in ret:
            continue
        i0 = close.index.searchsorted(d.event_date) + int(bool(d.after_close))
        if i0 >= len(close):
            continue
        res = event_row(ret[d.ticker], rm, i0)
        if res is None:
            continue
        p = res.pop("_path", None)
        if p is not None:
            paths.append(pd.Series(p, name=d.doc_id))
        plc = event_row(ret[d.ticker], rm, i0 + E["placebo_shift"])
        res[K("placebo_car", lo, hi)] = plc.get(K("car", lo, hi)) if plc else np.nan
        pc, pv = close[d.ticker].iloc[max(0, i0 - 60):i0], vol[d.ticker].iloc[max(0, i0 - 60):i0]
        tv = (pc * pv).mean()
        res.update(doc_id=d.doc_id, day0=close.index[i0], log_tradeval=np.log(tv) if tv > 0 else np.nan)
        if fund is not None and d.doc_id in fund.index:
            sh, be = fund.loc[d.doc_id, ["shares_adj" if "shares_adj" in fund else "shares_out", "book_equity"]]
            mcap = pxm[d.ticker].iloc[i0 - 1] * sh if pd.notna(sh) else np.nan
            res["log_mcap"] = np.log(mcap) if mcap and mcap > 0 else np.nan
            res["bm"] = be / mcap if pd.notna(be) and mcap and mcap > 0 and be > 0 else np.nan
            v252 = vol[d.ticker].iloc[max(0, i0 - 252):i0 - 5]
            res["turnover"] = v252.sum() / sh if pd.notna(sh) and sh > 0 else np.nan
        rows.append(res)
    car = pd.DataFrame(rows)
    car.to_csv(D(mkt, "processed", "car.csv"), index=False)
    if paths:
        pd.DataFrame(paths).to_csv(D(mkt, "processed", "ar_path.csv.gz"))

    out = []
    for a, b in E["windows"]:
        t = tests(car.get(K("car", a, b)), f"CAR[{a},{b}]")
        if t:
            sc = car[K("scar", a, b)].dropna(); t["t_BMP"] = sc.mean() / (sc.std(ddof=1) / np.sqrt(len(sc)))
            out.append(t)
        out.append(tests(car.get(K("carma", a, b)), f"CAR market-adjusted[{a},{b}]"))
    out += [tests(car[K("bhar", lo, hi)], f"BHAR[{lo},{hi}] (LM 2011)"),
            tests(car[K("placebo_car", lo, hi)], f"PLACEBO CAR[{lo},{hi}]")]
    tab = pd.DataFrame([x for x in out if x]).round(4)
    tab.to_csv(O(mkt, "car_tests.csv"), index=False)
    print(f"{len(car)} sự kiện\n", tab.to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--market", choices=["us", "vn"], required=True)
    main(ap.parse_args().market)
