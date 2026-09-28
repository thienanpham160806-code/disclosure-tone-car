"""B3b. Đánh giá định lượng: Tesseract thuần vs OCR + LLM text_fix vs LLM vision, so với trang chuẩn gõ tay (gold).

Gold: data/vn/processed/gold/<TICKER>_<NĂM>_p<TRANG>.txt – chép tay NGUYÊN VĂN phần chữ của trang PDF, theo cùng quy ước
      với tầng AI: bỏ tiêu đề/chân trang lặp lại, số trang, chú thích ảnh, chữ trong biểu đồ/bảng số; giữ nguyên chính tả.
Chưa có gold → chọn 15 trang (seed 42; 10 trang dưới ngưỡng chất lượng + 5 trang còn lại, từ data/vn/processed/
      llm_pages_dry.csv hoặc llm_pages.csv), ghi danh sách vào gold/_chon_trang.csv, xuất ảnh trang ra
      data/vn/interim/gold_png/ để gõ tay, in hướng dẫn rồi dừng.
Có gold → với mỗi trang:
  CER = khoảng cách Levenshtein ký tự / số ký tự gold;  WER = Levenshtein trên chuỗi từ / số từ gold
  (sau chuẩn hóa NFC, chữ thường, gộp khoảng trắng) cho 3 phương án:
    tesseract : OCR Tesseract thuần (ép OCR, không dùng lớp chữ PDF)
    llm_fix   : Tesseract + LLM text_fix (chỉ sửa lỗi ký tự/dấu)
    llm_vision: LLM chép nguyên văn từ ảnh trang
  và giọng điệu (fin_neg, fin_pos, fin_net theo dict/fin_vn.csv) của từng phương án so với gold → bằng chứng AI có/không
  làm méo biến giọng điệu.
Đầu ra: outputs/vn/ocr_eval.csv, outputs/vn/ocr_eval_tone.csv, outputs/vn/fig_ocr_eval.png
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import re, unicodedata
import pandas as pd
from common import CFG, D, O

GOLD = D("vn", "processed", "gold", "x").parent
METHODS = ["tesseract", "llm_fix", "llm_vision"]
LABELS = {"tesseract": "Tesseract thuần", "llm_fix": "OCR + LLM sửa lỗi", "llm_vision": "LLM đọc ảnh"}
COLORS = {"tesseract": "#2a78d6", "llm_fix": "#eb6834", "llm_vision": "#1baf7a"}   # dataviz: slot 1–3, đã validate


def _norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s or "").lower()).strip()


def cer_wer(hyp, ref):
    from rapidfuzz.distance import Levenshtein
    h, r = _norm(hyp), _norm(ref)
    return Levenshtein.distance(h, r) / max(len(r), 1), Levenshtein.distance(h.split(), r.split()) / max(len(r.split()), 1)


def tone(text):
    from textkit.dictionaries import load_fin_vn
    from textkit.scoring import VietScorer, indices
    n, c, _ = VietScorer(load_fin_vn()).run(text)
    return {k: v for k, v in indices("fin", n, c).items() if k in ("fin_neg", "fin_pos", "fin_net")}


def choose_pages(n_low=10, n_other=5):
    dry, full = D("vn", "processed", "llm_pages_dry.csv"), D("vn", "processed", "llm_pages.csv")
    if not dry.exists() and not full.exists():
        raise SystemExit("Chưa có llm_pages_dry.csv – chạy trước: python src/vn/v03_extract_letter.py --llm-dry")
    p = pd.read_csv(dry) if dry.exists() else None
    if full.exists() and (p is None or len(pd.read_csv(full)) >= 0.9 * len(p)):
        p = pd.read_csv(full)                  # đã chạy --llm toàn bộ: có q_llm → bỏ trang trống (OCR & AI đều < 20 token)
        p = p[~((p.q_before == 0) & (p.get("q_llm", pd.Series(0, index=p.index)).fillna(0) == 0))]
    thr = CFG["vn"]["extract"]["llm"].get("quality_threshold", 0.85)
    low, other = p[p.q_before < thr], p[p.q_before >= thr]
    pick = pd.concat([low.sample(min(n_low, len(low)), random_state=CFG["seed"]),
                      other.sample(min(n_other, len(other)), random_state=CFG["seed"])])
    return pick[["ticker", "year", "page", "source", "q_before"]].reset_index(drop=True)


def export_instructions(pick):
    import fitz
    lm = pd.read_csv(D("vn", "processed", "letters_meta.csv")).set_index(["ticker", "year"])
    png_dir = D("vn", "interim", "gold_png", "x").parent
    for f in png_dir.glob("*.png"):            # ảnh của lần chọn trước
        f.unlink()
    for r in pick.itertuples():
        doc = fitz.open(D("vn", "raw", "bctn", lm.loc[(r.ticker, r.year), "file"]))
        doc[int(r.page) - 1].get_pixmap(dpi=150).save(str(png_dir / f"{r.ticker}_{r.year}_p{r.page}.png"))
    pick.assign(file_gold=[f"{r.ticker}_{r.year}_p{r.page}.txt" for r in pick.itertuples()]).to_csv(
        GOLD / "_chon_trang.csv", index=False, encoding="utf-8-sig")
    print(f"Chưa có trang chuẩn (gold). Đã chọn {len(pick)} trang (seed {CFG['seed']}, ưu tiên chất lượng thấp):")
    print(pick.to_string(index=False))
    print(f"\nHướng dẫn: mở ảnh trong {png_dir} (hoặc PDF gốc), gõ tay NGUYÊN VĂN phần chữ của trang vào\n"
          f"  {GOLD}\\<TICKER>_<NĂM>_p<TRANG>.txt  (UTF-8; bỏ tiêu đề/chân trang lặp lại, số trang, chú thích ảnh,\n"
          f"  chữ trong biểu đồ/bảng số; giữ nguyên chính tả, dấu câu; xuống dòng không quan trọng). Rồi chạy lại script này.")


def evaluate(gold_files):
    import fitz
    from textkit.llm_client import LLMClient
    from vn.v03_extract_letter import page_text, render_png
    L = CFG["vn"]["extract"]["llm"]
    client = LLMClient(L)
    lm = pd.read_csv(D("vn", "processed", "letters_meta.csv")).set_index(["ticker", "year"])
    rows, tones = [], []
    for g in gold_files:
        m = re.match(r"([A-Z0-9]+)_(\d{4})_p(\d+)\.txt$", g.name)
        if not m:
            continue
        tk, yr, pg = m.group(1), int(m.group(2)), int(m.group(3))
        ref = g.read_text(encoding="utf-8")
        doc = fitz.open(D("vn", "raw", "bctn", lm.loc[(tk, yr), "file"])); page = doc[pg - 1]
        ocr = page_text(doc, pg - 1, "vi", force_ocr=True)[0]
        png = render_png(page, L.get("dpi", 200))
        hyp = {"tesseract": ocr}
        for mode, key in [("text_fix", "llm_fix"), ("vision", "llm_vision")]:
            try:
                hyp[key] = client.transcribe_page(png, ocr, mode)["page_text"]
            except Exception as e:
                print(f"  ! {g.name} {mode}: {e}"); hyp[key] = None
        tones.append({"page": g.stem, "method": "gold", **tone(ref)})
        for k in METHODS:
            if hyp.get(k) is None:
                continue
            c, w = cer_wer(hyp[k], ref)
            rows.append(dict(page=g.stem, method=k, cer=round(c, 4), wer=round(w, 4), n_chars_gold=len(_norm(ref))))
            tones.append({"page": g.stem, "method": k, **tone(hyp[k])})
    ev, tn = pd.DataFrame(rows), pd.DataFrame(tones)
    mean = ev.groupby("method")[["cer", "wer"]].mean().reset_index().assign(page="TRUNG BÌNH", n_chars_gold=ev.n_chars_gold.sum())
    ev = pd.concat([ev, mean], ignore_index=True)
    ev.to_csv(O("vn", "ocr_eval.csv"), index=False, encoding="utf-8-sig")
    # lệch giọng điệu so với gold, theo phương án
    t = tn.pivot_table(index="page", columns="method", values=["fin_neg", "fin_net"])
    dev = []
    for k in METHODS:
        if ("fin_neg", k) in t:
            dev.append(dict(method=k, mae_fin_neg_pp=100 * (t[("fin_neg", k)] - t[("fin_neg", "gold")]).abs().mean(),
                            mae_fin_net=(t[("fin_net", k)] - t[("fin_net", "gold")]).abs().mean(),
                            corr_fin_net_vs_gold=t[("fin_net", k)].corr(t[("fin_net", "gold")])))
    pd.concat([tn, pd.DataFrame(dev)], ignore_index=True).round(5).to_csv(O("vn", "ocr_eval_tone.csv"), index=False, encoding="utf-8-sig")
    figure(mean)
    print(mean.round(4).to_string(index=False)); print(pd.DataFrame(dev).round(4).to_string(index=False))


def figure(mean):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    mean = mean.set_index("method").reindex([m for m in METHODS if m in set(mean.method)])
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), sharey=False)
    for ax, col, title in [(axes[0], "cer", "CER – tỷ lệ lỗi ký tự"), (axes[1], "wer", "WER – tỷ lệ lỗi từ")]:
        vals = 100 * mean[col]
        bars = ax.bar([LABELS[m] for m in mean.index], vals, color=[COLORS[m] for m in mean.index], width=.6)
        for b, v in zip(bars, vals):
            ax.annotate(f"{v:.1f}%", (b.get_x() + b.get_width() / 2, v), xytext=(0, 3), textcoords="offset points",
                        ha="center", color="#1d1d1b", fontsize=9)
        ax.set_title(title, loc="left", fontsize=10, color="#1d1d1b")
        ax.spines[["top", "right"]].set_visible(False); ax.grid(axis="y", color="#e6e5e1", lw=.6); ax.set_axisbelow(True)
        ax.tick_params(axis="x", labelsize=8, colors="#6b6a66"); ax.tick_params(axis="y", colors="#6b6a66")
        ax.set_ylabel("%", color="#1d1d1b")
    fig.tight_layout(); fig.savefig(O("vn", "fig_ocr_eval.png"), dpi=200); plt.close(fig)


def main():
    golds = sorted(GOLD.glob("*_p*.txt"))
    if not golds:
        export_instructions(choose_pages()); return
    evaluate(golds)


if __name__ == "__main__":
    main()
