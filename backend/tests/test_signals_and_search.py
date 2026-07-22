from __future__ import annotations

import uuid

from app.ai.pipeline.signals import has_pain_signal, spam_heuristic
from app.services.search import rrf_fuse


class TestPainSignal:
    def test_unmet_need_language_detected(self) -> None:
        assert has_pain_signal("Is there a tool that syncs Stripe invoices to Notion?")
        assert has_pain_signal("I'm so tired of manually copying data between sheets")
        assert has_pain_signal("Why is there no decent alternative to X for teams?")
        assert has_pain_signal("Please add dark mode, this is a feature request")

    def test_neutral_content_passes_through(self) -> None:
        assert not has_pain_signal("We shipped version 2.0 today with new docs.")
        assert not has_pain_signal("Here is a summary of the conference talks.")


class TestSpamHeuristic:
    def test_clean_question_scores_low(self) -> None:
        score, _ = spam_heuristic(
            "How do you all handle background jobs in FastAPI? Celery feels heavy "
            "for my use case and I wonder what smaller teams use."
        )
        assert score < 0.25

    def test_promo_blast_scores_high(self) -> None:
        score, reason = spam_heuristic(
            "CHECK OUT MY NEW COURSE!!! LIMITED TIME OFFER — SIGN UP TODAY "
            "https://spam.example https://spam2.example CLICK HERE dm me"
        )
        assert score > 0.75
        assert reason

    def test_empty_body_is_spam(self) -> None:
        score, _ = spam_heuristic("   ")
        assert score > 0.75


class TestRRF:
    def test_doc_in_both_rankings_wins(self) -> None:
        a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        fused = rrf_fuse([[a, b], [c, a]])
        assert fused[0][0] == a

    def test_rank_order_preserved_within_single_list(self) -> None:
        a, b = uuid.uuid4(), uuid.uuid4()
        fused = rrf_fuse([[a, b]])
        assert [doc for doc, _ in fused] == [a, b]

    def test_empty_input(self) -> None:
        assert rrf_fuse([]) == []
