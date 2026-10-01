"""Chuẩn bị từ điển cho máy chủ dashboard (chạy ở bước build trên Render; chạy tay trên máy nào cũng được).

  • VietSentiWordNet 1.3.5  – tải từ GitHub (giống pipeline).
  • Harvard GI IV-4         – có sẵn trong gói pysentiment2 (requirements.txt), không cần tải.
  • Loughran–McDonald       – giấy phép không cho phân phối lại nên KHÔNG có trong git. Đặt biến môi trường
                              LM_DICT_URL = đường dẫn tải file Loughran-McDonald_MasterDictionary_*.csv
                              (vd link chia sẻ Google Drive của chính bạn: drive.google.com/file/d/<ID>/view).
                              Thiếu → dashboard vẫn chạy, chỉ phần chấm tone tiếng Anh báo thiếu từ điển.
Không bao giờ làm hỏng bước build: lỗi chỉ in cảnh báo.
"""
import os, pathlib, re, sys

import requests

ROOT = pathlib.Path(__file__).resolve().parents[2]
DICT = ROOT / "dict"
DICT.mkdir(exist_ok=True)
VSWN_URL = ("https://raw.githubusercontent.com/sonvx/VietSentiWordNet/master/"
            "VietSentiWordNet/dicts/VietSentiWordnet_Ver1.3.5.txt")


def direct(url: str) -> str:
    """Link chia sẻ Google Drive → link tải trực tiếp; link khác giữ nguyên."""
    m = re.search(r"drive\.google\.com/(?:file/d/|open\?id=|uc\?(?:export=download&)?id=)([\w-]+)", url)
    return f"https://drive.usercontent.google.com/download?id={m.group(1)}&export=download&confirm=t" if m else url


def fetch(url: str, dest: pathlib.Path, must_start: str | None = None) -> bool:
    try:
        r = requests.get(direct(url), timeout=180)
        r.raise_for_status()
        head = r.content[:200].decode("utf-8", "ignore").lstrip("﻿")
        if must_start and not head.startswith(must_start):
            print(f"  ! {dest.name}: nội dung tải về không phải file mong đợi (bắt đầu bằng {head[:60]!r})")
            return False
        dest.write_bytes(r.content)
        print(f"  ✓ {dest.name} ({len(r.content) / 1e6:.1f} MB)")
        return True
    except Exception as e:
        print(f"  ! không tải được {dest.name}: {e}")
        return False


def main():
    print("Chuẩn bị từ điển cho dashboard:")
    v = DICT / "VietSentiWordnet_Ver1.3.5.txt"
    if v.exists():
        print(f"  ✓ {v.name} (đã có)")
    else:
        fetch(VSWN_URL, v)

    have_lm = sorted(DICT.glob("Loughran*MasterDictionary*.csv"))
    url = os.getenv("LM_DICT_URL", "").strip()
    if have_lm:
        print(f"  ✓ {have_lm[-1].name} (đã có)")
    elif url:
        fetch(url, DICT / "Loughran-McDonald_MasterDictionary_1993-2025.csv", must_start="Word,")
    else:
        print("  · Chưa có từ điển LM và chưa đặt LM_DICT_URL → phần chấm tone tiếng Anh sẽ báo thiếu từ điển.")

    try:
        import pysentiment2  # noqa: F401
        print("  ✓ Harvard GI (gói pysentiment2)")
    except ImportError:
        print("  ! thiếu gói pysentiment2 (Harvard GI) – kiểm tra requirements.txt")


if __name__ == "__main__":
    main()
    sys.exit(0)
