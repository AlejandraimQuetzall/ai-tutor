import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Link, useParams } from "react-router-dom";
import remarkGfm from "remark-gfm";
import { api, ApiError } from "./api";
import { Chapter, Course, PRODUCT_URL } from "./types";

const STAGES = [
  ["read", "Read materials"],
  ["extract", "Extract concepts"],
  ["arrange", "Arrange chapters"],
  ["write", "Write lessons and quizzes"],
] as const;

export function Study() {
  const { courseId = "" } = useParams();
  const [course, setCourse] = useState<Course | null>(null);
  const [loadError, setLoadError] = useState("");
  const [error, setError] = useState("");
  const [chapterId, setChapterId] = useState("");
  const [tab, setTab] = useState<"learn" | "review" | "check">("learn");
  const [hint, setHint] = useState(false);
  const [note, setNote] = useState("");
  const [question, setQuestion] = useState("");
  const [reply, setReply] = useState("");
  const [asking, setAsking] = useState(false);
  const [configured, setConfigured] = useState(false);

  const reload = useCallback(async () => {
    const next = await api<Course>(`/api/courses/${courseId}`);
    setCourse(next);
    setChapterId((current) => current || next.chapters.find((chapter) => chapter.unlocked)?.id || next.chapters[0]?.id || "");
    return next;
  }, [courseId]);

  useEffect(() => {
    void reload().catch((err: unknown) => setLoadError(err instanceof Error ? err.message : "Could not load this path."));
    void api<{ llm_configured: boolean }>("/api/health").then((health) => setConfigured(health.llm_configured)).catch(() => setConfigured(false));
  }, [reload]);

  useEffect(() => {
    if (course?.status !== "generating") return;
    const timer = window.setInterval(() => {
      void reload().catch(() => undefined);
    }, 1200);
    return () => window.clearInterval(timer);
  }, [course?.status, reload]);

  const chapter = course?.chapters.find((item) => item.id === chapterId) || course?.chapters[0];
  const noteBaseline = useRef({ id: "", text: "" });
  if (chapter && noteBaseline.current.id !== chapter.id) {
    noteBaseline.current = { id: chapter.id, text: chapter.note || "" };
    if (note !== noteBaseline.current.text) setNote(noteBaseline.current.text);
  }

  useEffect(() => {
    setHint(false);
    setReply("");
  }, [chapter?.id]);

  useEffect(() => {
    if (!chapter?.id || note === noteBaseline.current.text) return;
    const id = chapter.id;
    const text = note;
    const timer = window.setTimeout(() => {
      noteBaseline.current = { id, text };
      void api(`/api/courses/${courseId}/chapters/${id}/note`, {
        method: "PUT",
        body: JSON.stringify({ text }),
      });
    }, 300);
    return () => window.clearTimeout(timer);
  }, [note, chapter?.id, courseId]);

  useEffect(() => {
    if (!chapter?.unlocked || chapter.opened) return;
    void api(`/api/courses/${courseId}/chapters/${chapter.id}/open`, { method: "POST" })
      .then(() => reload())
      .catch(() => undefined);
  }, [chapter?.id, chapter?.opened, chapter?.unlocked, courseId, reload]);

  if (loadError && !course) {
    return (
      <div className="page">
        <p className="banner error">{loadError}</p>
        <Link to="/">Back to the shelf</Link>
      </div>
    );
  }
  if (!course) return <div className="page"><p className="muted">Loading the path…</p></div>;

  return (
    <div className="page study-page">
      <div className="study-top">
        <Link className="text-link" to="/">Shelf</Link>
        <div>
          <h1>{course.title}</h1>
          <p>{course.overview || course.goal}</p>
        </div>
        <div className="progress-pill">
          {course.status === "ready" ? `${course.studied} / ${course.chapter_count} quizzes` : `${course.progress}%`}
        </div>
      </div>
      {course.warning && <p className="banner">{course.warning}</p>}
      {course.sample && (
        <p className="banner">
          Sample path, no model key required. Generate from your own files after setting <code>LLM_API_KEY</code>,
          or study this subject on <a href={PRODUCT_URL}>Lynote</a>.
        </p>
      )}

      {course.status !== "ready" ? (
        <Progress course={course} onRetry={() => void api(`/api/courses/${course.id}/retry`, { method: "POST" }).then(() => reload())} />
      ) : (
        <div className="workspace">
          <aside className="path">
            <h2>Path</h2>
            <ol>
              {course.chapters.map((item) => (
                <li key={item.id}>
                  <button
                    className={`${item.id === chapter?.id ? "current" : ""} ${item.unlocked ? "" : "locked"}`}
                    onClick={() => item.unlocked && setChapterId(item.id)}
                  >
                    <span>{item.position}</span>
                    <strong>{item.title}</strong>
                    <em>{item.quiz_answered ? "Checked" : item.unlocked ? "Open" : "Locked"}</em>
                  </button>
                </li>
              ))}
            </ol>
          </aside>
          {chapter && chapter.unlocked ? (
            <ChapterView
              chapter={chapter}
              tab={tab}
              setTab={setTab}
              hint={hint}
              setHint={setHint}
              note={note}
              setNote={setNote}
              question={question}
              setQuestion={setQuestion}
              reply={reply}
              asking={asking}
              configured={configured}
              onSaveNote={() => void api(`/api/courses/${course.id}/chapters/${chapter.id}/note`, { method: "PUT", body: JSON.stringify({ text: note }) })}
              onAnswer={async (optionId) => {
                setError("");
                try {
                  await api(`/api/courses/${course.id}/chapters/${chapter.id}/quiz`, {
                    method: "POST",
                    body: JSON.stringify({ option_id: optionId }),
                  });
                  await reload();
                } catch (err) {
                  setError(err instanceof ApiError || err instanceof Error ? err.message : "Could not submit the quiz.");
                }
              }}
              onAsk={async () => {
                setAsking(true);
                setReply("");
                try {
                  const result = await api<{ reply: string }>(`/api/courses/${course.id}/ask`, {
                    method: "POST",
                    body: JSON.stringify({ chapter_id: chapter.id, question }),
                  });
                  setReply(result.reply);
                } catch (err) {
                  setReply(err instanceof ApiError || err instanceof Error ? err.message : "The tutor could not answer.");
                } finally {
                  setAsking(false);
                }
              }}
              onContinue={() => {
                const next = course.chapters.find((item) => item.position === chapter.position + 1 && item.unlocked);
                if (next) {
                  setChapterId(next.id);
                  setTab("learn");
                }
              }}
            />
          ) : (
            <section className="panel">
              <h2>This chapter is still locked</h2>
              <p>Finish the quiz on the previous chapter. The path stays in order.</p>
            </section>
          )}
        </div>
      )}
      {error && <p className="banner error">{error}</p>}
    </div>
  );
}

