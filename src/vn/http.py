"""HTTP lịch sự cho nguồn Việt Nam (CafeF): nghỉ giữa request, thử lại, Referer."""
import time, requests
from common import CFG


def session():
    s = requests.Session()
    s.headers.update({"User-Agent": f"Mozilla/5.0 (UEL student research; {CFG['contact_email']})",
                      "Referer": "https://cafef.vn/"})
    return s


def polite_get(s, url, retries=3, **kw):
    for i in range(retries):
        try:
            r = s.get(url, timeout=60, **kw)
            time.sleep(CFG["vn"]["sleep"])
            if r.status_code == 200:
                return r
            if r.status_code == 404:          # không tồn tại → không thử lại (đỡ tải cho máy chủ)
                return None
        except requests.RequestException:
            pass
        time.sleep(2 * (i + 1))
    return None
