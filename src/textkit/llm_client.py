"""Tầng AI cho trích văn bản (v03 --llm): Gemini (mặc định) + Claude (dự phòng), cùng một giao diện.

Nguyên tắc phương pháp (bắt buộc – đề tài đo GIỌNG ĐIỆU, LLM viết lại sẽ làm nhiễm biến đo):
  • LLM chỉ CHÉP NGUYÊN VĂN (vision) hoặc CHỈ SỬA LỖI NHẬN DẠNG KÝ TỰ/DẤU (text_fix); không diễn đạt lại, không sửa
    chính tả của bản gốc, không tóm tắt, không thêm/bớt câu. temperature = 0. Prompt nêu rõ các điều này.
  • Chỉ gửi ẢNH/TEXT CỦA TỪNG TRANG cần sửa, không bao giờ gửi cả PDF.
  • Mọi phản hồi được cache ở data/vn/interim/llm_cache/<sha256(model+loại+prompt+text+ảnh)>.json → chạy lại không
    tốn lượt gọi, kết quả tái lập được.
  • Giới hạn: max_total_calls (lượt gọi thật, không tính cache) và requests_per_minute (gói miễn phí Gemini).
  • API key: biến môi trường GEMINI_API_KEY / ANTHROPIC_API_KEY hoặc file .env (không commit).
Model: tên model đặt trong config.yaml (vn.extract.llm.model_gemini / model_claude) – không hard-code.
Claude: dùng model nhận temperature (Claude Haiku 4.5); các model Claude đời mới (Opus 5, Sonnet 5) đã bỏ tham số
temperature (API trả 400) nên không đáp ứng được yêu cầu temperature = 0.
"""
from __future__ import annotations
import base64, collections, hashlib, json, os, re, time, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

TRANSCRIBE_SCHEMA = {
    "type": "object",
    "properties": {"page_text": {"type": "string"}, "is_chairman_letter": {"type": "boolean"},
                   "confidence": {"type": "number"}},
    "required": ["page_text", "is_chairman_letter", "confidence"],
}
LOCATE_SCHEMA = {"type": "object", "properties": {"start": {"type": ["integer", "null"]}, "end": {"type": ["integer", "null"]}},
                 "required": ["start", "end"]}
TONE_SCHEMA = {"type": "object", "properties": {"tone": {"type": "number"}, "uncertainty": {"type": "number"},
                                                  "rationale": {"type": "string"}},
               "required": ["tone", "uncertainty", "rationale"]}

_RULES = (
    "QUY TẮC BẮT BUỘC (văn bản dùng để đo giọng điệu trong một nghiên cứu khoa học):\n"
    "- Chép NGUYÊN VĂN, đúng từng chữ như trong ảnh. KHÔNG diễn đạt lại, KHÔNG sửa lỗi chính tả hay ngữ pháp của bản gốc, "
    "KHÔNG tóm tắt, KHÔNG thêm hoặc bớt câu, KHÔNG dịch, KHÔNG thêm lời bình.\n"
    "- Chữ không đọc được thì ghi [?] thay cho chữ đó, không đoán.\n")
PROMPT_VISION = (
    "Bạn là công cụ nhận dạng chữ (OCR) cho trang báo cáo thường niên tiếng Việt trong ảnh.\n" + _RULES +
    "- Chép phần chữ của trang theo thứ tự đọc tự nhiên (tiêu đề trước thân bài; hết cột trái rồi sang cột phải).\n"
    "- Bỏ: tiêu đề/chân trang lặp lại (tên công ty, 'Báo cáo thường niên 20xx'), số trang, chú thích ảnh, chữ trong "
    "biểu đồ và bảng số.\n"
    "- is_chairman_letter = true nếu trang thuộc thư/thông điệp của lãnh đạo (Chủ tịch HĐQT, Tổng Giám đốc, Ban lãnh đạo) "
    "gửi cổ đông. confidence ∈ [0,1] là mức chắc chắn về độ chính xác của bản chép.\n"
    'Chỉ trả về JSON: {"page_text": "...", "is_chairman_letter": true/false, "confidence": số}.')
