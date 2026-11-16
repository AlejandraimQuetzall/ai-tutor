"""Read sources, keep verbatim points, arrange chapters, write lessons and quizzes."""

from __future__ import annotations

import asyncio
import threading
import uuid
from datetime import datetime, timezone

from .config import settings
from .db import dump_json, execute, load_json, query_all, query_one
from .llm import LLMError, chat_json, chat_text
from .prompts import ARRANGE_SYSTEM, ASK_SYSTEM, EXTRACT_SYSTEM, LESSON_SYSTEM
from .textutil import chunks, clip_spans, locate_quote

_tasks: set[asyncio.Task] = set()


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def start(course_id: str) -> None:
    """Run the pipeline off the request. Sync routes execute on a worker thread."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        threading.Thread(target=lambda: asyncio.run(_run(course_id)), daemon=True).start()
        return
    task = loop.create_task(_run(course_id))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


def _touch(course_id: str, **fields) -> None:
    assignments = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [now(), course_id]
    execute(f"UPDATE course SET {assignments}, updated_at = ? WHERE id = ?", tuple(values))


async def _run(course_id: str) -> None:
    cfg = settings()
    try:
        if not cfg.llm_configured:
            raise LLMError("Set LLM_API_KEY to generate a path from your own files.")
        materials = query_all(
            "SELECT * FROM course_material WHERE course_id = ? ORDER BY name",
            (course_id,),
        )
        course = query_one("SELECT * FROM course WHERE id = ?", (course_id,))
        if course is None:
            return
        spans = []
        for material in materials:
            for span in load_json(material["spans_json"], []):
                spans.append(
                    {
                        "material_name": material["name"],
                        "locator": span.get("locator") or "source",
                        "text": span.get("text") or "",
                    }
                )
        _touch(course_id, status="generating", stage="read", message="Reading your materials", progress=8)
        spans, warning = clip_spans(spans)
        if warning:
            _touch(course_id, warning=warning)
        if not spans:
            raise LLMError("No readable text was found in these materials.")

        numbered = []
        for index, span in enumerate(spans, start=1):
            numbered.append({**span, "id": f"s{index}"})
        _touch(course_id, stage="extract", message="Extracting concepts that the sources support", progress=22)
        points = await _extract(cfg, numbered)
        if len(points) < 2:
            raise LLMError(
                "Not enough learnable content was grounded in the sources. "
                "Try a file with clearer prose, or a smaller excerpt."
            )
        points = points[:40]
        for index, point in enumerate(points, start=1):
            point["pid"] = f"p{index}"

        _touch(course_id, stage="arrange", message="Arranging the concepts into chapters", progress=48)
        arranged = await _arrange(cfg, course, points)
        chapters = _cover(arranged, points)
        _touch(
            course_id,
            title=arranged.get("title") or course["title"],
            overview=arranged.get("overview") or "",
            stage="write",
            message="Writing the first chapter",
            progress=58,
        )
        execute("DELETE FROM chapter WHERE course_id = ?", (course_id,))
        total = len(chapters)
        for index, chapter in enumerate(chapters, start=1):
            _touch(
                course_id,
                message=f"Writing chapter {index} of {total}: {chapter['title']}",
                progress=58 + int(36 * (index - 1) / max(total, 1)),
            )
            written = await _lesson(cfg, course, chapter)
            chapter_id = new_id()
            execute(
                """
                INSERT INTO chapter
                (id, course_id, position, title, overview, lesson_md, summary_md, citations_json, questions_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chapter_id,
                    course_id,
                    index,
                    chapter["title"],
                    chapter["overview"],
                    written["lesson_md"],
                    written["summary_md"],
                    dump_json(written["citations"]),
                    dump_json(written["questions"]),
                ),
            )
        _touch(course_id, status="ready", stage="ready", message="Your learning path is ready", progress=100)
    except Exception as exc:  # surface a short message; never the key or the request payload
        message = str(exc).strip() or "Generation failed."
        if len(message) > 400:
            message = message[:400]
        _touch(course_id, status="failed", stage="failed", message=message, progress=100)


async def _extract(cfg, spans: list[dict]) -> list[dict]:
    points = []
    seen_quotes = set()
    for batch in chunks(spans)[:8]:
        user = _span_block(batch)
        try:
            payload = await chat_json(cfg, EXTRACT_SYSTEM, user, max_tokens=2200)
        except LLMError:
            continue
        for item in payload.get("points") or []:
            if not isinstance(item, dict):
                continue
            quote = str(item.get("quote") or "").strip()
            span = locate_quote(quote, batch)
            if span is None:
                continue
            folded = " ".join(quote.split())
            if folded in seen_quotes:
                continue
            seen_quotes.add(folded)
            importance = item.get("importance")
            if importance not in {"core", "supporting", "supplementary"}:
                importance = "supporting"
            points.append(
                {
                    "name": _clip(item.get("name") or "Concept", 160),
                    "statement": _clip(item.get("statement") or quote, 600),
                    "quote": quote,
                    "importance": importance,
                    "source_name": span["material_name"],
                    "locator": span["locator"],
                }
            )
    rank = {"core": 0, "supporting": 1, "supplementary": 2}
    points.sort(key=lambda point: rank.get(point["importance"], 1))
    return points


