"""A3. Giọng điệu có mang thông tin cho thị trường không? – dùng chung US/VN.

(a) CAR[0,3] theo tam phân vị tone (fin_net): Tiêu cực / Trung tính / Tích cực; kiểm định T3 − T1 (Welch).
(b) OLS gộp, sai số chuẩn cluster theo mã, FE năm (+ FE ngành 2 chữ số SIC cho Mỹ):
      M1 chỉ kiểm soát | M2 +fin_neg | M3 +gen_neg | M4 đối đầu fin vs gen (Mục tiêu 2)
      M5 +fin_net +fin_unc | M6 +fin_neg_tfidf (LM eq.1) | M7 +finA_neg (MD&A – chỉ Mỹ)
    Biến tone chuẩn hóa z → hệ số = thay đổi CAR khi tone tăng 1 độ lệch chuẩn.
(c) Fama–MacBeth (như bảng IV của LM 2011, theo cách làm của lm2011-replication): hồi quy cắt ngang từng
    quý (Mỹ) / từng năm (VN), trung bình hệ số, t-stat Newey–West 1 trễ.
(d) Kiểm định giả định (Breusch–Pagan, Jarque–Bera, VIF) và độ vững (market-adjusted, BHAR, placebo,
    các cửa sổ khác, chỉ bản tiếng Việt).
"""
import argparse
import numpy as np, pandas as pd, statsmodels.api as sm, statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import jarque_bera
from common import CFG, D, O, K, winsor

lo, hi = CFG["event"]["main_window"]
Y = K("car", lo, hi)


def stars(p):
    return "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""


def fit(df, f):
    cols = [c for c in df.columns if c in f.replace("~", " ").replace("+", " ").split()]
    d = df.dropna(subset=cols)
    return smf.ols(f, d).fit(cov_type="cluster", cov_kwds={"groups": d["ticker"].astype("category").cat.codes})


def table(models, names):
    out = {}
    for nm, m in zip(names, models):
        col = {k: f"{m.params[k]:.4f}{stars(m.pvalues[k])} ({m.bse[k]:.4f})" for k in m.params.index if not k.startswith("C(")}
        col.update(N=int(m.nobs), **{"Adj. R2": f"{m.rsquared_adj:.4f}"})
        out[nm] = col
    return pd.DataFrame(out)


def fama_macbeth(df, y, xs, period):
    coefs = []
    for _, g in df.dropna(subset=[y] + xs).groupby(period):
        if len(g) < len(xs) + 5:
            continue
        coefs.append(sm.OLS(g[y], sm.add_constant(g[xs])).fit().params)
    B = pd.DataFrame(coefs)
    res = {}
    for c in B:
        nw = sm.OLS(B[c], np.ones(len(B))).fit(cov_type="HAC", cov_kwds={"maxlags": 1})
        res[c] = f"{B[c].mean():.4f}{stars(nw.pvalues.iloc[0])} (t={nw.tvalues.iloc[0]:.2f})"
    res["Số kỳ cắt ngang"] = len(B)
    return pd.Series(res)


