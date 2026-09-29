"""Demo trực tiếp: chấm giọng điệu một câu/đoạn bất kỳ bằng đúng bộ đếm từ của đồ án.

  python demo_tone.py "Năm nay ngân hàng gặp nhiều khó khăn, nợ xấu tăng nhưng lợi nhuận vẫn tăng trưởng."
  python demo_tone.py --en "The company reported a net loss and expects adverse litigation."
  python demo_tone.py --file data/vn/interim/text/MWG_2019_vi.txt      # cả một thư đã trích

So sánh từ điển tài chính (fin_vn / Loughran-McDonald) với từ điển tổng quát (VietSentiWordNet / Harvard GI)
để thấy vì sao từ điển tổng quát gắn nhãn sai trong văn bản tài chính (Mục tiêu 2).
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "src"))
import argparse
from textkit import dictionaries as dct
from textkit.scoring import VietScorer, EnglishScorer


def show(name, n, cnt, words):
    pos, neg = cnt.get("positive", 0), cnt.get("negative", 0)
    net = (pos - neg) / (pos + neg) if pos + neg else 0.0
    print(f"\n[{name}]  số từ = {n}  |  tiêu cực = {neg}  tích cực = {pos}  bất định = {cnt.get('uncertainty', 0)}"
          f"  |  net = (Pos-Neg)/(Pos+Neg) = {net:+.2f}")
    for c in ["negative", "positive", "uncertainty", "litigious"]:
        if words.get(c):
            print(f"   {c:<12}: " + ", ".join(f"{w} ×{k}" if k > 1 else w for w, k in words[c].most_common(15)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="?", help="câu/đoạn cần chấm")
    ap.add_argument("--file", help="đọc văn bản từ file UTF-8")
    ap.add_argument("--en", action="store_true", help="văn bản tiếng Anh (LM vs Harvard GI)")
    a = ap.parse_args()
    text = pathlib.Path(a.file).read_text(encoding="utf-8") if a.file else a.text
    if not text:
        ap.error("cần nhập câu hoặc --file")
    if a.en:
        lm = dct.load_lm(); master = lm.pop("master")
        fin, gen = EnglishScorer(lm, master), EnglishScorer(dct.load_harvard(), master)
        names = ("Tài chính: Loughran-McDonald", "Tổng quát: Harvard GI")
    else:
        fin, gen = VietScorer(dct.load_fin_vn()), VietScorer(dct.load_vswn())
        names = ("Tài chính: fin_vn", "Tổng quát: VietSentiWordNet")
    for nm, sc in zip(names, (fin, gen)):
        show(nm, *sc.run(text))


if __name__ == "__main__":
    main()
