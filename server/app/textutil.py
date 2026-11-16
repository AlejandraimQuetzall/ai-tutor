"""Quote checks. A concept or question is kept only when its quote sits in the source."""

from __future__ import annotations

import re


def normalize(text: str) -> str:
    return " ".join((text or "").split())


def locate_quote(quote: str, spans: list[dict]) -> dict | None:
    """Return the span that contains the quote, after whitespace is collapsed.

    The match has to be a real substring of a source span. A short fragment is
    rejected so a heading or a bare number cannot pass as evidence.
    """
    folded = normalize(quote)
    if len(folded) < 24:
        return None
    for span in spans:
        if folded in normalize(span.get("text", "")):
            return span
    return None


def chunks(spans: list[dict], limit: int = 6500) -> list[list[dict]]:
    batches: list[list[dict]] = []
    current: list[dict] = []
    size = 0
    for span in spans:
        text = span.get("text") or ""
        if current and size + len(text) > limit:
            batches.append(current)
            current = []
            size = 0
        current.append(span)
        size += len(text)
    if current:
        batches.append(current)
    return batches


def clip_spans(spans: list[dict], max_chars: int = 56000, max_batches: int = 8) -> tuple[list[dict], str]:
    """Keep the open edition inside a predictable model budget.

    Longer courses still run: the reader keeps the start of the material and
    evenly spaced later spans, and the course records that the read was sampled.
    """
    if not spans:
        return [], ""
    kept: list[dict] = []
    total = 0
    for span in spans:
        text = span.get("text") or ""
        if total >= max_chars:
            break
        if total + len(text) > max_chars and kept:
            break
        kept.append(span)
        total += len(text)
    batches = chunks(kept)
    warning = ""
    if len(batches) > max_batches or len(kept) < len(spans):
        if len(batches) > max_batches:
            step = max(1, len(batches) // max_batches)
            picked = batches[::step][:max_batches]
            kept = [span for batch in picked for span in batch]
        warning = (
            "This open edition read a sampled portion of a long source so the "
            "run stays within one model budget. The hosted Lynote workspace reads "
            "the full document."
        )
    return kept, warning


_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def sentences(text: str) -> list[str]:
    parts = [part.strip() for part in _SENTENCE.split(text or "") if part.strip()]
    return parts or ([text.strip()] if text and text.strip() else [])
