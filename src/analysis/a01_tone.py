"""A1. Chỉ số giọng điệu (Mục tiêu 1) + so sánh từ điển tài chính vs tổng quát (Mục tiêu 2). Dùng chung US/VN.

                   Từ điển TÀI CHÍNH (fin_*)      Từ điển TỔNG QUÁT (gen_*)
  Mỹ / BCTN tiếng Anh   Loughran–McDonald             Harvard GI IV-4
  BCTN tiếng Việt       dict/fin_vn.csv               VietSentiWordNet
Biến: *_neg, *_pos, *_unc, *_lit, *_net = (Pos−Neg)/(Pos+Neg), *_neg_tfidf (LM eq.1).
Văn bản chính = toàn văn 10-K (Mỹ) / thông điệp HĐQT (VN); văn bản phụ = MD&A (Mỹ) → biến finA_*.
Đầu ra: data/<mkt>/processed/tone_panel.csv; outputs/<mkt>/misclassified_general_neg.csv,
        dictionary_comparison.txt, (VN) candidate_terms.csv để mở rộng từ điển.
"""
import argparse, collections, gzip
import pandas as pd
from tqdm import tqdm
from common import CFG, D, O, winsor, norm_vi
from textkit import dictionaries as dct
from textkit.scoring import EnglishScorer, VietScorer, indices, tfidf_scores, TOK_VI


def read(mkt, name):
    f = D(mkt, "interim", "text", name)
    return gzip.open(f, "rt", encoding="utf-8").read() if name.endswith(".gz") else f.read_text(encoding="utf-8")


def scorers(need_en, need_vi):
    sc = {}
    if need_en:
        lm = dct.load_lm(); master = lm.pop("master")
        sc["en"] = (EnglishScorer(lm, master), EnglishScorer(dct.load_harvard(), master))
    if need_vi:
        sc["vi"] = (VietScorer(dct.load_fin_vn()), VietScorer(dct.load_vswn()))
    return sc


def main(mkt):
    docs = pd.read_csv(D(mkt, "processed", "docs.csv"))
    docs = docs[docs.flag.eq("ok")].reset_index(drop=True)
    sc = scorers((docs.lang == "en").any(), (docs.lang == "vi").any())
    rows, fneg, gneg, lens, fnegA, lensA = [], [], [], [], [], []
    gen_hits = collections.Counter()
    fin_neg_all = set().union(*[f.dic["negative"] if hasattr(f, "dic") else
                                {" ".join(k) for k, v in f.map.items() if "negative" in v} for f, _ in sc.values()])
    bigr = collections.Counter()
    for r in tqdm(docs.itertuples(), total=len(docs), desc=f"Tone {mkt}"):
        fin, gen = sc[r.lang]
        text = read(mkt, r.text_main)
        n, cf, wf = fin.run(text); _, cg, wg = gen.run(text)
        row = dict(doc_id=r.doc_id, n_words=n, n_fin_neg=cf["negative"], n_fin_pos=cf["positive"], **indices("fin", n, cf), **indices("gen", n, cg))
        fneg.append(wf["negative"]); gneg.append(wg["negative"]); lens.append(n)
        gen_hits.update({(w, r.lang): k for w, k in wg["negative"].items()})
        if isinstance(r.text_alt, str) and r.text_alt:
            nA, cA, wA = fin.run(read(mkt, r.text_alt))
            row.update({"n_words_alt": nA, **{k.replace("fin_", "finA_"): v for k, v in indices("fin", nA, cA).items()}})
            fnegA.append(wA["negative"]); lensA.append(nA)
        else:
            fnegA.append(collections.Counter()); lensA.append(0)
        if r.lang == "vi":
            t = TOK_VI.findall(norm_vi(text)); bigr.update(zip(t, t[1:]))
        rows.append(row)
    tone = pd.DataFrame(rows)
    tone["fin_neg_tfidf"] = tfidf_scores(fneg, lens)
    tone["gen_neg_tfidf"] = tfidf_scores(gneg, lens)
    if any(lensA):
        tone["finA_neg_tfidf"] = tfidf_scores(fnegA, lensA)
    for c in [c for c in tone if c.startswith(("fin", "gen"))]:
        tone[c] = winsor(tone[c])
    tone = docs[["doc_id", "ticker", "year", "lang", "group", "industry"]].merge(tone, on="doc_id")
    tone.to_csv(D(mkt, "processed", "tone_panel.csv"), index=False)

    # ---- Mục tiêu 2: từ tổng quát-tiêu cực KHÔNG thuộc danh sách tiêu cực tài chính ----
    g = pd.DataFrame([(w, lg, k) for (w, lg), k in gen_hits.items()], columns=["word", "lang", "freq"])
    g = g.groupby("word", as_index=False).freq.sum().sort_values("freq", ascending=False)
    g["in_fin_negative"] = g.word.isin(fin_neg_all)
    g["share_pct"] = (100 * g.freq / g.freq.sum()).round(2)
    g.head(50).assign(nghia_trong_tai_chinh="").to_csv(O(mkt, "misclassified_general_neg.csv"), index=False, encoding="utf-8-sig")
    noise = 100 * g.loc[~g.in_fin_negative, "freq"].sum() / max(g.freq.sum(), 1)
    corr = tone[["fin_neg", "gen_neg", "fin_net", "gen_net"]].corr().round(3)
    O(mkt, "dictionary_comparison.txt").write_text(
        f"Số văn bản: {len(tone)}\nTỷ lệ 'nhiễu' của từ điển tổng quát (tần suất từ tiêu cực tổng quát "
        f"không nằm trong danh sách tiêu cực tài chính): {noise:.1f}%\n\nTương quan:\n{corr}\n", encoding="utf-8")
    if bigr:  # gợi ý mở rộng từ điển tiếng Việt – duyệt tay giống cách LM (2011) xây từ điển
        known = set(sc["vi"][0].map) | set(sc["vi"][1].map)
        cand = [(" ".join(b), k) for b, k in bigr.most_common(4000) if b not in known][:400]
        pd.DataFrame(cand, columns=["term", "freq"]).assign(category="").to_csv(
            O(mkt, "candidate_terms.csv"), index=False, encoding="utf-8-sig")
    print(tone.filter(regex="^(fin|gen)_").describe().T.round(4).to_string())
    print(f"Nhiễu từ điển tổng quát: {noise:.1f}%")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--market", choices=["us", "vn"], required=True)
    main(ap.parse_args().market)
