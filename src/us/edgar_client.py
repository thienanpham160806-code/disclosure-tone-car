"""SEC EDGAR HTTP client: token-bucket rate limiter + retry (429/503/lỗi mạng) + User-Agent bắt buộc.

NGUỒN: chép và rút gọn từ m4a1ak471994/lm2011-replication – code/edgar_client.py (giấy phép MIT).
Thay đổi của nhóm: lấy email từ config.yaml thay vì biến môi trường; tự bỏ header Host để gọi
được cả data.sec.gov (API JSON) lẫn www.sec.gov (Archives).
"""
from __future__ import annotations
import threading, time
import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from common import CFG

EMAIL = CFG["contact_email"]
if "your_email" in EMAIL:
    raise SystemExit("Sửa contact_email trong config.yaml trước khi tải dữ liệu SEC (SEC yêu cầu User-Agent có email).")
HEADERS = {"User-Agent": f"UEL-DoAn05 research {EMAIL}", "Accept-Encoding": "gzip, deflate"}


class RateLimiter:
    """Token bucket: nạp lại `rps` token/giây, dung lượng = rps."""
    def __init__(self, rps: float):
        self.rate = self.capacity = self.tokens = rps
        self.last = time.monotonic(); self.lock = threading.Lock()

    def acquire(self):
        with self.lock:
            now = time.monotonic()
            self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate); self.last = now
            if self.tokens < 1.0:
                time.sleep((1.0 - self.tokens) / self.rate); self.tokens = 0.0; self.last = time.monotonic()
            else:
                self.tokens -= 1.0


class RetryableHTTPError(Exception):
    pass


SESSION = requests.Session(); SESSION.headers.update(HEADERS)
LIMITER = RateLimiter(float(CFG["us"]["max_rps"]))


@retry(reraise=True, stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=30),
       retry=retry_if_exception_type((RetryableHTTPError, requests.RequestException)))
def get(url: str, timeout: int = 60) -> requests.Response:
    LIMITER.acquire()
    r = SESSION.get(url, timeout=timeout)
    if r.status_code in (429, 503):
        ra = r.headers.get("Retry-After")
        if ra and ra.isdigit():
            time.sleep(min(30, int(ra)))
        raise RetryableHTTPError(f"{r.status_code} {url}")
    r.raise_for_status()
    return r
