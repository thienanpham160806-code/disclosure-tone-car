"""Đếm từ và chỉ số giọng điệu – dùng chung cho Mỹ và Việt Nam.

EnglishScorer : tách từ kiểu LM (textkit.us_clean.tokenize), mẫu số = số từ nằm trong LM master
                (đúng phụ lục LM 2011, theo lm2011-replication).
VietScorer    : khớp cụm dài nhất (greedy longest-match) trên chuỗi âm tiết, để "nợ xấu" không bị
                đếm thành "nợ"; từ tích cực đứng sau "không/chưa/chẳng" (≤3 âm tiết) không tính.
tfidf_scores  : trọng số tf-idf theo phương trình (1) của LM (2011):
                w_ij = (1+log tf_ij)/(1+log a_i) · log(N/df_j)
"""
from __future__ import annotations
import collections, math, re
from textkit.us_clean import tokenize
from common import norm_vi

NEG_VI = {"không", "chưa", "chẳng", "chả", "hề"}
NEG_EN = {"NO", "NOT", "NONE", "NEITHER", "NEVER", "NOBODY"}   # danh sách phủ định theo LM (2011)
TOK_VI = re.compile(r"[a-zà-ỹđ]+")


class EnglishScorer:
    def __init__(self, dic: dict[str, set], master: set | None = None):
        self.dic, self.master = dic, master

    def run(self, text: str):
        toks = tokenize(text.upper())
        tc = collections.Counter(toks)
        n = sum(v for w, v in tc.items() if w in self.master) if self.master else len(toks)
        cnt, words = collections.Counter(), {}
        for c, s in self.dic.items():
            words[c] = collections.Counter({w: v for w, v in tc.items() if w in s})
        if "positive" in self.dic:          # quy tắc phủ định LM: bỏ từ tích cực có NO/NOT... trong 3 từ trước
            for i, t in enumerate(toks):
                if t in self.dic["positive"] and NEG_EN & set(toks[max(0, i - 3):i]):
                    words["positive"][t] -= 1
            words["positive"] = +words["positive"]
        for c in words:
            cnt[c] = sum(words[c].values())
        return n, cnt, words


class VietScorer:
    def __init__(self, dic: dict[str, set]):
        self.map = collections.defaultdict(set)
        for c, terms in dic.items():
            for w in terms:
                self.map[tuple(w.split())].add(c)
        self.maxn = max(len(k) for k in self.map)

    def run(self, text: str):
        toks = TOK_VI.findall(norm_vi(text))
        n, i = len(toks), 0
        cnt, words = collections.Counter(), collections.defaultdict(collections.Counter)
        while i < n:
            for L in range(min(self.maxn, n - i), 0, -1):
                key = tuple(toks[i:i + L])
                if key in self.map:
                    cats = set(self.map[key])
                    if "positive" in cats and NEG_VI & set(toks[max(0, i - 3):i]):
                        cats.discard("positive")
                    for c in cats:
                        cnt[c] += 1; words[c][" ".join(key)] += 1
                    i += L; break
            else:
                i += 1
        return n, cnt, words


def indices(prefix: str, n: int, c) -> dict:
    pos, neg = c.get("positive", 0), c.get("negative", 0)
    n = max(n, 1)
    return {f"{prefix}_neg": neg / n, f"{prefix}_pos": pos / n,
            f"{prefix}_unc": c.get("uncertainty", 0) / n, f"{prefix}_lit": c.get("litigious", 0) / n,
            f"{prefix}_net": (pos - neg) / (pos + neg) if pos + neg else 0.0}


def tfidf_scores(word_counters: list[collections.Counter], doc_lens: list[int]) -> list[float]:
    """LM (2011) eq.(1). word_counters[i] = Counter các từ (của một nhóm, vd negative) trong văn bản i."""
    N = len(word_counters)
    df = collections.Counter(w for wc in word_counters for w in wc)
    out = []
    for wc, a in zip(word_counters, doc_lens):
        if a <= 0:
            out.append(float("nan")); continue
        out.append(sum((1 + math.log(tf)) / (1 + math.log(a)) * math.log(N / df[w]) for w, tf in wc.items()))
    return out