async def _arrange(cfg, course: dict, points: list[dict]) -> dict:
    lines = [
        f"Learner goal: {course['goal'] or 'Learn the material in a clear order.'}",
        f"Depth: {course['depth']}",
        "",
    ]
    for point in points:
        lines.append(
            f"{point['pid']} | {point['importance']} | {point['name']} | {point['statement']}"
        )
    try:
        payload = await chat_json(cfg, ARRANGE_SYSTEM, "\n".join(lines), max_tokens=1800)
    except LLMError:
        payload = {}
    title = _clip(payload.get("title") or course["title"] or "Learning path", 180)
    overview = _clip(payload.get("overview") or "", 500)
    return {"title": title, "overview": overview, "chapters": payload.get("chapters") or []}


def _cover(arranged: dict, points: list[dict]) -> list[dict]:
    by_id = {point["pid"]: point for point in points}
    used = set()
    chapters = []
    for raw in arranged.get("chapters") or []:
        if not isinstance(raw, dict):
            continue
        ids = [pid for pid in raw.get("point_ids") or [] if pid in by_id and pid not in used]
        if not ids:
            continue
        used.update(ids)
        chapters.append(
            {
                "title": _clip(raw.get("title") or "Chapter", 160),
                "overview": _clip(raw.get("overview") or "", 400),
                "points": [by_id[pid] for pid in ids],
            }
        )
    leftovers = [point for point in points if point["pid"] not in used]
    if leftovers:
        chapters.append(
            {
                "title": "Further concepts",
                "overview": "Concepts from the sources that the first arrangement did not place.",
                "points": leftovers,
            }
        )
    if not chapters:
        for offset in range(0, len(points), 4):
            group = points[offset : offset + 4]
            chapters.append(
                {
                    "title": group[0]["name"],
                    "overview": group[0]["statement"],
                    "points": group,
                }
            )
    return chapters[:8]


async def _lesson(cfg, course: dict, chapter: dict) -> dict:
    depth = (
        "Write a fuller lesson of about 450 to 700 words."
        if course.get("depth") == "guided"
        else "Write a short overview of about 180 to 280 words."
    )
    lines = [
        f"Course: {course.get('title') or 'Learning path'}",
        f"Goal: {course.get('goal') or ''}",
        f"Chapter: {chapter['title']}",
        f"Chapter overview: {chapter['overview']}",
        depth,
        "",
        "Points:",
    ]
    for point in chapter["points"]:
        lines.append(
            "\n".join(
                [
                    f"Name: {point['name']}",
                    f"Statement: {point['statement']}",
                    f"Source: {point['source_name']} ({point['locator']})",
                    f"Quote: {point['quote']}",
                ]
            )
        )
    citations = [
        {"quote": point["quote"], "source_name": point["source_name"], "locator": point["locator"]}
        for point in chapter["points"]
    ]
    try:
        payload = await chat_json(cfg, LESSON_SYSTEM, "\n\n".join(lines), max_tokens=3200)
        lesson = str(payload.get("lesson_md") or "").strip()
        summary = str(payload.get("summary_md") or "").strip()
        questions = _questions(payload.get("questions") or [], chapter["points"])
        if lesson and summary:
            return {
                "lesson_md": lesson,
                "summary_md": summary,
                "citations": citations,
                "questions": questions,
            }
    except LLMError:
        pass
    return {
        "lesson_md": _fallback_lesson(chapter),
        "summary_md": _fallback_summary(chapter),
        "citations": citations,
        "questions": [],
    }


def _questions(raw_questions, points: list[dict]) -> list[dict]:
    spans = [{"text": point["quote"], "source_name": point["source_name"], "locator": point["locator"]} for point in points]
    ready = []
    for item in raw_questions:
        if not isinstance(item, dict) or len(ready) >= 4:
            continue
        span = locate_quote(str(item.get("quote") or ""), spans)
        options = []
        for option in item.get("options") or []:
            if isinstance(option, dict) and option.get("id") and option.get("text"):
                options.append({"id": str(option["id"]), "text": _clip(option["text"], 300)})
        correct = str(item.get("correct_id") or "")
        if span is None or len(options) < 2 or correct not in {option["id"] for option in options}:
            continue
        ready.append(
            {
                "stem": _clip(item.get("stem") or "Check the source.", 500),
                "options": options[:4],
                "correct_id": correct,
                "explanation": _clip(item.get("explanation") or "", 800),
                "hint": _clip(item.get("hint") or "", 300),
                "quote": str(item.get("quote") or "").strip(),
                "source_name": span["source_name"],
                "locator": span["locator"],
            }
        )
    return ready


def _fallback_lesson(chapter: dict) -> str:
    lines = [chapter["overview"], ""]
    for point in chapter["points"]:
        lines.extend(
            [
                f"## {point['name']}",
                "",
                point["statement"],
                "",
                f"> {point['quote']}",
                "",
                f"— {point['source_name']}, {point['locator']}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def _fallback_summary(chapter: dict) -> str:
    bits = [point["statement"] for point in chapter["points"][:4]]
    return " ".join(bits)


def _span_block(spans: list[dict]) -> str:
    blocks = []
    for span in spans:
        blocks.append(
            f"[{span['id']} | {span['material_name']} | {span['locator']}]\n{span['text']}"
        )
    return "\n\n".join(blocks)


def _clip(value, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


async def answer_question(course: dict, chapter: dict, question: str) -> str:
    cfg = settings()
    citations = load_json(chapter["citations_json"], [])
    lines = [
        f"Chapter: {chapter['title']}",
        "",
        "Lesson:",
        chapter["lesson_md"],
        "",
        "Source quotes:",
    ]
    for citation in citations:
        lines.append(f"- {citation.get('source_name')} ({citation.get('locator')}): {citation.get('quote')}")
    lines.extend(["", f"Learner question: {question.strip()}"])
    return await chat_text(cfg, ASK_SYSTEM, "\n".join(lines), max_tokens=700, json_mode=False)
