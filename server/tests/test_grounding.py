import re
from pathlib import Path

from app.parse import parse_upload, youtube_id
from app.pipeline import _cover
from app.sample import course_body
from app.textutil import locate_quote, normalize


def test_sample_quotes_are_verbatim():
    body = course_body()
    sources = {item["name"]: item["text"] for item in body["materials"]}
    assert len(body["chapters"]) == 3
    for chapter in body["chapters"]:
        for citation in chapter["citations"]:
            assert normalize(citation["quote"]) in normalize(sources[citation["source_name"]])
        for question in chapter["questions"]:
            assert normalize(question["quote"]) in normalize(sources[question["source_name"]])
            assert question["correct_id"] in {option["id"] for option in question["options"]}


def test_locate_quote_rejects_invention_and_tiny_fragments():
    spans = [{"text": "Attention decides what enters that trace.", "locator": "section 1"}]
    assert locate_quote("Attention decides what enters that trace.", spans)["locator"] == "section 1"
    assert locate_quote("Attention   decides what enters that trace.", spans) is not None
    assert locate_quote("Sleep replaces attention.", spans) is None
    assert locate_quote("Attention decides", spans) is None


def test_arrangement_keeps_every_point():
    points = [
        {"pid": "p1", "name": "Attention", "statement": "Attention selects the trace.", "quote": "q", "importance": "core", "source_name": "n", "locator": "p. 1"},
        {"pid": "p2", "name": "Sleep", "statement": "Sleep protects a trace.", "quote": "q2", "importance": "supporting", "source_name": "n", "locator": "p. 2"},
    ]
    arranged = {"chapters": [{"title": "Encoding", "overview": "", "point_ids": ["p1", "missing"]}]}
    chapters = _cover(arranged, points)
    kept = [point["pid"] for chapter in chapters for point in chapter["points"]]
    assert kept == ["p1", "p2"]


def test_plain_text_upload_keeps_a_locator():
    text = (
        "Encoding is the process of turning an experience into a memory trace. "
        "Attention decides what enters that trace.\n\n"
        "Repeating a word without meaning it is a weak form of encoding. "
        "Meaning, not the number of repetitions, is what gives encoding its strength.\n"
    )
    spans = parse_upload("notes.txt", text.encode())
    assert spans
    assert spans[0]["locator"].startswith("section")
    assert "Attention decides" in spans[0]["text"]


def test_youtube_ids():
    assert youtube_id("https://www.youtube.com/watch?v=abcdefghijk") == "abcdefghijk"
    assert youtube_id("https://youtu.be/abcdefghijk") == "abcdefghijk"
    assert youtube_id("https://www.youtube.com/shorts/abcdefghijk") == "abcdefghijk"
    assert youtube_id("https://example.com/watch?v=abcdefghijk") is None


def test_repository_has_no_live_secrets():
    root = Path(__file__).resolve().parents[2]
    secret = re.compile(r"sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}")
    assigned = re.compile(r"(?m)^LLM_API_KEY\s*=\s*(\S*)\s*$")
    skip = {".git", ".venv", "node_modules", "data", "dist", "__pycache__", ".pytest_cache"}
    offenders = []
    for path in root.rglob("*"):
        if any(part in skip for part in path.parts) or not path.is_file():
            continue
        if path.name == ".env" or path.suffix in {".png", ".jpg", ".webp", ".pyc", ".db"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if secret.search(text) or any(match.group(1) for match in assigned.finditer(text)):
            offenders.append(str(path.relative_to(root)))
    assert offenders == []
