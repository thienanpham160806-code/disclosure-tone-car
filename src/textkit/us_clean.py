"""
Làm sạch 10-K + trích MD&A + tách từ theo phụ lục Loughran & McDonald (2011).

NGUỒN: phần lớn file này sao chép từ repo m4a1ak471994/lm2011-replication (code/mdna_extract.py),
giấy phép MIT – Copyright (c) tác giả repo đó. Xem CREDITS.md.
Những gì GIỮ NGUYÊN (điểm mạnh của họ):
  • bỏ bảng có >25% ký tự là số, bỏ khối <ix:hidden> (inline XBRL), nối từ bị gạch nối xuống dòng
  • trích MD&A nhiều tầng (Item 7 → số La Mã → tiêu đề trần), duyệt vị trí bắt đầu TỪ CUỐI LÊN để né mục lục
  • tách từ đúng phụ lục LM: ≥2 chữ cái, cho phép gạch nối
Những gì CHÚNG TA THÊM:
  • clean_primary_html(): xử lý file HTML chính tải từ submissions API (repo gốc chỉ xử lý file .txt đầy đủ)
  • gỡ thẻ inline (<span>, <font>, <ix:*>) KHÔNG chèn khoảng trắng để không cắt đôi từ "B</span><span>USINESS"
    – ý tưởng từ lefterisloukas/edgar-crawler (GPL-3.0, chỉ tham khảo ý tưởng, không chép code)
  • extract_item1a() cho mục Rủi ro (Item 1A) để làm kiểm định độ vững
"""

from __future__ import annotations

import html
import re
import unicodedata
from pathlib import Path

# --------------------------------------------------------------------------- #
# 1. Document cleaning                                                        #
# --------------------------------------------------------------------------- #

# Match <TYPE>10-K (or family) … and grab the body of THAT <DOCUMENT>.
DOC_BLOCK_RE = re.compile(
    r"<DOCUMENT>\s*<TYPE>(?P<type>10-?K(?:SB)?(?:40)?(?:405)?(?:T)?(?:/A)?)"
    r"[^<]*?(?:<SEQUENCE>[^<]*)?(?:<FILENAME>[^<]*)?(?:<DESCRIPTION>[^<]*)?"
    r"<TEXT>(?P<body>.*?)</TEXT>\s*</DOCUMENT>",
    re.IGNORECASE | re.DOTALL,
)