function Progress({ course, onRetry }: { course: Course; onRetry: () => void }) {
  const active = STAGES.findIndex(([id]) => id === course.stage);
  return (
    <section className="panel progress-panel">
      <h2>{course.status === "failed" ? "Generation stopped" : "Building your learning path"}</h2>
      <p>{course.message}</p>
      <div className="bar" aria-valuenow={course.progress} aria-valuemin={0} aria-valuemax={100}>
        <span style={{ width: `${course.progress}%` }} />
      </div>
      <ol className="stepper">
        {STAGES.map(([id, label], index) => (
          <li key={id} className={index < active ? "done" : index === active ? "now" : ""}>
            {label}
          </li>
        ))}
      </ol>
      {course.status === "failed" && (
        <button className="button" onClick={onRetry}>
          Try again
        </button>
      )}
    </section>
  );
}

function ChapterView(props: {
  chapter: Chapter;
  tab: "learn" | "review" | "check";
  setTab: (tab: "learn" | "review" | "check") => void;
  hint: boolean;
  setHint: (value: boolean) => void;
  note: string;
  setNote: (value: string) => void;
  question: string;
  setQuestion: (value: string) => void;
  reply: string;
  asking: boolean;
  configured: boolean;
  onSaveNote: () => void;
  onAnswer: (optionId: string) => Promise<void>;
  onAsk: () => Promise<void>;
  onContinue: () => void;
}) {
  const { chapter } = props;
  const pendingIndex = chapter.questions.findIndex((item) => !item.answered);
  const visible = pendingIndex === -1 ? chapter.questions : chapter.questions.slice(0, pendingIndex + 1);
  return (
    <section className="reader">
      <div className="tabs" role="tablist">
        {(["learn", "review", "check"] as const).map((id) => (
          <button key={id} role="tab" aria-selected={props.tab === id} className={props.tab === id ? "on" : ""} onClick={() => props.setTab(id)}>
            {id === "learn" ? "Learn" : id === "review" ? "Review" : "Quick check"}
          </button>
        ))}
      </div>

      {props.tab === "learn" && (
        <>
          <article className="lesson">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{chapter.lesson_md}</ReactMarkdown>
          </article>
          <div className="citations">
            <h3>Sources</h3>
            {chapter.citations.map((citation, index) => (
              <blockquote key={`${citation.locator}-${index}`}>
                <p>{citation.quote}</p>
                <footer>{citation.source_name} · {citation.locator}</footer>
              </blockquote>
            ))}
          </div>
        </>
      )}

      {props.tab === "review" && (
        <div className="review">
          <article className="lesson">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{chapter.summary_md}</ReactMarkdown>
          </article>
          <label className="notes">
            Your notes
            <textarea
              value={props.note}
              onChange={(event) => props.setNote(event.target.value)}
              onBlur={props.onSaveNote}
              placeholder="Keep a reminder beside this chapter."
            />
          </label>
        </div>
      )}

      {props.tab === "check" && (
        <div className="quiz">
          {visible.length === 0 ? (
            <p>This chapter has no quiz. The lesson is still grounded in the citations on Learn.</p>
          ) : (
            visible.map((current, index) => (
            <article key={current.stem}>
              <h3>{visible.length > 1 ? `${index + 1}. ` : ""}{current.stem}</h3>
              <div className="options">
                {current.options.map((option) => {
                  const revealed = current.answered;
                  const chosen = current.choice === option.id;
                  const right = revealed && option.id === current.correct_id;
                  return (
                    <button
                      key={option.id}
                      className={`option ${chosen ? "chosen" : ""} ${right ? "right" : ""}`}
                      disabled={current.answered}
                      onClick={() => void props.onAnswer(option.id)}
                    >
                      {option.text}
                    </button>
                  );
                })}
              </div>
              {!current.answered && current.hint && (
                <button className="text-link hint" type="button" onClick={() => props.setHint(!props.hint)}>
                  {props.hint ? "Hide hint" : "Hint"}
                </button>
              )}
              {props.hint && !current.answered && <p className="hint-copy">{current.hint}</p>}
              {current.answered && (
                <div className={`result ${current.correct ? "good" : "miss"}`}>
                  <strong>{current.correct ? "That matches the source." : "Not quite. The source says otherwise."}</strong>
                  <p>{current.explanation}</p>
                  {current.quote && (
                    <blockquote>
                      <p>{current.quote}</p>
                      <footer>{current.source_name} · {current.locator}</footer>
                    </blockquote>
                  )}
                </div>
              )}
            </article>
            ))
          )}
          {chapter.quiz_answered && (
            <button className="button" onClick={props.onContinue}>
              Continue
            </button>
          )}
        </div>
      )}

      <form
        className="ask"
        onSubmit={(event) => {
          event.preventDefault();
          if (props.question.trim()) void props.onAsk();
        }}
      >
        <h3>Ask about this chapter</h3>
        {props.configured ? (
          <>
            <textarea
              value={props.question}
              onChange={(event) => props.setQuestion(event.target.value)}
              placeholder="Ask something the chapter can answer from its sources."
            />
            <button className="button ghost" disabled={props.asking || !props.question.trim()}>
              {props.asking ? "Thinking" : "Ask"}
            </button>
            {props.reply && <p className="reply">{props.reply}</p>}
          </>
        ) : (
          <p>
            Set <code>LLM_API_KEY</code> to ask here. Kit on the hosted workspace answers from your materials at{" "}
            <a href={PRODUCT_URL}>lynote.ai/learning-path</a>.
          </p>
        )}
      </form>
    </section>
  );
}
