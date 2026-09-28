"""A5 (TÙY CHỌN). Chấm giọng điệu bằng FinBERT để so với từ điển – ý tưởng từ rj694/earnings-sentiment.

Chỉ áp dụng văn bản tiếng Anh (10-K MD&A, hoặc BCTN bản tiếng Anh). FinBERT (ProsusAI/finbert) chấm từng câu
thành positive/negative/neutral; finbert_net = trung bình (P(pos) − P(neg)) của các câu.
Cần: pip install transformers torch  (CPU chạy được nhưng chậm; giới hạn max_sentences để tiết kiệm).
Kết quả: data/<mkt>/processed/finbert.csv → a03 tự thêm mô hình M8 và tương quan với fin_net.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))   # chạy trực tiếp: thêm src/
import argparse, gzip, re
import pandas as pd
from tqdm import tqdm
from common import D


def main(mkt, max_sentences=200):
    from transformers import pipeline
    clf = pipeline("text-classification", model="ProsusAI/finbert", top_k=None, truncation=True)
    docs = pd.read_csv(D(mkt, "processed", "docs.csv"))
    docs = docs[docs.flag.eq("ok") & docs.lang.eq("en")]
    rows = []
    for r in tqdm(docs.itertuples(), total=len(docs), desc="FinBERT"):
        name = r.text_alt if isinstance(r.text_alt, str) else r.text_main
        f = D(mkt, "interim", "text", name)
        text = gzip.open(f, "rt", encoding="utf-8").read() if name.endswith(".gz") else f.read_text(encoding="utf-8")
        sents = [s for s in re.split(r"(?<=[.!?])\s+", text) if 8 <= len(s.split()) <= 80][:max_sentences]
        if not sents:
            continue
        sc = [{d["label"]: d["score"] for d in out} for out in clf(sents, batch_size=16)]
        rows.append(dict(doc_id=r.doc_id, finbert_net=sum(s["positive"] - s["negative"] for s in sc) / len(sc)))
    pd.DataFrame(rows).to_csv(D(mkt, "processed", "finbert.csv"), index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--market", choices=["us", "vn"], required=True)
    main(ap.parse_args().market)
