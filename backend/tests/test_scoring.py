from __future__ import annotations

import math

from app.ai.scoring import (
    COMPOSITE_WEIGHTS,
    composite_score,
    overall_confidence,
    trend_score,
)
from app.models.enums import ScoreKind


def full_components(value: float = 70.0, confidence: float = 0.8):
    return {kind: (value, confidence) for kind in COMPOSITE_WEIGHTS}


def test_weights_sum_to_one() -> None:
    assert math.isclose(sum(COMPOSITE_WEIGHTS.values()), 1.0)


def test_composite_uniform_scores_reflect_inversion() -> None:
    # All components 70 → competition inverts to 30, dragging the blend below 70.
    score = composite_score(full_components(70.0))
    expected = 70.0 - COMPOSITE_WEIGHTS[ScoreKind.COMPETITION] * (70.0 - 30.0)
    assert math.isclose(score, expected, abs_tol=0.01)


def test_high_competition_lowers_composite() -> None:
    easy = full_components()
    crowded = dict(easy)
    crowded[ScoreKind.COMPETITION] = (95.0, 0.9)
    easy[ScoreKind.COMPETITION] = (10.0, 0.9)
    assert composite_score(crowded) < composite_score(easy)


def test_low_confidence_component_moves_blend_less() -> None:
    confident = full_components(50.0, 0.9)
    confident[ScoreKind.PAIN] = (100.0, 0.9)
    shaky = full_components(50.0, 0.9)
    shaky[ScoreKind.PAIN] = (100.0, 0.1)
    assert composite_score(confident) > composite_score(shaky)


def test_missing_components_renormalize_not_inflate() -> None:
    partial = {ScoreKind.PAIN: (80.0, 1.0)}
    assert composite_score(partial) == 80.0


def test_empty_components() -> None:
    assert composite_score({}) == 0.0
    assert overall_confidence({}) == 0.0


def test_trend_growth_beats_flat() -> None:
    growing, _, _ = trend_score([1, 2, 4, 7, 11, 16, 22])
    flat, _, _ = trend_score([10, 10, 10, 10, 10, 10, 10])
    declining, _, _ = trend_score([20, 16, 12, 8, 5, 2, 1])
    assert growing > flat > declining


def test_trend_relative_growth_favors_small_movers() -> None:
    small_mover, _, _ = trend_score([2, 3, 5, 9, 14, 20, 28])
    big_static, _, _ = trend_score([1000, 1010, 1020, 1030, 1040, 1050, 1060])
    assert small_mover > big_static


def test_trend_short_series_is_neutral() -> None:
    assert trend_score([5]) == (0.0, 0.0, 0.0)
