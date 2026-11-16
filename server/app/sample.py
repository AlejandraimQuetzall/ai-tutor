"""A three-source memory course that runs with no model key.

Quotes in the lessons and questions are copied from examples/memory.
"""

from __future__ import annotations

from .config import repo_root


def sources() -> list[dict]:
    folder = repo_root() / "examples" / "memory"
    files = [
        ("01-encoding.md", "Encoding notes", "md"),
        ("02-storage.md", "Storage notes", "md"),
        ("03-retrieval.md", "Retrieval notes", "md"),
    ]
    loaded = []
    for filename, name, kind in files:
        text = (folder / filename).read_text(encoding="utf-8").strip()
        loaded.append(
            {
                "name": name,
                "kind": kind,
                "text": text,
                "spans": [{"locator": "section 1", "text": text}],
            }
        )
    return loaded


def _cite(material: dict, quote: str) -> dict:
    return {
        "quote": quote,
        "source_name": material["name"],
        "locator": "section 1",
    }


def course_body() -> dict:
    materials = sources()
    encoding, storage, retrieval = materials
    q_attention = "Attention decides what enters that trace."
    q_elaborate = "Elaborative encoding connects the new idea to something you already know, which makes the trace easier to find later."
    q_repeat = "Repeating a word without meaning it is a weak form of encoding."
    q_fade = "A short-term trace fades in seconds unless it is rehearsed."
    q_sleep = "Sleep shortly after study supports consolidation of material you paid attention to."
    q_consol = "Material that was never encoded cannot be consolidated, because there is no trace to stabilize."
    q_practice = "A successful retrieval strengthens the trace more than rereading the same passage."
    q_feedback = "Feedback after a failed attempt tells you which cue was missing."
    q_cue = "Retrieval is using a cue to bring a stored trace back into mind."

    chapters = [
        {
            "title": "Encoding",
            "overview": "How an experience becomes a memory trace, and why meaning beats bare repetition.",
            "lesson_md": """A memory starts when an experience becomes a trace. What gets in depends on attention, and how findable it is later depends on whether you tied the new idea to something you already know.

## Attention selects the trace

Encoding is the process of turning an experience into a memory trace. The notes are direct about the gate in front of that process.

> Attention decides what enters that trace.

A page you did not attend to has little chance of being encoded. The later stages of memory do not get a chance to repair that miss.

## Meaning makes the trace findable

> Elaborative encoding connects the new idea to something you already know, which makes the trace easier to find later.

A definition copied with no link to prior knowledge is weaker than the same definition tied to an example you can picture. The strength is in the link, not in how official the wording looks.

## Repetition without meaning stays weak

> Repeating a word without meaning it is a weak form of encoding.

The sound can feel familiar while the idea still has no durable trace. Meaning, not the number of repetitions, is what gives encoding its strength.
""",
            "summary_md": (
                "Encoding turns an experience into a memory trace, and attention decides what enters it. "
                "A page you never attend to has little chance of being stored later. Elaborative encoding "
                "connects the new idea to something you already know, which makes the trace easier to find. "
                "A copied definition with no link to prior knowledge is weaker than one tied to an example "
                "you can picture. Repeating a word without meaning it only makes the sound familiar. "
                "Meaning, not the number of repetitions, gives encoding its strength."
            ),
            "citations": [_cite(encoding, q_attention), _cite(encoding, q_elaborate), _cite(encoding, q_repeat)],
            "questions": [
                {
                    "stem": "What decides whether an experience enters a memory trace?",
                    "options": [
                        {"id": "a", "text": "Attention"},
                        {"id": "b", "text": "The number of times you repeat the words"},
                        {"id": "c", "text": "Sleep on the night after reading"},
                    ],
                    "correct_id": "a",
                    "explanation": "The encoding notes say attention decides what enters the trace. Repetition without meaning is described as a weak form of encoding, not the gate.",
                    "hint": "Look at the sentence that names the gate in front of the trace.",
                    "quote": q_attention,
                    "source_name": encoding["name"],
                    "locator": "section 1",
                },
                {
                    "stem": "Why is elaborative encoding easier to use later than a definition copied on its own?",
                    "options": [
                        {"id": "a", "text": "It connects the new idea to something you already know"},
                        {"id": "b", "text": "It repeats the wording until the sound is familiar"},
                        {"id": "c", "text": "It skips attention and writes the trace directly into storage"},
                    ],
                    "correct_id": "a",
                    "explanation": "The notes say elaborative encoding connects the new idea to something you already know, which makes the trace easier to find later.",
                    "hint": "The useful link is to prior knowledge, not to extra repetition.",
                    "quote": q_elaborate,
                    "source_name": encoding["name"],
                    "locator": "section 1",
                },
            ],
        },
        {
            "title": "Storage",
            "overview": "How a trace is kept, and why consolidation cannot rescue a page you never encoded.",
            "lesson_md": """Storage is what happens to a trace after encoding. Holding it for a few seconds, stabilizing it for a delay, and sleeping after study are three different claims in the notes.

## Short-term traces need rehearsal

> Storage is the maintenance of a memory trace over time.

A short-term trace does not wait patiently.

> A short-term trace fades in seconds unless it is rehearsed.

Rehearsal keeps the trace available. The notes also say rehearsal does not by itself decide whether the trace will last until next week.

## Consolidation stabilizes a real trace

> Consolidation stabilizes a trace so it can be recalled after a delay.

The trace is reorganized, not merely held still. There is a hard limit on what consolidation can do.

> Material that was never encoded cannot be consolidated, because there is no trace to stabilize.

## Sleep protects traces attention already made

> Sleep shortly after study supports consolidation of material you paid attention to.

Sleep is not a substitute for encoding. It protects traces that attention already created.
""",
            "summary_md": (
                "Storage is the maintenance of a memory trace over time. A short-term trace fades in seconds "
                "unless it is rehearsed, and rehearsal alone does not decide whether it lasts until next week. "
                "Consolidation stabilizes a trace so it can be recalled after a delay. Material that was never "
                "encoded cannot be consolidated, because there is no trace to stabilize. Sleep shortly after "
                "study supports consolidation of material you paid attention to. It protects traces attention "
                "already created and does not replace encoding."
            ),
            "citations": [_cite(storage, q_fade), _cite(storage, q_consol), _cite(storage, q_sleep)],
            "questions": [
                {
                    "stem": "What happens to a short-term trace that is not rehearsed?",
                    "options": [
                        {"id": "a", "text": "It fades in seconds"},
                        {"id": "b", "text": "It is consolidated during sleep automatically"},
                        {"id": "c", "text": "It becomes easier to retrieve than a rehearsed trace"},
                    ],
                    "correct_id": "a",
                    "explanation": "The storage notes say a short-term trace fades in seconds unless it is rehearsed.",
                    "hint": "The claim is about seconds, not about next week's review.",
                    "quote": q_fade,
                    "source_name": storage["name"],
                    "locator": "section 1",
                },
                {
                    "stem": "Which material can consolidation stabilize?",
                    "options": [
                        {"id": "a", "text": "A trace that encoding already created"},
                        {"id": "b", "text": "A page you never attended to"},
                        {"id": "c", "text": "Any reading, because sleep replaces encoding"},
                    ],
                    "correct_id": "a",
                    "explanation": "Material that was never encoded cannot be consolidated, because there is no trace to stabilize. Sleep supports consolidation of material you paid attention to.",
                    "hint": "Look for the sentence that says there is no trace to stabilize.",
                    "quote": q_consol,
                    "source_name": storage["name"],
                    "locator": "section 1",
                },
            ],
        },
        {
            "title": "Retrieval",
            "overview": "How a cue brings a trace back, and why a failed attempt still matters if feedback comes after it.",
            "lesson_md": """Retrieval is the moment a stored idea becomes available again. The notes separate the cue, the benefit of a successful recall, and the timing of feedback.

## A cue has to meet the trace

> Retrieval is using a cue to bring a stored trace back into mind.

The cue can be a question, a diagram with a blank, or the start of an example. Without a cue that matches the trace, the stored idea can remain silent.

## Practice beats another reread

> A successful retrieval strengthens the trace more than rereading the same passage.

This is called the retrieval practice effect. The effort of bringing the idea back is part of why the trace becomes easier to find next time.

## Feedback comes after the attempt

> Feedback after a failed attempt tells you which cue was missing.

The correction should arrive after the attempt, so the attempt itself still counts as retrieval. Reading the answer first turns the exercise back into rereading.
""",
            "summary_md": (
                "Retrieval uses a cue to bring a stored trace back into mind. A question, a blank in a diagram, "
                "or the start of an example can be that cue. Without a matching cue, the stored idea can stay "
                "silent. A successful retrieval strengthens the trace more than rereading the same passage. "
                "That difference is the retrieval practice effect. Feedback after a failed attempt tells you "
                "which cue was missing. Reading the answer first turns the exercise back into rereading."
            ),
            "citations": [_cite(retrieval, q_cue), _cite(retrieval, q_practice), _cite(retrieval, q_feedback)],
            "questions": [
                {
                    "stem": "What do the notes call the finding that a successful retrieval strengthens a trace more than rereading?",
                    "options": [
                        {"id": "a", "text": "The retrieval practice effect"},
                        {"id": "b", "text": "Consolidation"},
                        {"id": "c", "text": "Elaborative encoding"},
                    ],
                    "correct_id": "a",
                    "explanation": "The retrieval notes name this the retrieval practice effect: a successful retrieval strengthens the trace more than rereading the same passage.",
                    "hint": "The name is in the retrieval notes, not the storage notes.",
                    "quote": q_practice,
                    "source_name": retrieval["name"],
                    "locator": "section 1",
                },
                {
                    "stem": "When should feedback arrive if a retrieval attempt fails?",
                    "options": [
                        {"id": "a", "text": "After the attempt, so the attempt still counts as retrieval"},
                        {"id": "b", "text": "Before the attempt, so you can reread the answer first"},
                        {"id": "c", "text": "It is optional, because a failed attempt already names the missing cue"},
                    ],
                    "correct_id": "a",
                    "explanation": "Feedback after a failed attempt tells you which cue was missing. Reading the answer first turns the exercise back into rereading.",
                    "hint": "The notes contrast feedback after the attempt with reading the answer first.",
                    "quote": q_feedback,
                    "source_name": retrieval["name"],
                    "locator": "section 1",
                },
            ],
        },
    ]
    return {
        "title": "Memory: encoding, storage, and retrieval",
        "goal": "Understand how a memory is formed, kept, and recalled.",
        "depth": "guided",
        "overview": "Three notes, one path: how a trace is encoded, how it is kept, and how a cue brings it back.",
        "materials": materials,
        "chapters": chapters,
    }
