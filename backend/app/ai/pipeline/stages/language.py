"""Stage 1 — language detection (local, free, gate).

lingua is the most accurate offline detector for short informal text; we
restrict the detector to a handful of high-volume languages, which both
speeds it up and improves precision.
"""

from __future__ import annotations

from typing import ClassVar

from lingua import Language, LanguageDetectorBuilder

from app.ai.pipeline.base import DocumentContext, LocalStage, StageResult
from app.core.config import get_settings

_DETECTOR = (
    LanguageDetectorBuilder.from_languages(
        Language.ENGLISH,
        Language.SPANISH,
        Language.FRENCH,
        Language.GERMAN,
        Language.PORTUGUESE,
        Language.RUSSIAN,
        Language.CHINESE,
        Language.JAPANESE,
        Language.HINDI,
        Language.KOREAN,
    )
    .with_low_accuracy_mode()  # 5x faster; plenty for a routing decision
    .build()
)


class LanguageStage(LocalStage):
    name: ClassVar[str] = "language"

    async def run(self, ctx: DocumentContext) -> StageResult:
        settings = get_settings()
        detected = _DETECTOR.detect_language_of(ctx.text)
        code = detected.iso_code_639_1.name.lower() if detected else "und"
        accepted = code in settings.target_languages
        return StageResult(
            stage=self.name,
            output={"language": code},
            gate_rejected=not accepted,
            gate_reason=None if accepted else f"language {code} not in targets",
        )
