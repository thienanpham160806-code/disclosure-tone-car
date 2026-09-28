"""Kiểm thử chấm chất lượng văn bản OCR (không cần Internet, không cần dữ liệu thật)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from textkit.ocr_quality import quality_score, quality_detail, is_vietnamese_syllable

CLEAN = ("Kính thưa Quý cổ đông, năm 2023 là một năm đầy thách thức đối với nền kinh tế thế giới và Việt Nam. "
         "Tuy nhiên, với sự nỗ lực không ngừng của toàn thể cán bộ nhân viên, Công ty đã hoàn thành vượt kế hoạch "
         "lợi nhuận, doanh thu tăng trưởng 12% so với cùng kỳ. Thay mặt Hội đồng quản trị, tôi xin chân thành cảm ơn.")
# lỗi font TCVN3 (chữ Việt mã hóa sang Latin-1)
TCVN3 = ("KÝnh th­a Quý cæ ®«ng, n¨m 2023 lµ mét n¨m ®Çy th¸ch thøc ®èi víi nÒn kinh tÕ thÕ giíi vµ ViÖt Nam. "
         "Tuy nhiªn, víi sù nç lùc kh«ng ngõng cña toµn thÓ c¸n bé nh©n viªn, C«ng ty ®· hoµn thµnh v­ît kÕ ho¹ch "
         "lîi nhuËn, doanh thu t¨ng tr­ëng 12% so víi cïng kú. Thay mÆt Héi ®ång qu¶n trÞ, t«i xin ch©n thµnh c¶m ¬n.")
# font nhúng mã hóa sai (kiểu VIC 2025) + OCR vỡ
BROKEN = ("Thông ,i6p c:a T#ng Giám ,%c M+t trong nh(ng d8u 8n n#i b8t là d( án t3i n1m 2025 v!@n minh bat pha "
          "c)c ch; tieu kinh doanh co b)n giai ,o3n 7*a ban kinh doanh h6 sinh thai t/ong m3i d*ch vu h6 th%ng c1n h+, "
          "l'nh v(c kinh d gi!i thi\"u t-ng quan h+i ,-ng qu)n tr* cac dau m%c phat tri&n")
OCR_NOISE = ("=| IMMDOVAST O se 02 CÔMG TỶ GỖ PHẨM vĩM mướ* n cán thLl3rg L L L U L L E EU U ï Ù EE EU ï Ù E E U š Ù E E Ù Ù "
             "L EE EU Ù Ù E E Ừ U Ù E E L š ¬fi=, ilk=s: emaeii e tuomg u eecw5 eh miekhti hlr3r ii |sox: chu l x ii; b' se")


def test_syllable_structure():
    assert is_vietnamese_syllable("nghiêng") and is_vietnamese_syllable("Quý") and is_vietnamese_syllable("trưởng")
    assert not is_vietnamese_syllable("th­a") and not is_vietnamese_syllable("n¨m") and not is_vietnamese_syllable("xyz")


def test_clean_text_scores_high():
    assert quality_score(CLEAN, lexicon=set()) >= 0.9


def test_font_and_ocr_garbage_score_low():
    for bad in (TCVN3, BROKEN, OCR_NOISE):
        assert quality_score(bad, lexicon=set()) < 0.75, quality_detail(bad, lexicon=set())
    assert quality_score(CLEAN, lexicon=set()) - quality_score(TCVN3, lexicon=set()) > 0.25


def test_short_text_is_zero():
    assert quality_score("Trang 5", lexicon=set()) == 0.0
