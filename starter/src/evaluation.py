"""Chấm Evidence Hit@1/Hit@3 tự động và lưu trace. Không suy ra nhãn coherence/grounding."""
import re
import unicodedata
from collections import defaultdict
from typing import Any


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip()


def is_hit(question: dict[str, Any], hit: dict[str, Any]) -> bool:
    """Hit = đúng nguồn + đúng trang gold và chunk chứa TRỌN evidence_quote."""
    if hit["document_id"] != question["gold_source_id"] or hit["page"] != question["gold_page"]:
        return False
    return _norm(question["evidence_quote"]) in _norm(hit["text"])


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    flags = [is_hit(question, h) for h in hits]
    # đúng trang nhưng chunk không chứa đủ evidence -> nghi evidence bị tách qua chunk
    split = [(h["page"] == question["gold_page"] and not f) for h, f in zip(hits, flags)]
    return {
        "hit_at_1": bool(flags[:1] and flags[0]),
        "hit_at_3": any(flags[:3]),
        "per_rank_hit": flags[:3],
        "per_rank_gold_page_but_incomplete": split[:3],
        "evidence_possibly_split": (not any(flags)) and any(split),
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Gộp theo strategy x split (+ 'all'); báo tử/mẫu."""
    agg: dict[str, dict[str, list[int]]] = defaultdict(lambda: {"h1": [], "h3": []})
    for t in traces:
        for key in (f"{t['strategy']}|{t['split']}", f"{t['strategy']}|all"):
            agg[key]["h1"].append(int(t["eval"]["hit_at_1"]))
            agg[key]["h3"].append(int(t["eval"]["hit_at_3"]))
    out = {}
    for key, v in sorted(agg.items()):
        n = len(v["h1"])
        out[key] = {"n": n, "hit1": sum(v["h1"]), "hit3": sum(v["h3"]),
                    "hit1_rate": round(sum(v["h1"]) / n, 4), "hit3_rate": round(sum(v["h3"]) / n, 4)}
    return out