def main(mkt):
    car = pd.read_csv(D(mkt, "processed", "car.csv"), parse_dates=["day0"])
    tone = pd.read_csv(D(mkt, "processed", "tone_panel.csv"), dtype={"industry": str})
    df = car.merge(tone, on="doc_id")
    fb = D(mkt, "processed", "finbert.csv")          # tùy chọn: chạy a05_finbert.py trước
    if fb.exists():
        df = df.merge(pd.read_csv(fb), on="doc_id", how="left")
    lt = D(mkt, "processed", "llm_tone.csv")         # tùy chọn: chạy a07_llm_tone.py trước (biến đối chứng, M9)
    if lt.exists():
        df = df.merge(pd.read_csv(lt)[["doc_id", "llm_tone", "llm_uncertainty"]], on="doc_id", how="left")
    for c in [c for c in df if c.startswith(("car_", "carma_", "bhar_", "placebo_"))] + ["pre_ret", "pre_alpha"]:
        df[c] = winsor(df[c])
    df["log_len"] = np.log(df.n_words.clip(lower=1))
    df["vn30"] = (df.group == "VN30").astype(int)
    if "bm" in df: df["log_bm"] = np.log(df.bm)
    if "turnover" in df: df["log_turn"] = np.log(df.turnover.where(df.turnover > 0))
    df["period"] = df.day0.dt.to_period("Q" if mkt == "us" else "Y").astype(str)
    for c in ["fin_neg", "gen_neg", "fin_net", "fin_unc", "fin_neg_tfidf", "finA_neg", "finbert_net", "llm_tone", "llm_uncertainty"]:
        if c in df and df[c].std() > 0: df[c + "_z"] = (df[c] - df[c].mean()) / df[c].std()

    cand = (["log_mcap", "log_bm", "log_turn", "pre_alpha", "log_len"] if mkt == "us"
            else ["log_tradeval", "pre_ret", "log_len", "vn30", "beta"])
    ctrl_vars = [c for c in cand if c in df and df[c].notna().mean() > .5]
    fe = "C(year)" + (" + C(industry)" if mkt == "us" and df.industry.nunique() > 1 else "")
    ctrl = " + ".join(ctrl_vars + [fe])

    # (a) nhóm tone
    df["tone_grp"] = pd.qcut(df.fin_net.rank(method="first"), 3, labels=["T1 Tiêu cực", "T2 Trung tính", "T3 Tích cực"])
    g = df.groupby("tone_grp", observed=True)[Y].agg(N="count", mean_pct=lambda x: 100 * x.mean(),
                                                     p_t=lambda x: stats.ttest_1samp(x.dropna(), 0).pvalue)
    t3, t1 = df.loc[df.tone_grp == "T3 Tích cực", Y].dropna(), df.loc[df.tone_grp == "T1 Tiêu cực", Y].dropna()
    g.loc["T3 − T1"] = [len(t3) + len(t1), 100 * (t3.mean() - t1.mean()), stats.ttest_ind(t3, t1, equal_var=False).pvalue]
    g.round(4).to_csv(O(mkt, "car_by_tone.csv")); print(g.round(4).to_string())
    df.to_csv(D(mkt, "processed", "analysis_panel.csv"), index=False)

    # (b) OLS gộp
    specs = {"M1 nền": f"{Y} ~ {ctrl}", "M2 fin_neg": f"{Y} ~ fin_neg_z + {ctrl}",
             "M3 gen_neg": f"{Y} ~ gen_neg_z + {ctrl}", "M4 đối đầu": f"{Y} ~ fin_neg_z + gen_neg_z + {ctrl}",
             "M5 net+unc": f"{Y} ~ fin_net_z + fin_unc_z + {ctrl}", "M6 tf-idf": f"{Y} ~ fin_neg_tfidf_z + {ctrl}"}
    if "finA_neg_z" in df and df.finA_neg_z.notna().sum() > 30:
        specs["M7 MD&A"] = f"{Y} ~ finA_neg_z + {ctrl}"
    if "finbert_net_z" in df and df.finbert_net_z.notna().sum() > 30:
        specs["M8 FinBERT"] = f"{Y} ~ finbert_net_z + {ctrl}"
    if "llm_tone_z" in df and df.llm_tone_z.notna().sum() > 30:
        specs["M9 LLM tone"] = f"{Y} ~ llm_tone_z + llm_uncertainty_z + {ctrl}"
    ok = lambda f: all(v in df for v in f.split("~")[1].replace(" ", "").split("+") if not v.startswith("C("))
    specs = {k: f for k, f in specs.items() if ok(f)}      # bỏ mô hình thiếu biến (vd tf-idf không biến thiên)
    ms = [fit(df, f) for f in specs.values()]
    main_tab = table(ms, list(specs)); main_tab.to_csv(O(mkt, "regression_main.csv"), encoding="utf-8-sig")
    print(main_tab.to_string())

    # (c) Fama–MacBeth
    fm = pd.DataFrame({x: fama_macbeth(df, Y, [x] + ctrl_vars, "period")
                       for x in ["fin_neg_z", "gen_neg_z", "fin_neg_tfidf_z"] if x in df})
    fm.to_csv(O(mkt, "regression_fama_macbeth.csv"), encoding="utf-8-sig")

    # (d) giả định trên M2
    d2 = df.dropna(subset=["fin_neg_z"] + ctrl_vars + [Y])
    m2 = smf.ols(specs["M2 fin_neg"], d2).fit(); X = m2.model.exog; nm = m2.model.exog_names
    diag = {"Breusch-Pagan p": het_breuschpagan(m2.resid, X)[1], "Jarque-Bera p": jarque_bera(m2.resid)[1],
            "corr(fin_neg, gen_neg)": df[["fin_neg", "gen_neg"]].corr().iloc[0, 1]}
    diag.update({f"VIF {n}": variance_inflation_factor(X, i) for i, n in enumerate(nm) if not n.startswith(("C(", "Intercept"))})
    pd.Series(diag).round(4).to_csv(O(mkt, "assumption_tests.csv"))

    rob = {"Market-adjusted": K("carma", lo, hi), "BHAR (LM 2011)": K("bhar", lo, hi),
           "Placebo −60 phiên": K("placebo_car", lo, hi)}
    for a, b in CFG["event"]["windows"]:
        if [a, b] != [lo, hi]: rob[f"CAR[{a},{b}]"] = K("car", a, b)
    rms, rn = [], []
    for name, y in rob.items():
        if y in df and df[y].notna().sum() > 30:
            rms.append(fit(df, f"{y} ~ fin_neg_z + {ctrl}")); rn.append(name)
    if mkt == "vn" and (df.lang == "en").any() and (df.lang == "vi").sum() > 30:
        rms.append(fit(df[df.lang == "vi"], specs["M2 fin_neg"])); rn.append("Chỉ bản tiếng Việt")
    table(rms, rn).to_csv(O(mkt, "regression_robustness.csv"), encoding="utf-8-sig")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--market", choices=["us", "vn"], required=True)
    main(ap.parse_args().market)
