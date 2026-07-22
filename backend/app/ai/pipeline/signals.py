"""Zero-cost heuristics used as pipeline gates.

These never make final judgements — they route documents. False positives
cost one cheap LLM call; false negatives cost a missed signal, so thresholds
lean permissive.
"""

from __future__ import annotations

import re

# Phrases that correlate strongly with unmet-need language.
_PAIN_PATTERNS = [
    r"\bis there (a|any|some) (tool|app|way|service|library)",
    r"\bwhy is there no\b",
    r"\bwish (there was|it (had|could|would))",
    r"\b(so|really|incredibly) (frustrat|annoy)",
    r"\bhow do (i|you|we) (deal with|handle|manage|automate)",
    r"\b(hate|tired of|sick of|fed up)\b",
    r"\bpain (point|in the)\b",
    r"\bworkaround\b",
    r"\bdoesn'?t (work|support|scale|integrate)\b",
    r"\b(missing|lacks?|no) (feature|support|integration|api)\b",
    r"\balternative to\b",
    r"\bswitch(ing|ed) (from|away)\b",
    r"\btoo (expensive|slow|complicated|hard)\b",
    r"\bcan'?t (find|figure|get .{1,30} to work)\b",
    r"\bmanually? (doing|copy|paste|enter)",
    r"\bspent (hours|days|weeks)\b",
    r"\bfeature request\b",
    r"\bplease add\b",
]
_PAIN_RE = re.compile("|".join(_PAIN_PATTERNS), re.IGNORECASE)

_SPAM_PROMO_RE = re.compile(
    r"(check out my|use (promo|coupon|code)|limited time offer|dm me|link in bio"
    r"|100% free|earn \$|click here|sign up (now|today)|giveaway)",
    re.IGNORECASE,
)
_URL_RE = re.compile(r"https?://\S+")


def has_pain_signal(text: str) -> bool:
    return bool(_PAIN_RE.search(text))


def spam_heuristic(text: str) -> tuple[float, str]:
    """Return (spam_probability_estimate, reason). Cheap and conservative.

    < 0.25 → clean, > 0.75 → spam, in between → escalate to the fast model.
    """
    if not text.strip():
        return 0.9, "empty body"

    score = 0.0
    reasons: list[str] = []

    words = text.split()
    urls = _URL_RE.findall(text)
    if words and len(urls) / max(len(words), 1) > 0.15:
        score += 0.45
        reasons.append("high link density")
    promo_matches = len(_SPAM_PROMO_RE.findall(text))
    if promo_matches:
        # One promo phrase is a hint; a pile of them is a pitch.
        score += min(0.25 * promo_matches, 0.6)
        reasons.append(f"promotional phrasing x{promo_matches}")
    letters = [c for c in text if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.5 and len(letters) > 40:
        score += 0.3
        reasons.append("shouting")
    if len(words) < 4 and urls:
        score += 0.35
        reasons.append("link-only post")

    return min(score, 1.0), "; ".join(reasons) or "clean"
