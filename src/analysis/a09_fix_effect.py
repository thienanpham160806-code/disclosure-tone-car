"""A9. Tác động của một lần sửa dữ liệu văn bản lên kết quả: chạy lại ĐÚNG các mô hình của a03 (cùng biến kiểm soát, FE,
sai số chuẩn cluster theo mã) trên panel TRƯỚC (bản sao lưu) và panel hiện tại; kèm mức thay đổi của chính các biến tone.

  python src/analysis/a09_fix_effect.py --market us --before data/us/interim/snap/analysis_panel_truoc_64.csv --out xbrl_fix
Đầu ra (outputs/<mkt>/):
  <out>_effect.csv : mô hình, biến phụ thuộc, biến tone, hệ số / SE / p trước và sau, N
  <out>_tone.csv   : với từng biến tone – tương quan trước/sau theo văn bản, chênh lệch trung bình và lớn nhất (điểm %)
Không ước lượng gì mới ngoài các mô hình đã có.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import argparse
import pandas as pd
from common import CFG, D, O, K
from analysis.a03_regress import fit

TONE = ["fin_neg", "fin_pos", "fin_unc", "fin_lit", "fin_net", "gen_neg", "finA_neg"]


def specs(mkt, df):
    lo, hi = CFG["event"]["main_window"]
    y = K("car", lo, hi)
    out = [("M2 fin_neg", y, ["fin_neg_z"]), ("M3 gen_neg", y, ["gen_neg_z"]), ("M4 đối đầu", y, ["fin_neg_z", "gen_neg_z"]),
           ("M5 net+unc", y, ["fin_net_z", "fin_unc_z"]), ("M6 tf-idf", y, ["fin_neg_tfidf_z"]),
           ("M7 MD&A", y, ["finA_neg_z"]), ("M8 FinBERT", y, ["finbert_net_z"])]
    out += [("Market-adjusted", K("carma", lo, hi), ["fin_neg_z"]), ("BHAR (LM 2011)", K("bhar", lo, hi), ["fin_neg_z"]),
            ("Placebo −60 phiên", K("placebo_car", lo, hi), ["fin_neg_z"])]
    out += [(f"CAR[{a},{b}]", K("car", a, b), ["fin_neg_z"]) for a, b in CFG["event"]["windows"] if [a, b] != [lo, hi]]
    return [s for s in out if s[1] in df and all(x in df and df[x].notna().sum() > 30 for x in s[2])]


def estimate(mkt, df):
    cand = (["log_mcap", "log_bm", "log_turn", "pre_alpha", "log_len"] if mkt == "us"
            else ["log_tradeval", "pre_ret", "log_len", "vn30", "beta"])
    fe = "C(year)" + (" + C(industry)" if mkt == "us" and df.industry.nunique() > 1 else "")
    ctrl = " + ".join([c for c in cand if c in df and df[c].notna().mean() > .5] + [fe])
    res = {}
    for name, y, xs in specs(mkt, df):
        m = fit(df, f"{y} ~ {' + '.join(xs)} + {ctrl}")
        for x in xs:
            res[(name, y, x)] = (m.params[x], m.bse[x], m.pvalues[x], int(m.nobs))
    return res


def main(mkt, before, out):
    old = pd.read_csv(before, dtype={"industry": str})
    new = pd.read_csv(D(mkt, "processed", "analysis_panel.csv"), dtype={"industry": str})
    b, a = estimate(mkt, old), estimate(mkt, new)
    rows = [dict(mo_hinh=k[0], bien_phu_thuoc=k[1], bien=k[2], he_so_truoc=round(b[k][0], 4), se_truoc=round(b[k][1], 4),
                 p_truoc=round(b[k][2], 4), he_so_sau=round(a[k][0], 4), se_sau=round(a[k][1], 4), p_sau=round(a[k][2], 4),
                 N_truoc=b[k][3], N_sau=a[k][3]) for k in a if k in b]
    eff = pd.DataFrame(rows)
    eff.to_csv(O(mkt, f"{out}_effect.csv"), index=False, encoding="utf-8-sig")
    print(eff.to_string(index=False))
    m = old[["doc_id"] + [c for c in TONE if c in old]].merge(new[["doc_id"] + [c for c in TONE if c in new]],
                                                              on="doc_id", suffixes=("_truoc", "_sau"))
    tone = []
    for c in TONE:
        if f"{c}_truoc" in m and f"{c}_sau" in m:
            d = m[f"{c}_sau"] - m[f"{c}_truoc"]
            tone.append(dict(bien=c, n_van_ban=int(d.notna().sum()), tuong_quan=round(m[f"{c}_truoc"].corr(m[f"{c}_sau"]), 5),
                             chenh_tb=round(d.mean(), 5), chenh_tuyet_doi_lon_nhat=round(d.abs().max(), 5),
                             so_van_ban_doi=int((d.abs() > 1e-9).sum()), do_lech_chuan_truoc=round(m[f"{c}_truoc"].std(), 5)))
    tone = pd.DataFrame(tone)
    tone.to_csv(O(mkt, f"{out}_tone.csv"), index=False, encoding="utf-8-sig")
    print(tone.to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", choices=["us", "vn"], required=True)
    ap.add_argument("--before", required=True, help="analysis_panel.csv sao lưu trước lần sửa")
    ap.add_argument("--out", required=True, help="tiền tố tên file trong outputs/<mkt>/")
    a = ap.parse_args()
    main(a.market, a.before, a.out)
