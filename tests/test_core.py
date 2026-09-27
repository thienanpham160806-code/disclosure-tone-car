"""Kiểm thử nhanh các khối lõi – chạy: pytest -q   (không cần Internet, không cần dữ liệu thật)."""
import math, sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from textkit import us_clean as ux
from textkit.scoring import EnglishScorer, VietScorer, tfidf_scores, indices
from common import K


def test_span_split_word_is_rejoined():
    assert "BUSINESS" in ux.clean_primary_html("<p><span>B</span><span>USINESS</span> overview</p>")


def test_numeric_table_removed_text_table_kept():
    h = "<table><tr><td>1,234</td><td>9,876</td></tr></table><table><tr><td>Risk overview text</td></tr></table>"
    c = ux.clean_primary_html(h)
    assert "1,234" not in c and "RISK OVERVIEW TEXT" in c


def test_mdna_skips_table_of_contents():
    body = "REVENUE DECLINED. " * 300
    text = ("ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS 25\nITEM 8. FINANCIAL STATEMENTS 40\n"
            f"ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS\n{body}\nITEM 7A. QUANTITATIVE")
    m, st = ux.extract_mdna(text)
    assert st.startswith("ok") and m.count("REVENUE") == 300


def test_lm_negation_rule():
    sc = EnglishScorer({"positive": {"GOOD"}, "negative": {"LOSS"}})
    _, c, _ = sc.run("This was not a good year. Later results in the fourth quarter were good. A loss.")
    assert c["positive"] == 1 and c["negative"] == 1


def test_viet_longest_match():
    sc = VietScorer({"negative": {"nợ xấu"}, "positive": {"tăng trưởng"}, "uncertainty": set(), "litigious": set()})
    gen = VietScorer({"negative": {"nợ"}, "positive": set()})
    _, c, _ = sc.run("Nợ xấu tăng nhưng doanh thu tăng trưởng; công ty không tăng trưởng mảng khác. Nợ phải trả ổn định.")
    assert c["negative"] == 1 and c["positive"] == 1           # phủ định bỏ 1 lần "tăng trưởng"
    _, g, _ = gen.run("Nợ xấu. Nợ phải trả.")
    assert g["negative"] == 2                                   # từ điển tổng quát đếm cả "nợ phải trả" → nhiễu


def test_tfidf_matches_lm_equation():
    docs = [collections.Counter({"LOSS": 2}), collections.Counter({"LOSS": 1, "DECLINE": 1})]
    s = tfidf_scores(docs, [100, 50])
    assert math.isclose(s[0], 0.0) and math.isclose(s[1], (1 + math.log(1)) / (1 + math.log(50)) * math.log(2))


def test_indices_and_column_names():
    x = indices("fin", 100, {"positive": 3, "negative": 1})
    assert math.isclose(x["fin_net"], 0.5) and K("car", -1, 1) == "car_m1_1"
