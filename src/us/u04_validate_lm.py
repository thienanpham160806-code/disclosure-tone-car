"""US-4 (TÙY CHỌN, khuyên làm). Đối chiếu số đếm của nhóm với số liệu công bố của SRAF (LM 10X Summaries).

Ý tưởng từ lm2011-replication (step4 cross_check_vs_lm): nếu N_Words / N_Negative của ta lệch ít so với
file chính thức của Loughran–McDonald thì pipeline làm sạch + tách từ được kiểm chứng độc lập → điểm "tái lập".
Tải file "Loughran-McDonald_10X_Summaries_*.csv" tại https://sraf.nd.edu/sec-edgar-data/lm_10x_summaries/
và đặt vào thư mục dict/. Khác biệt nhỏ là bình thường (ta dùng file HTML chính, LM dùng toàn bộ hồ sơ .txt).

Hai phép đối chiếu:
  validate_vs_lm.csv          : biến chính (file HTML chính của 10-K) vs LM – khác PHẠM VI văn bản: LM đếm toàn bộ
                                hồ sơ gồm mọi exhibit (EX-13 báo cáo thường niên, EX-10 hợp đồng...).
  validate_vs_lm_fullsub.csv  : cùng phạm vi với LM – mẫu ngẫu nhiên N hồ sơ, tải toàn bộ hồ sơ .txt, làm sạch từng
                                <DOCUMENT> văn bản bằng cùng pipeline (clean_primary_html + tokenize + LM master)
                                → kiểm chứng khâu làm sạch/tách từ (CHANGELOG_RUN #9).
"""
import glob, re
import numpy as np, pandas as pd
from common import CFG, P, D, O


def _compare(j, pairs):
    rows = []
    for a, b in pairs:
        rel = (j[a] - j[b]) / j[b].where(j[b] > 0)
        rows.append(dict(bien=b, N=rel.notna().sum(), lech_trung_vi_pct=100 * rel.median(),
                         trong_2pct=100 * (rel.abs() <= .02).mean(), trong_5pct=100 * (rel.abs() <= .05).mean(),
                         tuong_quan=j[a].corr(j[b])))
    return pd.DataFrame(rows).round(3)


SKIP_TYPES = re.compile(r"^(GRAPHIC|ZIP|EXCEL|PDF|XML|JSON|EX-101|XBRL|ZIP)", re.IGNORECASE)
DOC_RE = re.compile(r"<DOCUMENT>\s*<TYPE>([^\s<]+).*?<TEXT>(.*?)</TEXT>", re.IGNORECASE | re.DOTALL)


def full_submission_counts(man, n, seed):
    """Tải toàn bộ hồ sơ .txt (cache data/us/raw/fullsub/) cho n hồ sơ ngẫu nhiên và đếm theo đúng pipeline."""
    from textkit import dictionaries as dct, us_clean as ux
    from textkit.scoring import EnglishScorer
    from us.edgar_client import get
    lm = dct.load_lm(); master = lm.pop("master"); sc = EnglishScorer(lm, master)
    rows = []
    for r in man.sample(n=n, random_state=seed).itertuples():
        a = r.accession.replace("-", "")
        f = D("us", "raw", "fullsub", f"{r.accession}.txt")
        if not f.exists():
            f.write_bytes(get(f"https://www.sec.gov/Archives/edgar/data/{int(r.cik)}/{a}/{r.accession}.txt").content)
        raw = f.read_bytes().decode("utf-8", errors="replace")
        text = "\n".join(ux.clean_primary_html(body) for typ, body in DOC_RE.findall(raw) if not SKIP_TYPES.match(typ))
        nw, c, _ = sc.run(text)
        rows.append(dict(doc_id=r.accession, ticker=r.ticker, n_words=nw, n_fin_neg=c["negative"], n_fin_pos=c["positive"]))
    return pd.DataFrame(rows)


def main(n_full=40):
    fs = glob.glob(str(P("dict", "Loughran-McDonald_10X_Summaries*.csv")))
    if not fs:
        print("Bỏ qua: chưa có file LM 10X Summaries trong dict/"); return
    lm = pd.read_csv(fs[-1], usecols=["ACC_NUM", "N_Words", "N_Negative", "N_Positive"], dtype={"ACC_NUM": str})
    lm["doc_id"] = lm.ACC_NUM.str.replace(r"^(\d{10})(\d{2})(\d{6})$", r"\1-\2-\3", regex=True)
    # hồ sơ gộp nhiều pháp nhân (SO, DUK, NEE, CMCSA...) xuất hiện 1 dòng/CIK với số liệu giống hệt → bỏ trùng
    lm = lm.drop_duplicates("doc_id")
    pairs = [("n_words", "N_Words"), ("n_fin_neg", "N_Negative"), ("n_fin_pos", "N_Positive")]
    me = pd.read_csv(D("us", "processed", "tone_panel.csv"))[["doc_id", "n_words", "n_fin_neg", "n_fin_pos"]]
    t = _compare(me.merge(lm, on="doc_id"), pairs)
    t.to_csv(O("us", "validate_vs_lm.csv"), index=False)
    print("Biến chính (file HTML chính) vs LM (toàn bộ hồ sơ):\n", t.to_string(index=False))

    man = pd.read_csv(D("us", "processed", "manifest.csv"), dtype={"cik": str})
    man = man[man.accession.isin(lm.doc_id)]
    fu = full_submission_counts(man, n_full, CFG["seed"]).merge(lm, on="doc_id")
    fu.to_csv(D("us", "processed", "validate_fullsub_sample.csv"), index=False)
    t2 = _compare(fu, pairs)
    t2.to_csv(O("us", "validate_vs_lm_fullsub.csv"), index=False)
    print(f"\nCùng phạm vi (toàn bộ hồ sơ .txt, {len(fu)} hồ sơ ngẫu nhiên) vs LM:\n", t2.to_string(index=False))


if __name__ == "__main__":
    main()