PROMPT_FIX = (
    "Dưới đây là văn bản OCR (Tesseract) của trang báo cáo thường niên tiếng Việt trong ảnh đính kèm.\n" + _RULES +
    "- NHIỆM VỤ DUY NHẤT: sửa lỗi NHẬN DẠNG KÝ TỰ và DẤU tiếng Việt do OCR gây ra (vd 'hội đòng' → 'hội đồng', "
    "'cô đông' → 'cổ đông') khi ảnh cho thấy rõ chữ đúng. GIỮ NGUYÊN từ ngữ, thứ tự từ, thứ tự câu, xuống dòng và dấu câu "
    "của văn bản OCR; không xóa hoặc thêm đoạn nào.\n"
    "- is_chairman_letter như định nghĩa: trang thuộc thư/thông điệp của lãnh đạo gửi cổ đông. confidence ∈ [0,1].\n"
    'Chỉ trả về JSON: {"page_text": "...", "is_chairman_letter": true/false, "confidence": số}.\n\nVĂN BẢN OCR:\n')
PROMPT_LOCATE = (
    "Đây là khoảng 300 ký tự đầu của từng trang trong một báo cáo thường niên tiếng Việt. Trang nào BẮT ĐẦU và KẾT THÚC "
    "thông điệp/thư của lãnh đạo gửi cổ đông (ưu tiên thư của Chủ tịch HĐQT; nếu không có thì thư chung Chủ tịch + TGĐ, "
    "'Thông điệp Ban lãnh đạo' hoặc thư của TGĐ)? Không tính trang mục lục. "
    'Chỉ trả về JSON {"start": số trang, "end": số trang}, hoặc {"start": null, "end": null} nếu không có.\n\n')
PROMPT_TONE = (
    "Bạn là chuyên gia phân tích tài chính. Đọc thông điệp của lãnh đạo doanh nghiệp niêm yết Việt Nam gửi cổ đông dưới "
    "đây và chấm: tone ∈ [-1, 1] = giọng điệu về tình hình và triển vọng TÀI CHÍNH – KINH DOANH của công ty (-1 rất tiêu "
    "cực, 0 trung tính, +1 rất tích cực; bỏ qua lời chào, cảm ơn, khẩu hiệu mang tính nghi thức); uncertainty ∈ [0, 1] = mức "
    "độ bất định/rủi ro được nhấn mạnh trong thư. rationale: tối đa 2 câu tiếng Việt.\n"
    'Chỉ trả về JSON {"tone": số, "uncertainty": số, "rationale": "..."}.\n\nTHÔNG ĐIỆP:\n')


class RetryableError(Exception):
    """Lỗi tạm thời (429, 5xx, mạng) – được thử lại có backoff."""


class BudgetExceeded(Exception):
    pass


class LLMError(Exception):
    pass


def parse_json(raw: str) -> dict:
    s = (raw or "").strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", s, re.S)
        if not m:
            raise
        return json.loads(m.group())


def _load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass


