"""Kiểm thử tầng AI bằng backend giả (mock) – KHÔNG gọi API thật."""
import sys, pathlib, json
import pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from textkit.llm_client import (LLMClient, RetryableError, BudgetExceeded, LLMError, decide, parse_json, similarity,
                                PROMPT_VISION, PROMPT_FIX)

CFG = {"provider": "gemini", "fallback_provider": "claude", "model_gemini": "g-test", "model_claude": "c-test",
       "requests_per_minute": 6000, "max_total_calls": 10, "max_retries": 2, "max_consecutive_failures": 2,
       "similarity_min": 0.8}


class Fake:
    def __init__(self, text="Kính thưa Quý cổ đông", fail=0, exc=RetryableError):
        self.calls, self.fail, self.text, self.exc = [], fail, text, exc

    def __call__(self, model, prompt, image, schema, max_tokens):
        self.calls.append((model, prompt[:30], bool(image)))
        if len(self.calls) <= self.fail:
            raise self.exc("tạm thời")
        return json.dumps({"page_text": self.text, "is_chairman_letter": True, "confidence": 0.9}), {"input_tokens": 10, "output_tokens": 5}


def client(tmp_path, **backends):
    return LLMClient(CFG, cache_dir=tmp_path, backends=backends, sleep=lambda s: None)


def test_prompts_demand_verbatim():
    for p in (PROMPT_VISION, PROMPT_FIX):
        assert "NGUYÊN VĂN" in p and "KHÔNG diễn đạt lại" in p and "KHÔNG tóm tắt" in p


def test_cache_avoids_second_call(tmp_path):
    g = Fake(); c = client(tmp_path, gemini=g)
    a = c.transcribe_page(b"img", mode="vision"); b = c.transcribe_page(b"img", mode="vision")
    assert len(g.calls) == 1 and c.calls == 1 and c.cache_hits == 1
    assert a["page_text"] == b["page_text"] and a["provider"] == "gemini" and a["model"] == "g-test" and b["cached"]
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_retry_then_success(tmp_path):
    g = Fake(fail=1); c = client(tmp_path, gemini=g)
    out = c.transcribe_page(b"img")
    assert len(g.calls) == 2 and out["provider"] == "gemini"


def test_fallback_to_claude_when_gemini_keeps_failing(tmp_path):
    g, cl = Fake(fail=99), Fake(text="bản Claude"); c = client(tmp_path, gemini=g, claude=cl)
    out = c.transcribe_page(b"img1")
    assert out["provider"] == "claude" and out["model"] == "c-test" and out["page_text"] == "bản Claude"
    c.transcribe_page(b"img2")                          # gemini lỗi liên tục → Claude được thử trước
    assert c.providers()[0] == "claude"


def test_budget_limit(tmp_path):
    c = LLMClient({**CFG, "max_total_calls": 1}, cache_dir=tmp_path, backends={"gemini": Fake()}, sleep=lambda s: None)
    c.transcribe_page(b"a")
    with pytest.raises(BudgetExceeded):
        c.transcribe_page(b"b")


def test_no_provider_raises(tmp_path):
    c = LLMClient({**CFG, "provider": "none", "fallback_provider": None}, cache_dir=tmp_path, backends={}, sleep=lambda s: None)
    with pytest.raises(LLMError):
        c.transcribe_page(b"a")


def test_decide_rejects_rewrite_and_regression():
    ocr = "Kính thưa Quý cô đông, năm 2023 là một năm đầy thách thúc đối với nền kinh tế."
    fixed = "Kính thưa Quý cổ đông, năm 2023 là một năm đầy thách thức đối với nền kinh tế."
    rewritten = "Thưa các cổ đông, 2023 là năm khó khăn cho kinh tế toàn cầu và công ty đã vượt qua."
    assert similarity(ocr, fixed) > 0.9
    assert decide("text_fix", ocr, fixed, 0.8, 0.95, CFG) == (True, "accepted")
    ok, why = decide("text_fix", ocr, rewritten, 0.8, 0.95, CFG)
    assert not ok and why.startswith("rewrite_suspected")
    assert decide("vision", ocr, fixed, 0.9, 0.7, CFG)[0] is False


def test_parse_json_with_fences():
    assert parse_json('```json\n{"start": 3, "end": 4}\n```') == {"start": 3, "end": 4}
