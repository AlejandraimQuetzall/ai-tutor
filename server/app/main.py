"""HTTP API and, when the web app has been built, the study interface."""

from __future__ import annotations

import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import settings
from .db import connect, dump_json, execute, load_json, query_all, query_one
from .llm import LLMError, transcribe
from .parse import (
    AUDIO_EXTENSIONS,
    ParseError,
    extension_of,
    kind_for,
    parse_transcript,
    parse_upload,
    parse_url,
)
from .pipeline import answer_question, new_id, now, start
from .sample import course_body

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    cfg = settings()
    connect(cfg.data_dir / "learning-path.db")
    yield


app = FastAPI(title="Lynote Learning Path", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class LinkIn(BaseModel):
    url: str = Field(min_length=4, max_length=2000)


class CourseIn(BaseModel):
    item_ids: list[str] = Field(min_length=1, max_length=20)
    goal: str = ""
    depth: str = "guided"
    title: str = ""


class QuizIn(BaseModel):
    option_id: str


class NoteIn(BaseModel):
    text: str = ""


class AskIn(BaseModel):
    chapter_id: str
    question: str = Field(min_length=1, max_length=1000)


@app.get("/api/health")
def health() -> dict:
    cfg = settings()
    return {"status": "ok", "llm_configured": cfg.llm_configured}


@app.get("/api/shelf")
def shelf() -> dict:
    rows = query_all("SELECT id, name, kind, created_at FROM shelf_item ORDER BY created_at")
    return {"items": rows, "limit": 20}


@app.post("/api/shelf/upload")
async def upload(files: list[UploadFile] = File(...)) -> dict:
    created = []
    for upload_file in files:
        if _shelf_count() >= 20:
            raise HTTPException(400, "The shelf holds 20 sources. Remove one before adding another.")
        data = await upload_file.read()
        name = upload_file.filename or "notes.txt"
        try:
            if extension_of(name) in AUDIO_EXTENSIONS:
                text = await transcribe(
                    settings(),
                    name,
                    data,
                    upload_file.content_type or "application/octet-stream",
                )
                spans = parse_transcript(text)
            else:
                spans = parse_upload(name, data)
        except ParseError as exc:
            raise HTTPException(400, str(exc)) from exc
        except LLMError as exc:
            raise HTTPException(400, str(exc)) from exc
        created.append(_insert_shelf(name, kind_for(name), spans))
    return {"items": created}


@app.post("/api/shelf/link")
def add_link(body: LinkIn) -> dict:
    if _shelf_count() >= 20:
        raise HTTPException(400, "The shelf holds 20 sources. Remove one before adding another.")
    try:
        name, spans = parse_url(body.url)
    except ParseError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _insert_shelf(name or body.url, "link", spans)


@app.delete("/api/shelf/{item_id}")
def remove_item(item_id: str) -> dict:
    execute("DELETE FROM shelf_item WHERE id = ?", (item_id,))
    return {"ok": True}


@app.get("/api/courses")
def courses() -> dict:
    rows = query_all(
        """
        SELECT id, title, status, progress, sample, updated_at
        FROM course ORDER BY updated_at DESC
        """
    )
    return {"courses": rows}


@app.post("/api/courses")
def create_course(body: CourseIn) -> dict:
    if body.depth not in {"guided", "overview"}:
        raise HTTPException(400, "Depth is either guided or overview.")
    if not settings().llm_configured:
        raise HTTPException(400, "Set LLM_API_KEY to generate a path from your own files.")
    items = []
    for item_id in body.item_ids:
        row = query_one("SELECT * FROM shelf_item WHERE id = ?", (item_id,))
        if row is None:
            raise HTTPException(400, "One of the shelf items is no longer there. Refresh and try again.")
        items.append(row)
    course_id = new_id()
    title = (body.title or "").strip() or _title_from_items(items)
    stamp = now()
    execute(
        """
        INSERT INTO course
        (id, title, goal, depth, status, stage, message, progress, warning, overview, sample, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'generating', 'read', 'Reading your materials', 5, '', '', 0, ?, ?)
        """,
        (course_id, title, body.goal.strip()[:400], body.depth, stamp, stamp),
    )
    for item in items:
        execute(
            """
            INSERT INTO course_material (id, course_id, name, kind, text, spans_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (new_id(), course_id, item["name"], item["kind"], item["text"], item["spans_json"]),
        )
    start(course_id)
    return {"id": course_id, "status": "generating"}


@app.post("/api/courses/sample")
def create_sample() -> dict:
    body = course_body()
    course_id = new_id()
    stamp = now()
    execute(
        """
        INSERT INTO course
        (id, title, goal, depth, status, stage, message, progress, warning, overview, sample, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'ready', 'ready', 'Sample path ready', 100, '', ?, 1, ?, ?)
        """,
        (course_id, body["title"], body["goal"], body["depth"], body["overview"], stamp, stamp),
    )
    for material in body["materials"]:
        execute(
            """
            INSERT INTO course_material (id, course_id, name, kind, text, spans_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                new_id(),
                course_id,
                material["name"],
                material["kind"],
                material["text"],
                dump_json(material["spans"]),
            ),
        )
    for index, chapter in enumerate(body["chapters"], start=1):
        execute(
            """
            INSERT INTO chapter
            (id, course_id, position, title, overview, lesson_md, summary_md, citations_json, questions_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id(),
                course_id,
                index,
                chapter["title"],
                chapter["overview"],
                chapter["lesson_md"],
                chapter["summary_md"],
                dump_json(chapter["citations"]),
                dump_json(chapter["questions"]),
            ),
        )
    return {"id": course_id}


@app.post("/api/courses/{course_id}/retry")
def retry_course(course_id: str) -> dict:
    course = _require_course(course_id)
    if course["sample"]:
        raise HTTPException(400, "The sample path is already complete.")
    if course["status"] == "generating":
        raise HTTPException(400, "This path is still being written.")
    if not settings().llm_configured:
        raise HTTPException(400, "Set LLM_API_KEY to generate a path from your own files.")
    execute("DELETE FROM chapter WHERE course_id = ?", (course_id,))
    execute("DELETE FROM chapter_state WHERE course_id = ?", (course_id,))
    execute(
        """
        UPDATE course
        SET status = 'generating', stage = 'read', message = 'Reading your materials', progress = 5, updated_at = ?
        WHERE id = ?
        """,
        (now(), course_id),
    )
    start(course_id)
    return {"id": course_id, "status": "generating"}


@app.get("/api/courses/{course_id}")
def get_course(course_id: str) -> dict:
    course = _require_course(course_id)
    materials = query_all(
        "SELECT id, name, kind FROM course_material WHERE course_id = ? ORDER BY name",
        (course_id,),
    )
    chapters = query_all(
        "SELECT * FROM chapter WHERE course_id = ? ORDER BY position",
        (course_id,),
    )
    states = {
        row["chapter_id"]: row
        for row in query_all("SELECT * FROM chapter_state WHERE course_id = ?", (course_id,))
    }
    public_chapters = []
    for index, chapter in enumerate(chapters):
        state = states.get(chapter["id"], {})
        previous = chapters[index - 1] if index else None
        unlocked = previous is None or _chapter_cleared(previous, states.get(previous["id"], {}))
        public_chapters.append(
            {
                "id": chapter["id"],
                "position": chapter["position"],
                "title": chapter["title"],
                "overview": chapter["overview"] if unlocked else "",
                "lesson_md": chapter["lesson_md"] if unlocked else "",
                "summary_md": chapter["summary_md"] if unlocked else "",
                "citations": load_json(chapter["citations_json"], []) if unlocked else [],
                "questions": _public_questions(load_json(chapter["questions_json"], []), state) if unlocked else [],
                "opened": bool(state.get("opened")),
                "quiz_correct": bool(state.get("quiz_correct")),
                "quiz_answered": _chapter_cleared(chapter, state),
                "note": state.get("note") or "",
                "unlocked": unlocked,
            }
        )
    done = sum(1 for chapter in public_chapters if chapter["quiz_answered"])
    return {
        "id": course["id"],
        "title": course["title"],
        "goal": course["goal"],
        "depth": course["depth"],
        "status": course["status"],
        "stage": course["stage"],
        "message": course["message"],
        "progress": course["progress"],
        "warning": course["warning"],
        "overview": course["overview"],
        "sample": bool(course["sample"]),
        "materials": materials,
        "chapters": public_chapters,
        "studied": done,
        "chapter_count": len(public_chapters),
    }


@app.post("/api/courses/{course_id}/chapters/{chapter_id}/open")
def open_chapter(course_id: str, chapter_id: str) -> dict:
    _require_chapter(course_id, chapter_id)
    _ensure_state(course_id, chapter_id)
    execute(
        "UPDATE chapter_state SET opened = 1 WHERE course_id = ? AND chapter_id = ?",
        (course_id, chapter_id),
    )
    return {"ok": True}


@app.post("/api/courses/{course_id}/chapters/{chapter_id}/quiz")
def submit_quiz(course_id: str, chapter_id: str, body: QuizIn) -> dict:
    chapter = _require_chapter(course_id, chapter_id)
    _ensure_unlocked(course_id, chapter)
    questions = load_json(chapter["questions_json"], [])
    if not questions:
        raise HTTPException(400, "This chapter has no quiz yet.")
    state = _ensure_state(course_id, chapter_id)
    answered = load_json(state.get("quiz_choice") or "", {})
    if not isinstance(answered, dict):
        answered = {}
    target = None
    for index, _item in enumerate(questions):
        if str(index) not in answered:
            target = index
            break
    if target is None:
        raise HTTPException(400, "This chapter quiz is already complete.")
    question = questions[target]
    correct = body.option_id == question["correct_id"]
    answered[str(target)] = {"option_id": body.option_id, "correct": correct}
    all_done = all(str(index) in answered for index in range(len(questions)))
    all_correct = all(item.get("correct") for item in answered.values())
    execute(
        """
        UPDATE chapter_state
        SET quiz_choice = ?, quiz_correct = ?, opened = 1
        WHERE course_id = ? AND chapter_id = ?
        """,
        (dump_json(answered), int(all_done and all_correct), course_id, chapter_id),
    )
    return {
        "question_index": target,
        "correct": correct,
        "correct_id": question["correct_id"],
        "explanation": question["explanation"],
        "quote": question["quote"],
        "source_name": question["source_name"],
        "locator": question["locator"],
        "chapter_complete": all_done,
    }


@app.put("/api/courses/{course_id}/chapters/{chapter_id}/note")
def save_note(course_id: str, chapter_id: str, body: NoteIn) -> dict:
    _require_chapter(course_id, chapter_id)
    _ensure_state(course_id, chapter_id)
    execute(
        "UPDATE chapter_state SET note = ? WHERE course_id = ? AND chapter_id = ?",
        (body.text[:8000], course_id, chapter_id),
    )
    return {"ok": True}


@app.post("/api/courses/{course_id}/ask")
async def ask(course_id: str, body: AskIn) -> dict:
    chapter = _require_chapter(course_id, body.chapter_id)
    course = _require_course(course_id)
    if not settings().llm_configured:
        raise HTTPException(400, "Set LLM_API_KEY to ask questions about this chapter.")
    try:
        reply = await answer_question(course, chapter, body.question)
    except LLMError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"reply": reply}


@app.delete("/api/courses/{course_id}")
def delete_course(course_id: str) -> dict:
    _require_course(course_id)
    execute("DELETE FROM chapter_state WHERE course_id = ?", (course_id,))
    execute("DELETE FROM chapter WHERE course_id = ?", (course_id,))
    execute("DELETE FROM course_material WHERE course_id = ?", (course_id,))
    execute("DELETE FROM course WHERE id = ?", (course_id,))
    return {"ok": True}


def _shelf_count() -> int:
    row = query_one("SELECT COUNT(*) AS n FROM shelf_item")
    return int(row["n"] if row else 0)


def _insert_shelf(name: str, kind: str, spans: list[dict]) -> dict:
    text = "\n\n".join(span["text"] for span in spans)
    item_id = new_id()
    execute(
        """
        INSERT INTO shelf_item (id, name, kind, text, spans_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (item_id, name[:180], kind, text, dump_json(spans), now()),
    )
    return {"id": item_id, "name": name[:180], "kind": kind}


def _title_from_items(items: list[dict]) -> str:
    if len(items) == 1:
        return items[0]["name"]
    return f"{items[0]['name']} and {len(items) - 1} more"


def _require_course(course_id: str) -> dict:
    course = query_one("SELECT * FROM course WHERE id = ?", (course_id,))
    if course is None:
        raise HTTPException(404, "That learning path was not found.")
    return course


def _require_chapter(course_id: str, chapter_id: str) -> dict:
    _require_course(course_id)
    chapter = query_one(
        "SELECT * FROM chapter WHERE id = ? AND course_id = ?",
        (chapter_id, course_id),
    )
    if chapter is None:
        raise HTTPException(404, "That chapter was not found.")
    return chapter


def _ensure_state(course_id: str, chapter_id: str) -> dict:
    row = query_one(
        "SELECT * FROM chapter_state WHERE course_id = ? AND chapter_id = ?",
        (course_id, chapter_id),
    )
    if row:
        return row
    execute(
        """
        INSERT INTO chapter_state (course_id, chapter_id, opened, quiz_choice, quiz_correct, note)
        VALUES (?, ?, 0, '', 0, '')
        """,
        (course_id, chapter_id),
    )
    return query_one(
        "SELECT * FROM chapter_state WHERE course_id = ? AND chapter_id = ?",
        (course_id, chapter_id),
    ) or {}


def _chapter_cleared(chapter: dict, state: dict) -> bool:
    questions = load_json(chapter.get("questions_json") or "[]", [])
    if not questions:
        return bool(state.get("opened"))
    answered = load_json(state.get("quiz_choice") or "", {})
    return isinstance(answered, dict) and len(answered) >= len(questions)


def _ensure_unlocked(course_id: str, chapter: dict) -> None:
    chapters = query_all(
        "SELECT * FROM chapter WHERE course_id = ? ORDER BY position",
        (course_id,),
    )
    states = {
        row["chapter_id"]: row
        for row in query_all("SELECT * FROM chapter_state WHERE course_id = ?", (course_id,))
    }
    for index, item in enumerate(chapters):
        if item["id"] != chapter["id"]:
            continue
        if index == 0 or _chapter_cleared(chapters[index - 1], states.get(chapters[index - 1]["id"], {})):
            return
        raise HTTPException(400, "Finish the quiz on the previous chapter first.")


def _public_questions(questions: list[dict], state: dict) -> list[dict]:
    answered = load_json(state.get("quiz_choice") or "", {})
    if not isinstance(answered, dict):
        answered = {}
    public = []
    for index, question in enumerate(questions):
        record = answered.get(str(index)) or {}
        revealed = bool(record)
        public.append(
            {
                "stem": question["stem"],
                "options": question["options"],
                "hint": question.get("hint") or "",
                "answered": revealed,
                "choice": record.get("option_id") or "",
                "correct": bool(record.get("correct")) if revealed else False,
                "correct_id": question["correct_id"] if revealed else "",
                "explanation": (question.get("explanation") or "") if revealed else "",
                "quote": (question.get("quote") or "") if revealed else "",
                "source_name": (question.get("source_name") or "") if revealed else "",
                "locator": (question.get("locator") or "") if revealed else "",
            }
        )
    return public


def _install_frontend() -> None:
    index = STATIC_DIR / "index.html"
    if not index.is_file():
        return
    assets = STATIC_DIR / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/")
    def serve_index() -> FileResponse:
        return FileResponse(index)

    @app.get("/course/{course_id}")
    def course_page(course_id: str) -> FileResponse:
        return FileResponse(index)


_install_frontend()
mimetypes.add_type("application/javascript", ".js")
