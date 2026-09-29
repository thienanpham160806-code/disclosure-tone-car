"""B2. Crawl toàn bộ Báo cáo thường niên (BCTN) của VN30 + VN100 từ CafeF + ứng viên ngày công bố.

Endpoint CafeF (đã kiểm tra 27/09/2026):
  https://cafef.vn/du-lieu/Ajax/PageNew/FileBCTC.ashx?Symbol=VNM&Type=3&Year=0
    → Type=3: tài liệu doanh nghiệp (BCTN, điều lệ), trường Time dạng "CN/2024" (KHÔNG có ngày)
  ...&Type=4 → công bố thông tin có ngày (Time = dd-mm-yyyy): nghị quyết, tài liệu ĐHĐCĐ...
JSON: {"Data":[{id,Type,Quarter,Year,Time,Name,IconFile,Link}], "Success":..., "Message":...}

Ngày sự kiện (T=0) – thứ tự ưu tiên, lưu hết để kiểm tra tay:
  d_cbtt   : ngày tin CBTT có chữ "báo cáo thường niên" trên CafeF Type=4 (năm Y+1)
  d_lastmod: header Last-Modified của file PDF BCTN (ngày upload lên CDN) nếu rơi vào 01/01–31/07 năm Y+1
  d_pdf    : ngày ModDate (dự phòng CreationDate) trong metadata của file PDF – thay Last-Modified vì CDN CafeF
             không gửi header này (kiểm tra 27/09/2026); cùng điều kiện 01/01–31/07 năm Y+1 và không muộn hơn
             ngày Nghị quyết ĐHĐCĐ thường niên (người dùng duyệt 27/09/2026, CHANGELOG_RUN #14)
  d_agm_doc: ngày sớm nhất của tài liệu/thông báo họp ĐHĐCĐ thường niên năm Y+1 (BCTN thường nằm trong bộ tài liệu này)
  d_agm_res: ngày Nghị quyết ĐHĐCĐ thường niên năm Y+1 – CHỈ dùng làm cận trên để kiểm tra, không làm T=0
Chạy lại an toàn: file đã tải sẽ bỏ qua (cache).
"""
import sys, pathlib
_SRC = pathlib.Path(__file__).resolve().parents[1]   # chạy trực tiếp: thêm src/, bỏ src/vn (vn/http.py che module http chuẩn)
sys.path[:] = [str(_SRC)] + [p for p in sys.path if pathlib.Path(p or ".").resolve() != _SRC / "vn"]
import re, json, argparse
import fitz
import pandas as pd
from tqdm import tqdm
from email.utils import parsedate_to_datetime
from common import CFG, P, D, norm_vi as norm
from vn.http import session, polite_get
V = CFG["vn"]

API = "https://cafef.vn/du-lieu/Ajax/PageNew/FileBCTC.ashx"
RAW = D("vn", "raw", "bctn", "x").parent
CACHE = D("vn", "raw", "cafef_json", "x").parent


def list_docs(s, tk, typ):
    f = CACHE / f"{tk}_t{typ}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    r = polite_get(s, API, params={"Symbol": tk, "Type": typ, "Year": 0})
    data = (r.json().get("Data") if r is not None else None) or []
    f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def lang_of(name):
    n = norm(name)
    return "en" if re.search(r"tiếng anh|english|\(en\)|\ben\b", n) else "vi"


def pick_dates(t4, year):
    """Các ứng viên ngày công bố BCTN năm `year` từ danh sách CBTT (Type=4)."""
    rows = []
    for d in t4:
        try:
            dt = pd.to_datetime(d.get("Time"), format="%d-%m-%Y")
        except Exception:
            continue
        if dt.year != year + 1:
            continue
        rows.append((dt, norm(d.get("Name", ""))))
    cbtt = [dt for dt, n in rows if "thường niên" in n and "báo cáo" in n]
    agm = [dt for dt, n in rows if re.search(r"(đại hội|đhđcđ|đhcđ).*thường niên|thường niên.*(đại hội|đhđcđ|đhcđ)", n)
           and re.search(r"tài liệu|mời họp|thông báo|chương trình", n)]
    res = [dt for dt, n in rows if "nghị quyết" in n and "thường niên" in n and re.search(r"đại hội|đhđcđ|đhcđ|cổ đông", n)]
    return (min(cbtt) if cbtt else pd.NaT), (min(agm) if agm else pd.NaT), (min(res) if res else pd.NaT)


ARCHIVES = (".zip", ".rar", ".7z")
BSDTAR = pathlib.Path("C:/Windows/System32/tar.exe")      # libarchive: giải nén được cả rar, 7z


def pdf_from_archive(content, name):
    """Lưu file nén vào data/vn/raw/bctn_archives/, trả về nội dung PDF lớn nhất bên trong (None nếu không được).
    CHANGELOG_RUN #27: 14 BCTN trên CafeF là .zip/.rar/.7z và trước đây bị bỏ qua."""
    import io, shutil, subprocess, tempfile, zipfile
    arch = D("vn", "raw", "bctn_archives", name); arch.write_bytes(content)
    try:
        if content[:2] == b"PK":
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                pdfs = [i for i in z.infolist() if i.filename.lower().endswith(".pdf")]
                return z.read(max(pdfs, key=lambda i: i.file_size)) if pdfs else None
        tool = str(BSDTAR) if BSDTAR.exists() else shutil.which("bsdtar")
        if not tool:
            return None
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([tool, "-xf", str(arch), "-C", tmp], check=True, capture_output=True)
            pdfs = sorted(pathlib.Path(tmp).rglob("*.pdf"), key=lambda q: q.stat().st_size)
            return pdfs[-1].read_bytes() if pdfs else None
    except Exception as e:
        print(f"  ! giải nén {name}: {e}")
        return None


