"""A8 (VN, sau khi chạy tầng AI `v03 --llm`). Báo cáo tầng AI và tác động của nó lên kết quả – không ước lượng gì mới
ngoài việc chạy lại đúng các mô hình của a03 trên hai panel.

  llm_ocr_summary.csv : số trang gửi AI / nhận / loại (theo lý do), chất lượng trước–sau, token và chi phí ước tính
                        (token cộng từ cache data/vn/interim/llm_cache/, gồm cả các lượt chạy thử)
  llm_ocr_effect.csv  : hệ số, sai số chuẩn, p-value của các biến tone TRƯỚC (panel không có tầng AI) và SAU (panel hiện tại),
                        cùng công thức, biến kiểm soát, FE và sai số chuẩn cluster như a03.

Panel TRƯỚC mặc định lấy từ git: `git show results:data/vn/processed/analysis_panel.csv` (lần chạy trước tầng AI);
có thể chỉ file khác bằng --before (và --out để ghi ra file khác, vd so sánh trước/sau sửa trang thư).
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import argparse, glob, io, json, subprocess
import pandas as pd
from common import CFG, D, O, ROOT
from analysis.a03_regress import fit

THR = CFG["vn"]["extract"]["llm"].get("quality_threshold", 0.85)
SPECS = [  # (tên, biến phụ thuộc, biến tone)
    ("M2 fin_neg", "car_0_3", "fin_neg_z"), ("M3 gen_neg", "car_0_3", "gen_neg_z"),
    ("M5 net+unc", "car_0_3", "fin_net_z"), ("M5 net+unc", "car_0_3", "fin_unc_z"),
    ("M6 tf-idf", "car_0_3", "fin_neg_tfidf_z"),
    ("Market-adjusted", "carma_0_3", "fin_neg_z"), ("BHAR (LM 2011)", "bhar_0_3", "fin_neg_z"),
    ("Placebo −60 phiên", "placebo_car_0_3", "fin_neg_z"), ("CAR[0,1]", "car_0_1", "fin_neg_z"),
    ("CAR[-1,1]", "car_m1_1", "fin_neg_z"), ("CAR[0,5]", "car_0_5", "fin_neg_z"), ("CAR[0,10]", "car_0_10", "fin_neg_z"),
]


def summary():
    p = pd.read_csv(D("vn", "processed", "llm_pages.csv"))
    lm = pd.read_csv(D("vn", "processed", "letters_meta.csv"))
    lm = lm[lm.flag.isin(["ok", "too_long", "too_short"])]          # chỉ các thư đang dùng (bỏ not_found / excluded_manual)
    s = p[p.decision.notna()]
    a = s[s.decision == "accepted"]
    used = lm[lm.llm_pages_used.fillna(0) > 0]
    rows = [(f"Trang thuộc thư ({len(lm)} văn bản)", len(p)), (f"Trang có quality_score < {THR}", int((p.q_before < THR).sum())),
            ("Trang gửi AI", len(s))]
    rows += [(f"  chế độ {k}", v) for k, v in s["mode"].value_counts().items()]
    rows += [("Trang nhận bản AI", len(a)),
             ("  trong đó điểm chất lượng tăng", int((a.q_after > a.q_before).sum())),
             ("  trong đó trang gần như trống (< 20 token cả trước và sau)", int(((a.q_before == 0) & (a.q_after == 0)).sum())),
             ("Trang loại bản AI", int((s.decision != "accepted").sum()))]
    rows += [(f"  lý do: {k}", v) for k, v in s.reason[s.decision != "accepted"].str.split("(").str[0].value_counts().items()]
    rows += [("Điểm chất lượng TB các trang nhận bản AI – trước", round(a.q_before.mean(), 3)),
             ("Điểm chất lượng TB các trang nhận bản AI – sau", round(a.q_after.mean(), 3)),
             ("Văn bản có ≥ 1 trang dùng bản AI", len(used)),
             ("Điểm chất lượng TB (theo token) các văn bản đó – trước", round(used.ocr_quality_before.mean(), 3)),
             ("Điểm chất lượng TB (theo token) các văn bản đó – sau", round(used.ocr_quality_after.mean(), 3))]
    rows += [(f"Văn bản theo method: {k}", v) for k, v in lm["method"].value_counts().items()]
    price = CFG["vn"]["extract"]["llm"].get("price_usd_per_1m", {})
    tok, cost = {}, 0.0
    for f in glob.glob(str(D("vn", "interim", "llm_cache", "*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        m, u = d.get("model"), d.get("usage") or {}
        t = tok.setdefault(m, [0, 0, 0]); t[0] += 1; t[1] += u.get("input_tokens") or 0; t[2] += u.get("output_tokens") or 0
    for m, (n, ti, to) in sorted(tok.items()):
        pi, po = price.get(m, [None, None])
        c = (ti * pi + to * po) / 1e6 if pi is not None else None
        cost += c or 0
        rows += [(f"{m}: số phản hồi trong cache", n), (f"{m}: token đầu vào", ti), (f"{m}: token đầu ra", to),
                 (f"{m}: chi phí ước tính nếu trả phí (USD)", round(c, 4) if c is not None else "")]
    rows.append(("Tổng chi phí ước tính nếu trả phí (USD)", round(cost, 4)))
    out = pd.DataFrame(rows, columns=["chi_so", "gia_tri"], dtype=object)
    out.to_csv(O("vn", "llm_ocr_summary.csv"), index=False, encoding="utf-8-sig")
    print(out.to_string(index=False))


def estimate(df):
    cand = ["log_tradeval", "pre_ret", "log_len", "vn30", "beta"]
    ctrl = " + ".join([c for c in cand if c in df and df[c].notna().mean() > .5] + ["C(year)"])
    res = {}
    for name, y, x in SPECS:
        xs = [x] if name != "M5 net+unc" else ["fin_net_z", "fin_unc_z"]
        if y not in df or any(v not in df for v in xs):
            continue
        m = fit(df, f"{y} ~ {' + '.join(xs)} + {ctrl}")
        res[(name, y, x)] = (m.params[x], m.bse[x], m.pvalues[x], int(m.nobs))
    return res


def effect(before, out_name="llm_ocr_effect.csv"):
    if before:
        old = pd.read_csv(before)
    else:
        raw = subprocess.run(["git", "show", "results:data/vn/processed/analysis_panel.csv"], cwd=ROOT,
                             capture_output=True, check=True).stdout
        old = pd.read_csv(io.BytesIO(raw))
    new = pd.read_csv(D("vn", "processed", "analysis_panel.csv"))
    b, a = estimate(old), estimate(new)
    rows = [dict(mo_hinh=k[0], bien_phu_thuoc=k[1], bien=k[2], he_so_truoc=round(b[k][0], 4), se_truoc=round(b[k][1], 4),
                 p_truoc=round(b[k][2], 4), he_so_sau=round(a[k][0], 4), se_sau=round(a[k][1], 4), p_sau=round(a[k][2], 4),
                 N_truoc=b[k][3], N_sau=a[k][3]) for k in a if k in b]
    out = pd.DataFrame(rows)
    out.to_csv(O("vn", out_name), index=False, encoding="utf-8-sig")
    print(out.to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--before", help="analysis_panel.csv của lần chạy không có tầng AI")
    ap.add_argument("--out", default="llm_ocr_effect.csv", help="tên file kết quả trong outputs/vn/ (vd page_fix_effect.csv)")
    ap.add_argument("--no-effect", action="store_true", help="chỉ cập nhật llm_ocr_summary.csv")
    a = ap.parse_args()
    summary()
    if not a.no_effect:
        effect(a.before, a.out)
