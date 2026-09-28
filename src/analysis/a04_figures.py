"""A4. Hình cho báo cáo/slide (PNG 200 dpi) – dùng chung US/VN.
  fig1_tone_by_year.png   : tone tiêu cực theo năm – từ điển tài chính vs tổng quát (Mục tiêu 1–2)
  fig2_misclassified.png  : 15 từ "tiêu cực" theo từ điển tổng quát hay gặp nhất, tô theo có/không trong từ điển tài chính
  fig3_caar_by_tone.png   : đường CAAR [-10,+10] theo tam phân vị tone (Mục tiêu 3) – ý tưởng CAAR path từ
                            Ernest717/covid-event-study-african-markets
Màu: nhóm tone là dữ liệu có thứ tự hai cực → bảng màu phân kỳ đỏ (tiêu cực) / xám (trung tính) / xanh (tích cực),
kèm nhãn trực tiếp và kiểu nét khác nhau để không phụ thuộc màu.
"""
import argparse
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from common import D, O

BLUE, ORANGE, RED, GRAY, INK, MUTED = "#2a78d6", "#eb6834", "#e34948", "#8a8984", "#1d1d1b", "#6b6a66"
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#bdbcb8",
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True,
                     "grid.color": "#e6e5e1", "grid.linewidth": .6, "font.size": 9, "lines.linewidth": 2})


def main(mkt):
    tone = pd.read_csv(D(mkt, "processed", "tone_panel.csv"))
    y = tone.groupby("year")[["fin_neg", "gen_neg"]].mean() * 100
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    for c, col, lab in [("fin_neg", BLUE, "Từ điển tài chính"), ("gen_neg", ORANGE, "Từ điển tổng quát")]:
        ax.plot(y.index, y[c], color=col, marker="o", ms=4, label=lab)
        ax.annotate(lab, (y.index[-1], y[c].iloc[-1]), xytext=(6, 0), textcoords="offset points", color=INK, va="center")
    ax.set_ylabel("Tỷ lệ từ tiêu cực (%)"); ax.set_title("Giọng điệu tiêu cực theo năm", loc="left", color=INK)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))   # nhãn trực tiếp ở cuối đường → bỏ chú thích (từng đè lên đường)
    fig.tight_layout(); fig.savefig(O(mkt, "fig1_tone_by_year.png"), dpi=200); plt.close(fig)

    mc = pd.read_csv(O(mkt, "misclassified_general_neg.csv")).head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.barh(mc.word, mc.share_pct, color=np.where(mc.in_fin_negative, BLUE, ORANGE), height=.7)
    ax.set_xlabel("% tần suất từ tiêu cực của từ điển tổng quát")
    ax.set_title("Cam = không tiêu cực trong tài chính · Xanh = tiêu cực thật", loc="left", color=INK, fontsize=9)
    ax.grid(axis="y", visible=False); fig.tight_layout(); fig.savefig(O(mkt, "fig2_misclassified.png"), dpi=200); plt.close(fig)

    f = D(mkt, "processed", "ar_path.csv.gz")
    if f.exists():
        ar = pd.read_csv(f, index_col=0)
        ap = pd.read_csv(D(mkt, "processed", "analysis_panel.csv"))[["doc_id", "tone_grp"]].set_index("doc_id")
        cum = ar.cumsum(axis=1) * 100
        p0 = -(ar.shape[1] // 2); days = np.arange(p0, p0 + ar.shape[1])
        fig, ax = plt.subplots(figsize=(6.4, 3.6))
        ends = []
        for grp, col, ls in [("T1 Tiêu cực", RED, "-"), ("T2 Trung tính", GRAY, "--"), ("T3 Tích cực", BLUE, "-")]:
            ids = ap.index[ap.tone_grp == grp].intersection(cum.index)
            if len(ids):
                m = cum.loc[ids].mean()
                ax.plot(days, m.values, color=col, ls=ls, label=f"{grp} (n={len(ids)})")
                ends.append([m.iloc[-1], grp.split(" ", 1)[1]])
        # nhãn trực tiếp ở cuối đường, giãn theo chiều dọc để không chồng nhau khi các đường kết thúc gần nhau
        lo_, hi_ = ax.get_ylim(); gap = .07 * (hi_ - lo_)
        ends.sort()
        for k in range(1, len(ends)):
            ends[k][0] = max(ends[k][0], ends[k - 1][0] + gap)
        for yv, lab in ends:
            ax.annotate(lab, (days[-1], yv), xytext=(6, 0), textcoords="offset points", color=INK, va="center")
        ax.axvline(0, color=MUTED, lw=1); ax.axvspan(0, 3, color="#f0efec", zorder=0)
        ax.set_xlabel("Phiên so với ngày công bố (T)"); ax.set_ylabel("CAAR (%)"); ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.set_title("Lợi suất bất thường tích lũy theo nhóm giọng điệu (vùng xám: T→T+3)", loc="left", color=INK)
        ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(.5, -.2), ncol=3)   # dưới trục: không đè lên đường
        fig.tight_layout(); fig.savefig(O(mkt, "fig3_caar_by_tone.png"), dpi=200); plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--market", choices=["us", "vn"], required=True)
    main(ap.parse_args().market)
