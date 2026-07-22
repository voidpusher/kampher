"""Shared prompt building blocks for the document pipeline."""

from __future__ import annotations

from app.ai.pipeline.base import DocumentContext

ANALYST_SYSTEM = (
    "You are Kampher's document analyst. You read one piece of public internet "
    "content (forum post, tweet, issue, discussion) and extract structured "
    "business-intelligence signals from it.\n"
    "Rules:\n"
    "- Judge only what the text supports. Never invent facts, entities, or pain.\n"
    "- Quotes must be verbatim substrings of the document.\n"
    "- Marketing language about the author's own product is not user pain.\n"
    "- When a taxonomy list is provided, use only slugs from that list.\n"
    "- Calibrate confidences honestly; 1.0 means certain."
)

_MAX_BODY_CHARS = 6000  # tail-truncate pathological documents, keep cost bounded


def document_block(ctx: DocumentContext) -> str:
    body = ctx.body if len(ctx.body) <= _MAX_BODY_CHARS else ctx.body[:_MAX_BODY_CHARS] + " …"
    lines = [
        "## Document",
        f"source: {ctx.source.value}",
        f"community: {ctx.community or '-'}",
        f"posted_at: {ctx.posted_at.isoformat()}",
        f"engagement: {ctx.metrics or '-'}",
        f"title: {ctx.title or '-'}",
        "body:",
        body or "(empty)",
    ]
    return "\n".join(lines)