def pdf_dates(f):
    """(ModDate, CreationDate) trong metadata PDF, dạng 'D:YYYYMMDDhhmmss+07'00''."""
    try:
        m = fitz.open(f).metadata or {}
    except Exception:
        return pd.NaT, pd.NaT
    conv = lambda v: pd.to_datetime(re.sub(r"^D:", "", v or "")[:8], format="%Y%m%d", errors="coerce")
    return conv(m.get("modDate")), conv(m.get("creationDate"))


def main(limit=None):
    s = session()
    tickers = pd.read_csv(P(V["tickers_file"]))
    if limit: tickers = tickers.head(limit)
    y0, y1 = V["years"]
    rows = []
    for tk, grp in tqdm(tickers[["ticker", "group"]].itertuples(index=False), total=len(tickers), desc="Mã"):
        t3, t4 = list_docs(s, tk, 3), list_docs(s, tk, 4)
        for d in t3:
            name, link = d.get("Name", ""), d.get("Link", "")
            if "thường niên" not in norm(name) or not link.lower().endswith((".pdf",) + ARCHIVES):
                continue
            yr = int(d.get("Year") or 0)
            if not (y0 <= yr <= y1):
                continue
            lg = lang_of(name)
            f = RAW / f"{tk}_{yr}_{lg}.pdf"
            lastmod = pd.NaT
            if not f.exists():
                r = polite_get(s, link)
                if (r is None or not r.content.startswith(b"%PDF")) and "cafefnew.mediacdn.vn" in link:
                    # CDN mới trả 404 cho nhiều file 2016–2021; bản gốc còn trên host cũ (CHANGELOG_RUN #17)
                    r = polite_get(s, link.replace("cafefnew.mediacdn.vn", "cafef1.mediacdn.vn"))
                if r is not None and link.lower().endswith(ARCHIVES):   # BCTN nén (zip/rar/7z) → lấy PDF lớn nhất bên trong
                    pdf = pdf_from_archive(r.content, f"{tk}_{yr}_{lg}{link[link.rfind('.'):]}")
                    if pdf is None:
                        rows.append(dict(ticker=tk, group=grp, year=yr, lang=lg, url=link, file=None, status="archive_fail")); continue
                    f.write_bytes(pdf); r = None
                elif r is None or not r.content.startswith(b"%PDF"):
                    rows.append(dict(ticker=tk, group=grp, year=yr, lang=lg, url=link, file=None, status="download_fail")); continue
                else:
                    f.write_bytes(r.content)
                lm = r.headers.get("Last-Modified") if r is not None else None
                if lm: lastmod = pd.Timestamp(parsedate_to_datetime(lm)).tz_localize(None).normalize()
            d_cbtt, d_agm, d_res = pick_dates(t4, yr)
            d_mod, d_cre = pdf_dates(f)
            rows.append(dict(ticker=tk, group=grp, year=yr, lang=lg, name=name, url=link, file=f.name,
                             size_mb=round(f.stat().st_size / 1e6, 2), d_cbtt=d_cbtt, d_lastmod=lastmod,
                             d_pdf_mod=d_mod, d_pdf_create=d_cre, d_agm_doc=d_agm, d_agm_res=d_res, status="ok"))
    meta = pd.DataFrame(rows)
    old = D("vn", "processed", "bctn_meta.csv")
    if old.exists():  # giữ Last-Modified đã ghi ở lần chạy trước
        prev = pd.read_csv(old, parse_dates=["d_lastmod"])[["file", "d_lastmod"]].dropna()
        meta = meta.merge(prev, on="file", how="left", suffixes=("", "_old"))
        meta["d_lastmod"] = meta["d_lastmod"].fillna(meta.pop("d_lastmod_old"))
    # chọn ngày sự kiện theo thứ tự ưu tiên
    ok_lm = meta.d_lastmod.where((meta.d_lastmod.dt.year == meta.year + 1) & (meta.d_lastmod.dt.month <= 7))
    ok_date = lambda d: d.where((d.dt.year == meta.year + 1) & (d.dt.month <= 7) &
                                (meta.d_agm_res.isna() | (d <= meta.d_agm_res)))
    ok_pdf = ok_date(meta.d_pdf_mod).fillna(ok_date(meta.d_pdf_create))
    meta["event_date"] = meta.d_cbtt.fillna(ok_lm).fillna(ok_pdf).fillna(meta.d_agm_doc)
    meta["event_src"] = (meta.d_cbtt.notna().map({True: "cbtt"}).fillna(ok_lm.notna().map({True: "lastmod"}))
                         .fillna(ok_pdf.notna().map({True: "pdf_meta"}))
                         .fillna(meta.d_agm_doc.notna().map({True: "agm_doc", False: "missing"})))
    meta.to_csv(old, index=False)
    print(meta.groupby(["status", "lang"]).size().to_string())
    print("Nguồn ngày sự kiện:\n", meta.event_src.value_counts().to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--limit", type=int, help="chạy thử N mã đầu")
    main(ap.parse_args().limit)
