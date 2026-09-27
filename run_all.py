"""Chạy toàn bộ pipeline.
  python run_all.py --market us            # nhánh Mỹ
  python run_all.py --market vn            # nhánh Việt Nam
  python run_all.py --market both          # cả hai
  python run_all.py --market vn --from 5   # chạy lại từ bước 5 (dữ liệu đã tải được cache)
  python run_all.py --market us --only a03 # chạy một bước
"""
import sys, argparse, importlib, time
sys.path.insert(0, "src")
STEPS = {
    "us": ["us.u01_edgar", "us.u02_text", "us.u03_market", "analysis.a01_tone", "us.u04_validate_lm",
           "analysis.a02_event", "analysis.a03_regress", "analysis.a04_figures"],
    "vn": ["vn.v01_universe", "vn.v02_crawl_bctn", "vn.v03_extract_letter", "vn.v04_prices",
           "analysis.a01_tone", "analysis.a02_event", "analysis.a03_regress", "analysis.a04_figures"],
}


def run(mkt, start, end, only):
    for i, name in enumerate(STEPS[mkt], 1):
        if (only and only not in name) or (not only and not start <= i <= end):
            continue
        t = time.time(); print(f"\n===== [{mkt.upper()}] Bước {i}: {name} =====")
        mod = importlib.import_module(name)
        mod.main(mkt) if name.startswith("analysis.") else mod.main()
        print(f"({time.time() - t:.0f}s)")


if __name__ == "__main__":   # bắt buộc trên Windows vì một số bước dùng multiprocessing
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", choices=["us", "vn", "both"], default="both")
    ap.add_argument("--from", dest="start", type=int, default=1)
    ap.add_argument("--to", dest="end", type=int, default=99)
    ap.add_argument("--only", help="tên (một phần) module, vd a03")
    a = ap.parse_args()
    for m in (["us", "vn"] if a.market == "both" else [a.market]):
        run(m, a.start, a.end, a.only)