# Binary / non-text blocks inside <TEXT>…</TEXT> we should drop wholesale.
BIN_BLOCK_RE = re.compile(
    r"<(PDF|GRAPHIC|ZIP|EXCEL|JSON|XML|XBRL)>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)

# Encoded uuencode/base64 streams (older filings embed images this way).
UU_RE = re.compile(r"begin\s+\d{3}\s+\S+\n.*?\nend\s*\n", re.DOTALL)

# Inline-XBRL hidden-fact blocks: <ix:hidden>...</ix:hidden> wraps content tagged
# for machine readers but NOT rendered to humans. The content inside is often
# numeric (durations, CIK numbers, GAAP URIs — harmless), but in early-adopter
# filings (2019-2022) can include duplicated narrative prose that would inflate
# N_Words / N_Negative if it survived into the token stream. Strip these blocks
# entirely before the general tag strip. (Pre-2009 filings have no inline XBRL,
# so this is a no-op on the LM in-sample window.)
IX_HIDDEN_RE = re.compile(r"<ix:hidden\b[^>]*>.*?</ix:hidden>",
                          re.IGNORECASE | re.DOTALL)

# Strip ALL remaining tags (HTML / SGML / inline XBRL like <ix:…>).
TAG_RE = re.compile(r"<[^>]+>")

# Whitespace cleanup.
WS_RE = re.compile(r"[ \t\f\v]+")
NL_RE = re.compile(r"\n{3,}")


def _normalize_unicode(s: str) -> str:
    """Map curly quotes, fancy dashes, NBSP to ASCII equivalents."""
    s = unicodedata.normalize("NFKC", s)
    table = {
        "‘": "'", "’": "'", "‚": "'", "‛": "'",
        "“": '"', "”": '"', "„": '"', "‟": '"',
        "–": "-", "—": "-", "−": "-", "­": "-",
        " ": " ", " ": "\n", " ": "\n",
    }
    return s.translate(str.maketrans(table))


# Match the 10-K / 10-K405 primary submission. Explicit alternation on TYPE
# rules out 10-KSB / 10-KT / 10-K/A. Trailing \s prevents 10-K matching inside
# 10-KSB. (Per LM 2011 appendix: 10-K and 10-K405 only.)
DOC10K_RE = re.compile(
    r"<DOCUMENT>\s*<TYPE>(?P<type>10-K405|10K405|10-K|10K)\s+"
    r"(?P<header>.*?)"           # consumes optional <SEQUENCE>/<FILENAME>/...
    r"<TEXT>(?P<body>.*?)(?:</TEXT>|</DOCUMENT>)",
    re.IGNORECASE | re.DOTALL,
)

# Tables: match an entire <TABLE>...</TABLE> block (with optional attributes).
TABLE_RE = re.compile(r"<TABLE[^>]*>.*?</TABLE>", re.IGNORECASE | re.DOTALL)

# Hyphen followed by line-feed: word continuation; replace with hyphen only.
HYPH_LF_RE = re.compile(r"-\s*\n\s*")


def _table_is_numeric_heavy(table_html: str, threshold: float = 0.25) -> bool:
    """Per LM (2011): remove a <TABLE> if >25% of its nonblank chars are digits."""
    # Strip tags and entities from the table for the count
    inside = TAG_RE.sub(" ", html.unescape(table_html))
    chars = re.sub(r"\s+", "", inside)
    if not chars:
        return False
    digits = sum(1 for c in chars if c.isdigit())
    return digits / len(chars) > threshold


def clean_text(raw: str) -> str:
    """
    LM (2011) Appendix Section I parsing pipeline:
      1. Take the <TYPE>10-K or <TYPE>10-K405 DOCUMENT only (drop EX-* exhibits).
      2. Remove SEC header (implicit — we slice after <TEXT>).
      3. Re-encode HTML entities (&nbsp; → space, &amp; → &, etc.).
      4. Remove encoded graphics / binary blobs.
      5. Remove tables where > 25% of nonblank chars are digits.
      6. Replace 'hyphen + line-feed' with 'hyphen' so multi-line hyphenated
         words tokenize correctly.
      7. Strip remaining HTML tags.
      8. Normalize Unicode → ASCII; uppercase; collapse whitespace.

    Returns the cleaned, uppercased body text. Tokenization (and dictionary
    lookup) happens in step 4, not here.
    """
    # 1. Find the 10-K / 10-K405 primary document. If none, return empty
    #    string (the caller will tally as 0 words and the filing gets filtered).
    m = DOC10K_RE.search(raw)
    if not m:
        return ""
    body = m.group("body")

    # 2. Remove binary subdocuments and uuencode streams (covers encoded graphics).
    body = BIN_BLOCK_RE.sub(" ", body)
    body = UU_RE.sub(" ", body)

    # 3. Strip inline-XBRL hidden-fact blocks BEFORE entity decoding & tag strip.
    #    These wrap content tagged for machines but not rendered to humans.
    body = IX_HIDDEN_RE.sub(" ", body)

    # 4. Decode HTML entities BEFORE table-filtering and tag-stripping.
    body = html.unescape(body)

    # 4. Remove numeric-heavy tables. Iterate so we don't accidentally
    #    delete tables that are mostly text (e.g., the table of contents).
    def _table_repl(mm: re.Match) -> str:
        return " " if _table_is_numeric_heavy(mm.group(0)) else mm.group(0)
    body = TABLE_RE.sub(_table_repl, body)

    # 5. Hyphen + line-feed → hyphen.
    body = HYPH_LF_RE.sub("-", body)

    # 6. Strip remaining tags.
    body = TAG_RE.sub(" ", body)

    # 7. Normalize unicode.
    body = _normalize_unicode(body)

    # 8. Uppercase + whitespace cleanup.
    body = body.upper()
    body = WS_RE.sub(" ", body)
    body = NL_RE.sub("\n\n", body)
    return body.strip()


# --------------------------------------------------------------------------- #
# 2. MD&A extraction (tiered, form-aware)                                     #
# --------------------------------------------------------------------------- #
#
# Three filing-type patterns to handle:
#   - 10-K / 10-K405      ITEM 7 = MD&A, end at ITEM 7A or ITEM 8
#   - 10-KSB family       ITEM 6 = MD&A, end at ITEM 7
#   - Roman-numeral 10-KSB  VI. = MD&A, end at next Roman numeral or "FINANCIAL"
# Plus a content-based fallback when section numbering is absent.

# Apostrophe variants: ASCII ', curly ', or fully omitted ("MANAGEMENTS"). The
# common token is the phrase "MANAGEMENT('S) DISCUSSION (AND ANALYSIS)?".
_MD_PHRASE = r"MANAGEMENT(?:\s*['’]\s*S|S)?\s+DISCUSSION(?:\s+AND\s+ANALYSIS)?"

# Tier 1: form-aware ITEM N start.
_T1_10K  = re.compile(rf"ITEM\s*7[\.\s\-:\)]+(?:.{{0,400}}?){_MD_PHRASE}",
                      re.IGNORECASE | re.DOTALL)
_T1_10KSB = re.compile(rf"ITEM\s*6[\.\s\-:\)]+(?:.{{0,400}}?){_MD_PHRASE}",
                       re.IGNORECASE | re.DOTALL)

# Tier 2: Roman numeral section header (V., VI., VII., VIII.) + MD&A within range.
# Anchored to start-of-line to avoid mid-sentence Roman numerals.
_T2_ROMAN = re.compile(
    rf"(?:^|\n)\s*(?:[IVX]+\.)\s*(?:.{{0,200}}?){_MD_PHRASE}",
    re.IGNORECASE | re.DOTALL,
)

# Tier 3: bare phrase fallback — match the heading at start of a line, no
# section-number prefix required. Riskier (may match cross-references).
_T3_BARE = re.compile(
    rf"(?:^|\n)\s*{_MD_PHRASE}",
    re.IGNORECASE,
)

# End boundary candidates (tried in order; first match after start wins).
_END_PATTERNS = [
    re.compile(r"ITEM\s*7\s*A[\.\s\-:\)]", re.IGNORECASE),                     # 10-K post-1998
    re.compile(r"ITEM\s*8[\.\s\-:\)]+(?:.{0,200}?)FINANCIAL\s+STATEMENTS",     # 10-K
              re.IGNORECASE | re.DOTALL),
    re.compile(r"ITEM\s*7[\.\s\-:\)]+(?:.{0,200}?)FINANCIAL\s+STATEMENTS",     # 10-KSB
              re.IGNORECASE | re.DOTALL),
    re.compile(r"QUANTITATIVE\s+AND\s+QUALITATIVE\s+DISCLOSURES",              # content-based
              re.IGNORECASE),
    re.compile(r"REPORT\s+OF\s+(?:INDEPENDENT|MANAGEMENT)", re.IGNORECASE),    # auditors' report
    re.compile(r"CONSOLIDATED\s+BALANCE\s+SHEETS?", re.IGNORECASE),            # financial stmts proxy
]

MIN_MDNA_WORDS = 250
MAX_MDNA_WORDS = 100_000  # sanity ceiling

# ---- BỔ SUNG CỦA NHÓM (sửa lỗi khi chạy dữ liệu thật, xem CHANGELOG_RUN.md #6) ----
# File HTML chính của 10-K hiện đại có rất nhiều câu DẪN CHIẾU giữa đoạn, vd
#   'SEE ITEM 7 OF PART II, "MANAGEMENT'S DISCUSSION ..."'  hoặc tiêu đề lặp đầu trang '... (CONTINUED)'.
# Pattern tier 1 gốc (.{0,400}? giữa ITEM 7 và cụm MD&A) + quy tắc "chọn điểm bắt đầu cuối cùng" bắt trúng
# chính các dẫn chiếu này (AMZN, CAT, HD, F, TRV, PEP...). Với file HTML (có xuống dòng theo khối) ta yêu cầu:
#   • tiêu đề và mốc kết thúc ĐỨNG ĐẦU DÒNG;
#   • bỏ dòng tiêu đề có dấu nháy / "(CONTINUED)" / theo sau là dòng chỉ có số trang (mục lục);
#   • chọn đoạn DÀI NHẤT trong các điểm bắt đầu hợp lệ (tiêu đề lặp đầu trang cho đoạn ngắn hơn).
_T1_10K_LINE = re.compile(rf"(?:^|\n)[ \t]*(?:PART\s+II[\s,\.\-]*)?ITEM\s*7\s*[\.\-:\)]*\s*{_MD_PHRASE}", re.IGNORECASE)
_T3_BARE_LINE = re.compile(rf"(?:^|\n)[ \t]*(?:COMBINED\s+)?{_MD_PHRASE}", re.IGNORECASE)   # SO: "COMBINED MANAGEMENT'S..."
_END_PATTERNS_LINE = [re.compile(r"\n[ \t]*" + p.pattern, p.flags) for p in _END_PATTERNS]
_BAD_HEADING = re.compile(r"[\"']|\(CONTINUED\)|\bSEE\b|\bREFER\b|\bPAGES?\s*\d")
_TOC_NEXT = re.compile(r"^[^\n]*\n(?:[ \t]*\n)*(?:[^\n]*\n(?:[ \t]*\n)*)?[ \t]*(?:[IVX]{1,4}-)?\d{1,3}[ \t]*\n")


def _is_heading(cleaned: str, sm: re.Match) -> bool:
    rest = cleaned[sm.end():sm.end() + 300]
    line = re.sub(r"\(\s*[\"']?MD&A[\"']?\s*\)", "", rest.split("\n", 1)[0])   # '... ("MD&A")' là tiêu đề thật
    return not _BAD_HEADING.search(line) and not _TOC_NEXT.match(rest)


def _try_tier_lines(start_pat: re.Pattern, cleaned: str) -> tuple[int, int] | None:
    best = None
    for sm in start_pat.finditer(cleaned):
        if not _is_heading(cleaned, sm):
            continue
        s = sm.start()
        for end_pat in _END_PATTERNS_LINE:
            em = end_pat.search(cleaned, s + 100)
            if not em:
                continue
            n = len(cleaned[s:em.start()].split())
            if MIN_MDNA_WORDS <= n <= MAX_MDNA_WORDS and (best is None or em.start() - s > best[1] - best[0]):
                best = (s, em.start())
            break                                   # chỉ dùng mốc kết thúc ưu tiên cao nhất tìm thấy
    return best


def _try_tier(start_pat: re.Pattern, cleaned: str) -> tuple[int, int] | None:
    """Try a start pattern, return (start_idx, end_idx) for the longest valid span, else None."""
    starts = list(start_pat.finditer(cleaned))
    if not starts:
        return None
    # Try start positions from LAST to first (TOC entries appear earliest).
    for sm in reversed(starts):
        s = sm.start()
        for end_pat in _END_PATTERNS:
            em = end_pat.search(cleaned, s + 100)
            if not em:
                continue
            mdna = cleaned[s:em.start()]
            n = len(mdna.split())
            if MIN_MDNA_WORDS <= n <= MAX_MDNA_WORDS:
                return s, em.start()
    return None


def extract_mdna(cleaned: str, form_type: str = "10-K") -> tuple[str | None, str]:
    """
    Extract the MD&A section from cleaned, uppercased text.

    Returns (mdna_text or None, status). status ∈ {
        'ok'         extraction succeeded (length within bounds),
        'no_match'   no tier matched,
    }.
    """
    is_ksb = "KSB" in form_type.upper()
    # Tier order: form-specific first, then Roman numeral, then bare.
    tiers: list[tuple[str, re.Pattern]] = []
    if is_ksb:
        tiers.append(("t1_ksb_item6", _T1_10KSB))
    else:
        tiers.append(("t1_10k_item7", _T1_10K))
    # Roman-numeral attempt for 10-KSBs that use VI. headings.
    if is_ksb:
        tiers.append(("t2_roman", _T2_ROMAN))
    tiers.append(("t3_bare", _T3_BARE))

    if not is_ksb:   # 10-K: bản đứng-đầu-dòng (xem _try_tier_lines); 10-KSB giữ nguyên logic gốc
        tiers = [("t1_10k_item7", _T1_10K_LINE), ("t3_bare", _T3_BARE_LINE)]
    for tier_name, pat in tiers:
        hit = (_try_tier(pat, cleaned) if is_ksb else _try_tier_lines(pat, cleaned))
        if hit is not None:
            s, e = hit
            return cleaned[s:e].strip(), f"ok_{tier_name}"

    return None, "no_match"


# --------------------------------------------------------------------------- #
# 3. Tokenization                                                              #
# --------------------------------------------------------------------------- #

# LM (2011) appendix: "two or more alphabetic characters. (Hyphens are also
# allowed in the character collections.)" — no apostrophes. So "MANAGEMENT'S"
# becomes "MANAGEMENT" + dropped "S", giving a dictionary hit.
TOKEN_RE = re.compile(r"\b[A-Z][A-Z\-]+\b")


def tokenize(text: str) -> list[str]:
    """LM-style tokenization: alphabetic tokens (length ≥ 2), hyphens allowed."""
    return TOKEN_RE.findall(text)


# --------------------------------------------------------------------------- #
# 4. BỔ SUNG CỦA NHÓM: HTML chính (submissions API) + Item 1A                 #
# --------------------------------------------------------------------------- #
INLINE_TAGS = re.compile(r"</?(?:span|font|b|i|u|strong|em|a|sup|sub|small|ix:[a-z]+)\b[^>]*>", re.IGNORECASE)
BLOCK_TAGS = re.compile(r"</?(?:p|div|br|tr|li|h[1-6]|table|td|th)\b[^>]*>", re.IGNORECASE)
STYLE_SCRIPT = re.compile(r"<(style|script|head)\b.*?</\1>", re.IGNORECASE | re.DOTALL)


def clean_primary_html(raw: str) -> str:
    """Làm sạch file HTML/iXBRL chính của 10-K theo cùng quy tắc LM.
    Nếu là file .txt đầy đủ (có <DOCUMENT>) thì dùng clean_text() gốc."""
    if re.search(r"<DOCUMENT>\s*<TYPE>", raw, re.IGNORECASE):
        # File HTML chính trước ~2020 được EDGAR bọc SGML (<DOCUMENT><TYPE>10-K...<TEXT>). Nếu phần thân là HTML thì
        # phải làm sạch theo đường HTML bên dưới – clean_text() thay mọi thẻ bằng khoảng trắng → cắt đôi từ và mất
        # xuống dòng (CHANGELOG_RUN.md #7). Chỉ file .txt thuần mới dùng clean_text().
        m = DOC10K_RE.search(raw)
        if not m or not re.search(r"<(?:html|body|div|p|font|table)\b", m.group("body"), re.IGNORECASE):
            return clean_text(raw)
        raw = m.group("body")
    body = STYLE_SCRIPT.sub(" ", raw)
    body = IX_HIDDEN_RE.sub(" ", body)
    body = html.unescape(body)
    body = TABLE_RE.sub(lambda m: " " if _table_is_numeric_heavy(m.group(0)) else m.group(0), body)
    body = INLINE_TAGS.sub("", body)          # không chèn khoảng trắng → không cắt đôi từ
    body = BLOCK_TAGS.sub("\n", body)
    body = HYPH_LF_RE.sub("-", body)
    body = TAG_RE.sub(" ", body)
    body = _normalize_unicode(body).upper()
    body = WS_RE.sub(" ", body)
    body = NL_RE.sub("\n\n", body)
    return body.strip()


_T1_1A = re.compile(r"ITEM\s*1\s*A[\.\s\-:\)]+(?:.{0,100}?)RISK\s+FACTORS", re.IGNORECASE | re.DOTALL)
_END_1A = re.compile(r"ITEM\s*1\s*B[\.\s\-:\)]|ITEM\s*1\s*C[\.\s\-:\)]|ITEM\s*2[\.\s\-:\)]+(?:.{0,50}?)PROPERTIES",
                     re.IGNORECASE | re.DOTALL)


def extract_item1a(cleaned: str) -> tuple[str | None, str]:
    """Item 1A – Risk Factors; cùng chiến lược 'duyệt từ cuối lên' để né mục lục."""
    for sm in reversed(list(_T1_1A.finditer(cleaned))):
        em = _END_1A.search(cleaned, sm.start() + 100)
        if em:
            seg = cleaned[sm.start():em.start()]
            if len(seg.split()) >= MIN_MDNA_WORDS:
                return seg.strip(), "ok"
    return None, "no_match"
