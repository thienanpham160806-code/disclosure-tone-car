"""A7 (TÙY CHỌN, ĐỐI CHỨNG). Thước đo giọng điệu bằng LLM cho thông điệp lãnh đạo (VN).

LLM (Gemini mặc định / Claude dự phòng – cấu hình vn.extract.llm) đọc TOÀN VĂN thông điệp và chấm:
  llm_tone        ∈ [-1, 1]: giọng điệu về tình hình & triển vọng tài chính – kinh doanh (bỏ qua lời chào, nghi thức)
  llm_uncertainty ∈ [0, 1] : mức độ bất định / rủi ro được nhấn mạnh
temperature = 0, JSON, mọi phản hồi cache ở data/vn/interim/llm_cache/ (chạy lại không tốn lượt gọi).
Kết quả: data/vn/processed/llm_tone.csv → a03_regress.py tự thêm mô hình M9 (như finbert.csv → M8).
LƯU Ý PHƯƠNG PHÁP: thước đo này KÉM MINH BẠCH hơn từ điển (không biết từ nào dẫn tới điểm; phụ thuộc phiên bản model;
có thể nhạy với cách viết prompt) → chỉ dùng làm biến ĐỐI CHỨNG (robustness) bên cạnh fin_neg / fin_net, không thay thế.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import argparse
import pandas as pd
from tqdm import tqdm
from common import CFG, D


def main(mkt="vn", max_words=6000):
    from textkit.llm_client import LLMClient, BudgetExceeded
    L = CFG["vn"]["extract"]["llm"]
    client = LLMClient(L)
    if not client.providers():
        print("Bỏ qua: không có GEMINI_API_KEY / ANTHROPIC_API_KEY"); return
    docs = pd.read_csv(D(mkt, "processed", "docs.csv"))
    docs = docs[docs.flag.eq("ok")]
    rows = []
    for r in tqdm(list(docs.itertuples()), desc="LLM tone"):
        text = (D(mkt, "interim", "text", r.text_main)).read_text(encoding="utf-8")
        text = " ".join(text.split()[:max_words])
        try:
            out = client.rate_tone(text)
        except BudgetExceeded as e:
            print(f"  ! dừng: {e}"); break
        except Exception as e:
            print(f"  ! {r.doc_id}: {str(e)[:150]}"); continue
        clip = lambda v, lo, hi: max(lo, min(hi, float(v)))
        rows.append(dict(doc_id=r.doc_id, llm_tone=clip(out["tone"], -1, 1), llm_uncertainty=clip(out["uncertainty"], 0, 1),
                         llm_rationale=out.get("rationale"), llm_provider=out.get("provider"), llm_model=out.get("model")))
    t = pd.DataFrame(rows)
    t.to_csv(D(mkt, "processed", "llm_tone.csv"), index=False, encoding="utf-8-sig")
    tone = pd.read_csv(D(mkt, "processed", "tone_panel.csv")).merge(t, on="doc_id")
    print(f"{len(t)} văn bản | lượt gọi thật {client.calls}, cache {client.cache_hits} | token {dict(client.usage)}")
    print(tone[["llm_tone", "llm_uncertainty", "fin_net", "fin_neg", "fin_unc"]].corr().round(3).to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--market", default="vn", choices=["vn"])
    main(ap.parse_args().market)
