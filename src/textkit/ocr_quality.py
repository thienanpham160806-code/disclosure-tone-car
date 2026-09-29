"""Chấm chất lượng văn bản tiếng Việt lấy từ PDF/OCR – quyết định trang nào cần tầng AI (v03 --llm).

quality_score(text) ∈ [0, 1], kết hợp 3 thành phần:
  (a) valid  – tỷ lệ token chữ là ÂM TIẾT TIẾNG VIỆT HỢP LỆ: có trong từ vựng (lexicon) HOẶC đúng cấu trúc âm tiết
               (phụ âm đầu + vần + phụ âm cuối, tối đa 1 dấu thanh). Lexicon = dict/fin_vn.csv + VietSentiWordNet
               + âm tiết xuất hiện ≥ 3 lần trong các thư lấy từ lớp chữ PDF sạch (data/vn/processed/vi_syllables.txt);
               lexicon giúp giữ các từ nước ngoài/viết tắt hay gặp (vd "ROE", "Vietcombank").
  (b) junk   – tỷ lệ ký tự rác: không phải chữ, số, khoảng trắng hay dấu câu thường gặp (vd « ® ¬ µ ‹ □ …,
               ký tự vùng riêng Unicode, "(cid:")
  (c) broken – tỷ lệ token đứt/hỏng: chữ lẫn số hoặc ký hiệu ("n1m", "t#ng", ",i6p"), hoặc 1 chữ cái lẻ không phải từ
score = 0.6·valid + 0.2·(1 − min(1, 10·junk)) + 0.2·(1 − min(1, 4·broken)); văn bản < 20 token → 0.
Văn bản sạch ~0,95–1; lỗi font TCVN3/VNI hoặc OCR vỡ ~0,3–0,7 (xem tests/test_ocr_quality.py).
"""
from __future__ import annotations
import functools, re, unicodedata

TONES = {"̀", "́", "̃", "̉", "̣"}   # huyền, sắc, ngã, hỏi, nặng (dạng NFD)
_ONSET = r"(?:ngh|ng|gh|gi|kh|nh|ph|th|tr|ch|qu|[bcdđghklmnpqrstvx])?"
_VOWEL = r"[aăâeêioôơuưy]{1,3}"
_CODA = r"(?:ch|ng|nh|[cmnpt])?"
SYLLABLE = re.compile(rf"^{_ONSET}{_VOWEL}{_CODA}$")
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)                  # chuỗi chữ cái liền nhau
TOKEN = re.compile(r"\S+")
SINGLE_OK = set("aàáảãạăâeêoòóỏõọôơưuúùyýiíìởỷạ")         # chữ cái đơn có thể là từ / ký hiệu hợp lệ
PUNCT = set(".,;:!?()[]{}%-–—‒\"'“”‘’/&+*=<>•·…_#@$€£²³°§|\\~")


def _base(syll: str) -> tuple[str, int]:
    """Bỏ dấu THANH (giữ ă â ê ô ơ ư đ); trả về (âm tiết không thanh, số dấu thanh)."""
    d = unicodedata.normalize("NFD", syll)
    n_tone = sum(c in TONES for c in d)
    return unicodedata.normalize("NFC", "".join(c for c in d if c not in TONES)), n_tone


@functools.lru_cache(maxsize=200_000)
def is_vietnamese_syllable(tok: str) -> bool:
    t = unicodedata.normalize("NFC", tok.lower())
    base, n_tone = _base(t)
    return n_tone <= 1 and bool(SYLLABLE.match(base))


@functools.lru_cache(maxsize=1)
def default_lexicon() -> frozenset:
    """Từ vựng mặc định (âm tiết, chữ thường, NFC). Thiếu file nào thì bỏ qua file đó."""
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[2]
    words: set[str] = set()
    f = root / "data" / "vn" / "processed" / "vi_syllables.txt"
    if f.exists():
        words |= {w.strip() for w in f.read_text(encoding="utf-8").splitlines() if w.strip()}
    for f in [root / "dict" / "fin_vn.csv"]:
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines()[1:]:
                words |= set(unicodedata.normalize("NFC", line.split(",")[0].lower()).split())
    f = root / "dict" / "VietSentiWordnet_Ver1.3.5.txt"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            c = line.split("\t")
            if len(c) >= 5 and not line.startswith("#"):
                for term in re.split(r"#\d+", c[4]):
                    words |= set(unicodedata.normalize("NFC", term.replace("_", " ").lower()).split())
    return frozenset(words)


def quality_detail(text: str, lexicon=None) -> dict:
    text = unicodedata.normalize("NFC", text or "")
    lex = default_lexicon() if lexicon is None else lexicon
    toks = TOKEN.findall(text)
    if len(toks) < 20:
        return dict(score=0.0, valid=0.0, junk=0.0, broken=0.0, n_tokens=len(toks))
    chars = [c for c in text if not c.isspace()]
    junk = sum(not (c.isalpha() or c.isdigit() or c in PUNCT) or 0xE000 <= ord(c) <= 0xF8FF for c in chars) / max(len(chars), 1)
    junk = min(1.0, junk + 5 * text.count("(cid:") / max(len(chars), 1))
    words, broken = [], 0
    for t in toks:
        core = t.strip("".join(PUNCT))
        if not core:
            continue
        if re.fullmatch(r"[\d.,%]+", core):                    # số thuần – trung tính
            continue
        ws = WORD.findall(core)
        if not ws:
            broken += 1; continue
        if len(ws) > 1 or len(ws[0]) < len(core):              # chữ lẫn số/ký hiệu: "n1m", "t#ng", ",i6p"
            broken += 1
        for w in ws:
            lw = w.lower()
            if len(lw) == 1 and lw not in SINGLE_OK:
                broken += 1
            words.append(lw)
    n_core = max(len(words), 1)
    valid = sum(w in lex or is_vietnamese_syllable(w) for w in words) / n_core
    broken = broken / n_core
    score = 0.6 * valid + 0.2 * (1 - min(1.0, 10 * junk)) + 0.2 * (1 - min(1.0, 4 * broken))
    return dict(score=round(score, 4), valid=round(valid, 4), junk=round(junk, 4), broken=round(broken, 4), n_tokens=len(toks))


def quality_score(text: str, lexicon=None) -> float:
    """Điểm chất lượng 0..1 (xem docstring của module)."""
    return quality_detail(text, lexicon)["score"]


def build_lexicon(texts, min_count: int = 3) -> list[str]:
    """Âm tiết xuất hiện ≥ min_count lần trong các văn bản sạch (lớp chữ PDF) → danh sách để lưu vi_syllables.txt."""
    import collections
    cnt = collections.Counter(w.lower() for t in texts for w in WORD.findall(unicodedata.normalize("NFC", t)))
    return sorted(w for w, k in cnt.items() if k >= min_count)
