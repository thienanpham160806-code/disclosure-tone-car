"""A11 (Mỹ). Kiểm tra bổ sung: 10-K nộp trùng thời điểm công bố KQKD (CHANGELOG_RUN #24, viết lại thành script ở #64).

Cờ trùng thời điểm lấy từ outputs/us/earnings_overlap.csv (10-K nộp trong ±3 ngày lịch quanh 8-K mục 2.02, không phụ
thuộc văn bản). Ước lượng lại M2 (fin_neg_z) và M3 (gen_neg_z) – cùng biến kiểm soát, FE năm + ngành, SE cluster theo mã
như a03 – trên toàn mẫu, mẫu bỏ hồ sơ trùng và mẫu chỉ hồ sơ trùng, từ panel hiện tại (data/us/processed/analysis_panel.csv).
Đầu ra: outputs/us/regression_excl_earnings.csv
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pandas as pd
from common import CFG, D, O, K
from analysis.a03_regress import fit, table


def main():
    lo, hi = CFG["event"]["main_window"]
    y = K("car", lo, hi)
    df = pd.read_csv(D("us", "processed", "analysis_panel.csv"), dtype={"industry": str})
    ov = pd.read_csv(O("us", "earnings_overlap.csv"))[["doc_id", "overlap"]]
    df = df.merge(ov, on="doc_id", how="left")
    ctrl = " + ".join([c for c in ["log_mcap", "log_bm", "log_turn", "pre_alpha", "log_len"] if c in df and df[c].notna().mean() > .5]
                      + ["C(year)"] + (["C(industry)"] if df.industry.nunique() > 1 else []))
    models, names = [], []
    for name, d in [("Toàn mẫu", df), ("Bỏ 10-K trùng KQKD (±3 ngày)", df[df.overlap.eq(False)]), ("Chỉ 10-K trùng KQKD", df[df.overlap.eq(True)])]:
        for x in ["fin_neg_z", "gen_neg_z"]:
            models.append(fit(d, f"{y} ~ {x} + {ctrl}")); names.append(f"{name} | {x}")
    tab = table(models, names)
    tab.to_csv(O("us", "regression_excl_earnings.csv"), encoding="utf-8-sig")
    print(tab.to_string())


if __name__ == "__main__":
    main()
