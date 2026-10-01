"""Kiểm thử thứ tự đọc (v03.reading_order, CHANGELOG_RUN #65) và việc bỏ khối XBRL (us_clean, #64)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from textkit import us_clean as ux


def _ro():
    # import muộn: v03 nạp fitz/pytesseract – có trong requirements của pipeline
    from vn.v03_extract_letter import reading_order
    return reading_order


def blk(x0, y0, x1, y1, text):
    return (x0, y0, x1, y1, text, 0, 0)          # định dạng khối của PyMuPDF get_text("blocks")


def test_two_columns_read_column_by_column():
    """Hai cột có dòng ngang hàng nhau + tiêu đề và một đoạn trải ngang hai cột (đúng ca từng gây xen dòng)."""
    blocks = [blk(100, 20, 400, 40, "TIÊU ĐỀ"), blk(60, 60, 470, 75, "đoạn mở đầu trải hai cột")]
    for i in range(4):
        y = 120 + 16 * i
        blocks += [blk(50, y, 250, y + 12, f"trái {i}"), blk(300, y, 500, y + 12, f"phải {i}")]
    order = [b[4] for b in _ro()(blocks)]
    assert order == ["TIÊU ĐỀ", "đoạn mở đầu trải hai cột"] + [f"trái {i}" for i in range(4)] + [f"phải {i}" for i in range(4)]


def test_single_column_keeps_top_to_bottom():
    blocks = [blk(50, 100 + 20 * i, 500, 112 + 20 * i, f"dòng {i}") for i in (3, 0, 2, 1)]
    assert [b[4] for b in _ro()(blocks)] == [f"dòng {i}" for i in range(4)]


def test_image_blocks_ignored():
    blocks = [blk(50, 50, 500, 60, "chữ"), (50, 70, 500, 300, "<image>", 1, 1)]
    assert [b[4] for b in _ro()(blocks)] == ["chữ"]


def test_ix_header_removed():
    h = ("<html><body><div style='display:none'><ix:header><ix:hidden>x</ix:hidden><ix:resources>"
         "<xbrli:context id='c1'><xbrli:identifier>0001403161</xbrli:identifier>V:LAWSUIT 2024-09-30</xbrli:context>"
         "</ix:resources></ix:header></div><p>Annual report text</p></body></html>")
    c = ux.clean_primary_html(h)
    assert "LAWSUIT" not in c and "0001403161" not in c and "ANNUAL REPORT TEXT" in c
