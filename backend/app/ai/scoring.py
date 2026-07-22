"""Deterministic scoring math.

The LLM produces *component* scores with reasoning and evidence (stages
13-15). The composite opportunity score is a documented weighted blend
computed here — never a second model guess — so ranking is reproducible and
auditable.
"""

from __future__ import annotations

import math

from app.models.enums import ScoreKind

# Why these weights: pain and trend are the leading indicators of demand;
# competition is inverted (crowded market lowers the blend); market size and
# revenue matter but are the noisiest estimates, so they weigh less; virality
# is a distribution bonus, not a fundamental. Weights sum to 1.
COMPOSITE_WEIGHTS: dict[ScoreKind, float] = {
    ScoreKind.PAIN: 0.25,
    ScoreKind.TREND: 0.20,
    ScoreKind.NOVELTY: 0.15,
    ScoreKind.COMPETITION: 0.15,  # applied inverted: 100 - value
    ScoreKind.REVENUE_POTENTIAL: 0.10,
    ScoreKind.MARKET_SIZE: 0.10,
    ScoreKind.VIRALITY_POTENTIAL: 0.05,
}

_INVERTED = {ScoreKind.COMPETITION}


def composite_score(components: dict[ScoreKind, tuple[float, float]]) -> float:
    """Blend component (value, confidence) pairs into one 0-100 score.

    Each component is confidence-weighted: a shaky 90 moves the blend less
    than a confident 70. Missing components contribute nothing and their
    weight is renormalized away, so partial scoring never inflates results.
    """
    numerator = 0.0
    denominator = 0.0
    for kind, weight in COMPOSITE_WEIGHTS.items():
        if kind not in components:
            continue
        value, confidence = components[kind]
        if kind in _INVERTED:
            value = 100.0 - value
        effective = weight * max(min(confidence, 1.0), 0.0)
        numerator += effective * max(min(value, 100.0), 0.0)
        denominator += effective
    return round(numerator / denominator, 2) if denominator else 0.0


def overall_confidence(components: dict[ScoreKind, tuple[float, float]]) -> float:
    """Composite confidence = weighted mean of component confidences."""
    total_weight = 0.0
    acc = 0.0
    for kind, weight in COMPOSITE_WEIGHTS.items():
        if kind not in components:
            continue
        acc += weight * components[kind][1]
        total_weight += weight
    return round(acc / total_weight, 3) if total_weight else 0.0


def trend_score(counts: list[int]) -> tuple[float, float, float]:
    """Stage 13 (statistical half) — score a daily mention-count series.

    Returns (score 0-100, velocity, acceleration).

    velocity     = slope of a least-squares line over the window (mentions/day)
    acceleration = velocity(second half) - velocity(first half)
    score        = logistic squash of relative growth, so a topic going 2→20
                   outranks one going 1000→1100.
    """
    n = len(counts)
    if n < 2:
        return 0.0, 0.0, 0.0

    velocity = _slope(counts)
    half = n // 2
    acceleration = _slope(counts[half:]) - _slope(counts[:half]) if half >= 2 else 0.0

    baseline = max(sum(counts[:half]) / max(half, 1), 1.0)
    relative_growth = velocity / baseline
    score = 100.0 / (1.0 + math.exp(-4.0 * relative_growth))
    return round(score, 2), round(velocity, 4), round(acceleration, 4)


def _slope(ys: list[int]) -> float:
    n = len(ys)
    if n < 2:
        return 0.0
    xs = range(n)
    mean_x = (n - 1) / 2
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    var = sum((x - mean_x) ** 2 for x in xs)
    return cov / var if var else 0.0