def gemini_backend():
    """Backend Gemini (SDK chính thức google-genai). Trả hàm (model, prompt, image, schema, max_tokens) → (text, usage)."""
    from google import genai
    from google.genai import types, errors
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def call(model, prompt, image, schema, max_tokens):
        parts = ([types.Part.from_bytes(data=image, mime_type="image/png")] if image else []) + [prompt]
        cfg = types.GenerateContentConfig(
            temperature=0, max_output_tokens=max_tokens, response_mime_type="application/json",
            response_json_schema=schema, automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
        try:
            r = client.models.generate_content(model=model, contents=parts, config=cfg)
        except errors.APIError as e:
            if e.code == 429 or (e.code or 0) >= 500:
                raise RetryableError(f"gemini {e.code}: {str(e)[:200]}") from e
            raise
        except Exception as e:          # lỗi mạng
            if "timed out" in str(e).lower() or "connection" in str(e).lower():
                raise RetryableError(str(e)[:200]) from e
            raise
        cand = r.candidates[0] if r.candidates else None
        fr = getattr(getattr(cand, "finish_reason", None), "name", None)
        if fr and fr not in ("STOP", "FINISH_REASON_UNSPECIFIED"):
            # RECITATION: Gemini chặn chép nguyên văn nội dung trùng tài liệu công khai; SAFETY/MAX_TOKENS... → không thử lại
            raise LLMError(f"gemini finish_reason={fr}")
        u = r.usage_metadata
        return r.text, {"input_tokens": getattr(u, "prompt_token_count", None),
                        "output_tokens": getattr(u, "candidates_token_count", None)}
    return call


def claude_backend():
    """Backend Claude (SDK chính thức anthropic). Tự retry của SDK tắt – retry do LLMClient quản lý."""
    import anthropic
    client = anthropic.Anthropic(max_retries=0)

    def call(model, prompt, image, schema, max_tokens):
        content = ([{"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                  "data": base64.standard_b64encode(image).decode()}}] if image else [])
        content.append({"type": "text", "text": prompt})
        try:
            r = client.messages.create(model=model, max_tokens=max_tokens, temperature=0,
                                       messages=[{"role": "user", "content": content}])
        except anthropic.RateLimitError as e:
            raise RetryableError(f"claude 429: {e}") from e
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                raise RetryableError(f"claude {e.status_code}") from e
            raise
        except anthropic.APIConnectionError as e:
            raise RetryableError(f"claude connection: {e}") from e
        if r.stop_reason == "refusal":
            raise LLMError("claude refusal")
        text = "".join(b.text for b in r.content if b.type == "text")
        return text, {"input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens}
    return call


BACKENDS = {"gemini": (gemini_backend, "GEMINI_API_KEY"), "claude": (claude_backend, "ANTHROPIC_API_KEY")}


class LLMClient:
    def __init__(self, cfg: dict, cache_dir: Path | None = None, backends: dict | None = None, sleep=time.sleep,
                 clock=time.monotonic):
        _load_env()
        self.cfg = cfg
        self.cache_dir = Path(cache_dir or ROOT / "data" / "vn" / "interim" / "llm_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._injected = backends or {}
        self._built = {}
        self.sleep, self.clock = sleep, clock
        self.calls = 0                      # lượt gọi API thật
        self.cache_hits = 0
        self.fail_streak = collections.Counter()
        self.usage = collections.Counter()  # token theo provider
        self._last_call = -1e9

    # ---------- chọn provider ----------
    def available(self, provider: str) -> bool:
        if provider in self._injected:
            return True
        return provider in BACKENDS and bool(os.getenv(BACKENDS[provider][1]))

    def providers(self) -> list[str]:
        order = [self.cfg.get("provider", "gemini"), self.cfg.get("fallback_provider")]
        order = [p for p in dict.fromkeys(order) if p and self.available(p)]
        # provider lỗi liên tục ≥ max_consecutive_failures → chuyển xuống cuối (dùng provider còn lại trước)
        k = self.cfg.get("max_consecutive_failures", 3)
        return sorted(order, key=lambda p: self.fail_streak[p] >= k)

    def _backend(self, provider):
        if provider in self._injected:
            return self._injected[provider]
        if provider not in self._built:
            self._built[provider] = BACKENDS[provider][0]()
        return self._built[provider]

    # ---------- lõi: cache + budget + rate limit + retry + fallback ----------
    def _key(self, model, kind, prompt, image):
        h = hashlib.sha256()
        for part in (model, kind, prompt):
            h.update(part.encode("utf-8")); h.update(b"\x00")
        h.update(image or b"")
        return h.hexdigest()

    def _pace(self):
        gap = 60.0 / max(self.cfg.get("requests_per_minute", 10), 1e-9)
        wait = self._last_call + gap - self.clock()
        if wait > 0:
            self.sleep(wait)
        self._last_call = self.clock()

    def _with_retry(self, fn, *args):
        tries = self.cfg.get("max_retries", 4)
        for i in range(tries):
            try:
                self._pace()
                return fn(*args)
            except RetryableError:
                if i == tries - 1:
                    raise
                self.sleep(min(60, 2 ** (i + 1)))

    def request(self, kind: str, prompt: str, image: bytes | None, schema: dict, max_tokens: int = 8192) -> dict:
        """Gọi LLM (có cache). kind: 'vision' | 'text_fix' | 'locate' | 'tone'. Trả dict JSON + provider/model/cached."""
        last = None
        for prov in self.providers():
            model = self.cfg[f"model_{prov}"]
            f = self.cache_dir / f"{self._key(model, kind, prompt, image)}.json"
            if f.exists():
                self.cache_hits += 1
                return {**json.loads(f.read_text(encoding="utf-8")), "cached": True}
            if self.calls >= self.cfg.get("max_total_calls", 0):
                raise BudgetExceeded(f"đã dùng hết max_total_calls = {self.cfg.get('max_total_calls')}")
            try:
                self.calls += 1
                raw, usage = self._with_retry(self._backend(prov), model, prompt, image, schema, max_tokens)
                out = parse_json(raw)
            except BudgetExceeded:
                raise
            except Exception as e:
                self.fail_streak[prov] += 1; last = e
                continue
            self.fail_streak[prov] = 0
            for k, v in (usage or {}).items():
                self.usage[f"{prov}_{k}"] += v or 0
            out = {**out, "provider": prov, "model": model, "usage": usage}
            f.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
            return {**out, "cached": False}
        raise LLMError(f"mọi provider đều lỗi hoặc không có API key: {last}")

    # ---------- API dùng trong pipeline ----------
    def transcribe_page(self, image_bytes: bytes, ocr_text: str = "", mode: str = "vision") -> dict:
        if mode == "vision":
            out = self.request("vision", PROMPT_VISION, image_bytes, TRANSCRIBE_SCHEMA)
        elif mode == "text_fix":
            out = self.request("text_fix", PROMPT_FIX + (ocr_text or ""), image_bytes, TRANSCRIBE_SCHEMA)
        else:
            raise ValueError(mode)
        out["page_text"] = unicodedata.normalize("NFC", out.get("page_text") or "")
        return out

    def locate(self, snippet: str) -> dict:
        return self.request("locate", PROMPT_LOCATE + snippet, None, LOCATE_SCHEMA, max_tokens=200)

    def rate_tone(self, text: str) -> dict:
        return self.request("tone", PROMPT_TONE + text, None, TONE_SCHEMA, max_tokens=600)


def decide(mode: str, ocr_text: str, llm_text: str, q_before: float, q_after: float, cfg: dict) -> tuple[bool, str]:
    """Có dùng bản của LLM thay bản OCR/lớp chữ không? Trả (dùng?, lý do).
    text_fix: độ tương đồng ký tự với bản OCR phải ≥ similarity_min, ngược lại coi là LLM 'viết lại' → loại, gắn cờ.
    Cả hai chế độ: chỉ dùng khi chất lượng sau ≥ chất lượng trước (không làm tệ đi)."""
    if not (llm_text or "").strip():
        return False, "llm_empty"
    if mode == "text_fix":
        sim = similarity(ocr_text, llm_text)
        if sim < cfg.get("similarity_min", 0.8):
            return False, f"rewrite_suspected(sim={sim:.2f})"
    if q_after < q_before:
        return False, f"quality_not_improved({q_before:.2f}->{q_after:.2f})"
    return True, "accepted"


def similarity(a: str, b: str) -> float:
    """Độ tương đồng ký tự 0..1 (rapidfuzz, không phân biệt hoa thường, gộp khoảng trắng)."""
    from rapidfuzz import fuzz
    n = lambda s: re.sub(r"\s+", " ", unicodedata.normalize("NFC", s or "").lower()).strip()
    return fuzz.ratio(n(a), n(b)) / 100
