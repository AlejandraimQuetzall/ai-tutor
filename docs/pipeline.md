# Pipeline

A path is finished only when every taught claim can be pointed at a sentence in the materials. The hosted Lynote product uses the same learning loop. This edition runs that loop against an OpenAI-compatible chat endpoint you configure.

## 1. Read

Parsers keep a locator with each span: a PDF page, a slide number, a caption time, or a section of notes. Private and local URLs are refused before any request is sent. Text longer than the open-edition budget is sampled from the start and from later spans, and the course records that warning. The hosted product reads the full document.

## 2. Extract

Each batch of spans is sent to the model with a demand for verbatim quotes. A point is kept only when `locate_quote` finds that quote inside one of those spans after whitespace is collapsed. A fragment shorter than 24 characters is discarded, so a heading or a bare number cannot pass as evidence. Duplicate quotes are dropped. At least two grounded points are required.

## 3. Arrange

The model receives point ids, names, and statements. It does not receive permission to add facts. The server then checks coverage:

- unknown ids are ignored
- a point the model skipped is appended, so nothing grounded is lost
- if the model returns no usable chapters, points are grouped in their existing order

The result is capped at eight chapters.

## 4. Write

Each chapter is one lesson, one summary, and up to four questions. A question is kept only when its quote sits inside a point quote from that chapter. The correct option is withheld from the client until the learner answers. If the lesson call fails, the chapter falls back to the point statements and the original quotes, and the quiz for that chapter is left empty rather than invented.

Guided depth asks for a fuller lesson. Overview asks for a shorter one. An optional goal changes emphasis. Neither one is allowed to import facts from outside the quotes.

## 5. Study

The workspace is Learn, Review, and Quick check.

- Learn shows the lesson and the source cards.
- Review shows the chapter summary and a note that stays in SQLite.
- Quick check reveals the explanation and the quote after an answer.
- The following chapter unlocks when every question in the current chapter has an answer.
- Ask is a separate call. Its instructions tell the model to refuse when the chapter sources do not contain the answer.

## Sample path

`examples/memory/` is a three-note course on encoding, storage, and retrieval. `POST /api/courses/sample` loads lessons and questions that quote those files. Tests fail if a sample quote is no longer a substring of its note. That path is the zero-key way to walk the study cycle.
