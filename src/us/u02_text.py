"""US-2. Làm sạch 10-K → toàn văn + MD&A (Item 7) + Risk Factors (Item 1A), chạy song song.

Đầu ra
  data/us/interim/text/<stem>.<full|mdna|1a>.txt.gz
  data/us/processed/docs.csv  – bảng văn bản CHUẨN dùng chung với nhánh VN
        doc_id, ticker, year, event_date, after_close, lang, text_main, text_alt, industry, group, flag
QC (ý tưởng step2b/step4a của lm2011-replication): in tỷ lệ trích MD&A thành công theo năm và xuất
mẫu 30 đoạn MD&A để đọc tay: outputs/us/qc_mdna_sample.csv
"""
import gzip
from multiprocessing import Pool
import pandas as pd
from tqdm import tqdm
from common import CFG, D, O
from textkit import us_clean as ux

TXT = D("us", "interim", "text", "x").parent


def process(row):
    stem = row["file"].rsplit(".", 1)[0]
    try:
        raw = (D("us", "raw", "10k", row["file"])).read_bytes().decode("utf-8", errors="replace")
        full = ux.clean_primary_html(raw)
        mdna, st = ux.extract_mdna(full, row["form"])
        r1a, st1a = ux.extract_item1a(full)
        for sec, t in [("full", full), ("mdna", mdna), ("1a", r1a)]:
            if t:
                with gzip.open(TXT / f"{stem}.{sec}.txt.gz", "wt", encoding="utf-8") as fh:
                    fh.write(t)
        return dict(accession=row["accession"], n_tokens=len(ux.tokenize(full)), mdna_status=st,
                    mdna_tokens=len(mdna.split()) if mdna else 0, item1a_status=st1a, stem=stem)
    except Exception as e:
        return dict(accession=row["accession"], mdna_status=f"error:{type(e).__name__}", stem=stem)


def main(workers=4):
    man = pd.read_csv(D("us", "processed", "manifest.csv"), dtype={"cik": str, "sic": str})
    man = man[man.downloaded]
    with Pool(workers) as pool:
        res = list(tqdm(pool.imap_unordered(process, man.to_dict("records")), total=len(man), desc="Làm sạch 10-K"))
    m = man.merge(pd.DataFrame(res), on="accession")
    # acceptanceDateTime của EDGAR mang hậu tố 'Z' nhưng thực chất là giờ miền Đông (ET) – quirk đã biết.
    acc = pd.to_datetime(m.acceptance.str.slice(0, 19))
    docs = pd.DataFrame({
        "doc_id": m.accession, "ticker": m.ticker,
        "year": pd.to_datetime(m.period, errors="coerce").dt.year.fillna(pd.to_datetime(m.filing_date).dt.year - 1).astype(int),
        "event_date": acc.dt.normalize(), "after_close": acc.dt.hour >= 16, "lang": "en",
        "text_main": m.stem + ".full.txt.gz",
        "text_alt": (m.stem + ".mdna.txt.gz").where(m.mdna_status.str.startswith("ok")),
        "industry": m.sic.astype(str).str[:2], "group": "US",
        "flag": (m.n_tokens.fillna(0) >= 2000).map({True: "ok", False: "too_short"}),   # LM: ≥2.000 từ
    })
    docs.to_csv(D("us", "processed", "docs.csv"), index=False)
    m["fy"] = docs.year
    print("Tỷ lệ trích MD&A thành công theo năm:\n",
          m.groupby("fy").mdna_status.apply(lambda s: round(100 * s.str.startswith("ok").mean(), 1)).to_string())
    ok_ = m[m.mdna_status.str.startswith("ok")]; samp = ok_.sample(n=min(30, len(ok_)), random_state=CFG["seed"])
    samp[["ticker", "accession", "mdna_status", "mdna_tokens", "url"]].assign(dung_muc_mdna="", ghi_chu="").to_csv(
        O("us", "qc_mdna_sample.csv"), index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
