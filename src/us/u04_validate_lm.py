"""US-4 (TÙY CHỌN, khuyên làm). Đối chiếu số đếm của nhóm với số liệu công bố của SRAF (LM 10X Summaries).

Ý tưởng từ lm2011-replication (step4 cross_check_vs_lm): nếu N_Words / N_Negative của ta lệch ít so với
file chính thức của Loughran–McDonald thì pipeline làm sạch + tách từ được kiểm chứng độc lập → điểm "tái lập".
Tải file "Loughran-McDonald_10X_Summaries_*.csv" tại https://sraf.nd.edu/sec-edgar-data/lm_10x_summaries/
và đặt vào thư mục dict/. Khác biệt nhỏ là bình thường (ta dùng file HTML chính, LM dùng toàn bộ hồ sơ .txt).
"""
import glob
import pandas as pd
from common import P, D, O


def main():
    fs = glob.glob(str(P("dict", "Loughran-McDonald_10X_Summaries*.csv")))
    if not fs:
        print("Bỏ qua: chưa có file LM 10X Summaries trong dict/"); return
    lm = pd.read_csv(fs[-1], usecols=["ACC_NUM", "N_Words", "N_Negative", "N_Positive"], dtype={"ACC_NUM": str})
    lm["doc_id"] = lm.ACC_NUM.str.replace(r"^(\d{10})(\d{2})(\d{6})$", r"\1-\2-\3", regex=True)
    me = pd.read_csv(D("us", "processed", "tone_panel.csv"))[["doc_id", "n_words", "n_fin_neg", "n_fin_pos"]]
    j = me.merge(lm, on="doc_id")
    rows = []
    for a, b in [("n_words", "N_Words"), ("n_fin_neg", "N_Negative"), ("n_fin_pos", "N_Positive")]:
        rel = (j[a] - j[b]) / j[b].where(j[b] > 0)
        rows.append(dict(bien=b, N=rel.notna().sum(), lech_trung_vi_pct=100 * rel.median(),
                         trong_2pct=100 * (rel.abs() <= .02).mean(), trong_5pct=100 * (rel.abs() <= .05).mean(),
                         tuong_quan=j[a].corr(j[b])))
    t = pd.DataFrame(rows).round(3); t.to_csv(O("us", "validate_vs_lm.csv"), index=False); print(t.to_string(index=False))


if __name__ == "__main__":
    main()
