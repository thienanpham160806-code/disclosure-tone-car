"""A6. Bảng tổng hợp cho RESULTS.md – chỉ đọc lại dữ liệu đã xử lý, không ước lượng gì mới. Dùng chung US/VN.
  sample_funnel.csv     : số văn bản qua từng bước lọc (phễu mẫu)
  coverage_by_year.csv  : độ phủ theo năm (văn bản có tone / có CAR / vào hồi quy)
  tone_descriptive.csv  : thống kê mô tả các biến tone (%)
  tone_by_year.csv      : trung bình tone theo năm (%)
  economic_magnitude.csv: hệ số *_z của các mô hình và độ lớn kinh tế (điểm % CAR khi tone tăng 1 độ lệch chuẩn)
"""
import argparse, re
import pandas as pd
from common import CFG, D, O, K

lo, hi = CFG["event"]["main_window"]
Y = K("car", lo, hi)


def coef(cell):
    """'-0.0017** (0.0019)' → (hệ số, sai số chuẩn, sao)."""
    m = re.match(r"\s*(-?[\d.]+)(\**)\s*\((-?[\d.]+)\)", str(cell))
    return (float(m.group(1)), float(m.group(3)), m.group(2)) if m else (None, None, None)


def main(mkt):
    docs = pd.read_csv(D(mkt, "processed", "docs.csv"))
    tone = pd.read_csv(D(mkt, "processed", "tone_panel.csv"))
    car = pd.read_csv(D(mkt, "processed", "car.csv"))
    ap = pd.read_csv(D(mkt, "processed", "analysis_panel.csv"))
    reg = pd.read_csv(O(mkt, "regression_main.csv"), index_col=0)
    n_reg = int(float(reg.loc["N", "M2 fin_neg"]))

    if mkt == "us":
        man = pd.read_csv(D(mkt, "processed", "manifest.csv"))
        steps = [("Công ty trong mẫu", man.ticker.nunique()), ("Hồ sơ 10-K nộp 2015–2024 (submissions API)", len(man)),
                 ("Tải được file HTML chính", int(man.downloaded.sum())), ("Toàn văn ≥ 2.000 từ (flag = ok)", int(docs.flag.eq("ok").sum())),
                 ("  trong đó cắt được MD&A", int(docs.text_alt.notna().sum())), ("Có CAR[0,3] (đủ dữ liệu giá)", int(car[Y].notna().sum())),
                 ("Vào hồi quy M2 (đủ biến kiểm soát)", n_reg)]
    else:
        meta = pd.read_csv(D(mkt, "processed", "bctn_meta.csv"))
        lm = pd.read_csv(D(mkt, "processed", "letters_meta.csv"))
        ok = docs[docs.flag.eq("ok")]
        steps = [("Mã VN30 + VN100", pd.read_csv(CFG["vn"]["tickers_file"]).ticker.nunique()),
                 ("Mã–năm có BCTN PDF trên CafeF (2016–2025)", meta.drop_duplicates(["ticker", "year"]).shape[0]),
                 ("Tìm được Thông điệp HĐQT (ok + too_long)", int(lm.flag.isin(["ok", "too_long"]).sum())),
                 ("  không tìm thấy thư (not_found)", int(lm.flag.eq("not_found").sum())),
                 ("  thư quá ngắn < 250 âm tiết (too_short)", int(lm.flag.eq("too_short").sum())),
                 ("Có ngày sự kiện T=0 (PDF ModDate hợp lệ)", int(ok.event_date.notna().sum())),
                 ("Có CAR (đủ dữ liệu giá, ≥ 80 phiên ước lượng)", len(car)), ("Có CAR[0,3]", int(car[Y].notna().sum())),
                 ("Vào hồi quy M2 (đủ biến kiểm soát)", n_reg)]
    pd.DataFrame(steps, columns=["buoc", "so_van_ban"]).to_csv(O(mkt, "sample_funnel.csv"), index=False, encoding="utf-8-sig")
    if mkt == "vn":   # kiểm tra ngày sự kiện T=0 (PDF ModDate) so với ngày Nghị quyết ĐHĐCĐ thường niên
        m = meta.drop_duplicates(["ticker", "year"]).merge(ok[["ticker", "year"]], on=["ticker", "year"])
        ev, agm = pd.to_datetime(m.event_date), pd.to_datetime(m.d_agm_res)
        lag = (agm - ev).dt.days.dropna()
        chk = {"so_van_ban_ok": len(m), "co_T0": int(ev.notna().sum()),
               **{f"nguon_{k}": int(v) for k, v in m.event_src.value_counts().items()},
               **{f"T0_thang_{int(k)}": int(v) for k, v in ev.dt.month.value_counts().sort_index().items()},
               "T0_thang_3_den_5_pct": round(100 * ev.dt.month.between(3, 5).sum() / ev.notna().sum(), 1),
               "co_ngay_DHDCD": len(lag), "ngay_T0_den_DHDCD_p10": lag.quantile(.1),
               "ngay_T0_den_DHDCD_trung_vi": lag.median(), "ngay_T0_den_DHDCD_p90": lag.quantile(.9)}
        pd.Series(chk).to_csv(O(mkt, "event_date_check.csv"), header=["gia_tri"], encoding="utf-8-sig")

    diag = {"so_su_kien": len(car), "beta_trung_vi": car.beta.median(), "beta_p5": car.beta.quantile(.05),
            "beta_p95": car.beta.quantile(.95), "zero_ret_share_trung_vi": car.zero_ret_share.median(),
            "zero_ret_share_trung_binh": car.zero_ret_share.mean(), "zero_ret_share_p90": car.zero_ret_share.quantile(.9),
            "CAR_0_3_do_lech_chuan_pct": 100 * car[Y].std(), "max_abs_CAR_0_3_pct": 100 * car[Y].abs().max()}
    fb = D(mkt, "processed", "finbert.csv")
    if fb.exists():
        diag["corr_finbert_net_fin_net"] = tone.merge(pd.read_csv(fb), on="doc_id")[["finbert_net", "fin_net"]].corr().iloc[0, 1]
    pd.Series(diag).round(4).to_csv(O(mkt, "event_study_diag.csv"), header=["gia_tri"], encoding="utf-8-sig")

    cov = pd.DataFrame({"co_tone": tone.groupby("year").size(), "co_car_0_3": ap.dropna(subset=[Y]).groupby("year").size()})
    cov.fillna(0).astype(int).to_csv(O(mkt, "coverage_by_year.csv"), encoding="utf-8-sig")

    cols = [c for c in ["fin_neg", "fin_pos", "fin_unc", "fin_lit", "gen_neg", "gen_pos", "finA_neg"] if c in tone]
    desc = (tone[cols] * 100).describe().T[["count", "mean", "std", "min", "25%", "50%", "75%", "max"]]
    desc.loc["fin_net"] = tone.fin_net.describe()[desc.columns]
    desc.round(4).to_csv(O(mkt, "tone_descriptive.csv"), encoding="utf-8-sig")
    by = tone.groupby("year")[cols + ["fin_net"]].mean()
    by[cols] *= 100
    by.assign(N=tone.groupby("year").size()).round(4).to_csv(O(mkt, "tone_by_year.csv"), encoding="utf-8-sig")

    rows = []
    for sheet in ["regression_main.csv", "regression_robustness.csv"]:
        t = pd.read_csv(O(mkt, sheet), index_col=0)
        for model in t.columns:
            for var in [i for i in t.index if str(i).endswith("_z")]:
                b, se, st = coef(t.at[var, model])
                if b is not None:
                    rows.append(dict(bang=sheet, mo_hinh=model, bien=var, he_so=b, se=se, sao=st,
                                     thay_doi_CAR_diem_pct_khi_tang_1SD=round(100 * b, 3)))
    pd.DataFrame(rows).to_csv(O(mkt, "economic_magnitude.csv"), index=False, encoding="utf-8-sig")
    print(pd.DataFrame(steps, columns=["buoc", "so_van_ban"]).to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--market", choices=["us", "vn"], required=True)
    main(ap.parse_args().market)
