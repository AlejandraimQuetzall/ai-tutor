import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "./api";
import { CourseSummary, PRODUCT_URL, ShelfItem } from "./types";

export function Shelf() {
  const navigate = useNavigate();
  const [items, setItems] = useState<ShelfItem[]>([]);
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [configured, setConfigured] = useState(true);
  const [goal, setGoal] = useState("");
  const [depth, setDepth] = useState<"guided" | "overview">("guided");
  const [link, setLink] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [dragging, setDragging] = useState(false);

  async function refresh() {
    const [health, shelf, history] = await Promise.all([
      api<{ llm_configured: boolean }>("/api/health"),
      api<{ items: ShelfItem[] }>("/api/shelf"),
      api<{ courses: CourseSummary[] }>("/api/courses"),
    ]);
    setConfigured(health.llm_configured);
    setItems(shelf.items);
    setCourses(history.courses);
  }

  useEffect(() => {
    void refresh().catch((err: unknown) => setError(err instanceof Error ? err.message : "Could not reach the API."));
  }, []);

  async function run(label: string, work: () => Promise<void>) {
    setError("");
    setBusy(label);
    try {
      await work();
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy("");
    }
  }

  async function upload(files: FileList | File[]) {
    const list = [...files];
    if (!list.length) return;
    const body = new FormData();
    list.forEach((file) => body.append("files", file));
    await run("Reading files", async () => {
      await api("/api/shelf/upload", { method: "POST", body });
    });
  }

  return (
    <div className="page">
      <section className="hero">
        <p className="eyebrow">AI Learning Path Generator</p>
        <h1>Build a chapter path from your own materials.</h1>
        <p className="lede">
          Add notes, slides, or a link. This open edition turns them into ordered chapters, explanations that
          quote the source, and a short quiz. The hosted workspace lives on{" "}
          <a href={PRODUCT_URL}>lynote.ai/learning-path</a>.
        </p>
      </section>

      {!configured && (
        <p className="banner">
          No model key is configured. The sample path still runs. To generate from your files, set{" "}
          <code>LLM_API_KEY</code> in <code>.env</code> and start the server again.
        </p>
      )}
      {error && <p className="banner error">{error}</p>}

      <section className={`shelf ${dragging ? "dragging" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          if (event.dataTransfer.files.length) void upload(event.dataTransfer.files);
        }}
      >
        <div className="shelf-head">
          <div>
            <h2>Build your course shelf</h2>
            <p>Drop the notes, slides, and links for one course. Each becomes a card, then one learning path.</p>
          </div>
          <div className="row">
            {items.length > 0 && (
              <label className="button ghost">
                Add files
                <input
                  type="file"
                  multiple
                  hidden
                  onChange={(event) => {
                    if (event.target.files) void upload(event.target.files);
                    event.target.value = "";
                  }}
                />
              </label>
            )}
            <span className="count">{items.length} / 20 sources</span>
          </div>
        </div>

        {items.length === 0 ? (
          <div className="empty">
            <div className="empty-copy">
              <h3>Add at least one source to start</h3>
              <p>PDF, Word, PowerPoint, Excel, text, Markdown, HTML, CSV, subtitles, or a public web page.</p>
              <div className="row">
                <label className="button">
                  Browse files
                  <input
                    type="file"
                    multiple
                    hidden
                    onChange={(event) => {
                      if (event.target.files) void upload(event.target.files);
                      event.target.value = "";
                    }}
                  />
                </label>
                <button
                  className="button ghost"
                  disabled={!!busy}
                  onClick={() =>
                    void run("Opening sample", async () => {
                      const created = await api<{ id: string }>("/api/courses/sample", { method: "POST" });
                      navigate(`/course/${created.id}`);
                    })
                  }
                >
                  Try 3 samples
                </button>
              </div>
            </div>
            <div className="preview-cards" aria-hidden="true">
              <article className="file-card pdf">PDF</article>
              <article className="file-card ppt">PPT</article>
              <article className="file-card link">Link</article>
            </div>
          </div>
        ) : (
          <ul className="cards">
            {items.map((item) => (
              <li key={item.id} className={`source-card kind-${item.kind}`}>
                <span className="kind">{item.kind}</span>
                <strong>{item.name}</strong>
                <button className="icon-button" onClick={() => void run("Removing", () => api(`/api/shelf/${item.id}`, { method: "DELETE" }))}>
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}

        <form
          className="link-row"
          onSubmit={(event) => {
            event.preventDefault();
            const url = link.trim();
            if (!url) return;
            void run("Fetching link", async () => {
              await api("/api/shelf/link", { method: "POST", body: JSON.stringify({ url }) });
              setLink("");
            });
          }}
        >
          <input
            aria-label="Paste a link"
            placeholder="Paste a link"
            value={link}
            onChange={(event) => setLink(event.target.value)}
          />
          <button className="button ghost" disabled={!link.trim() || !!busy}>
            Add
          </button>
        </form>

        <div className="options">
          <label>
            Goal <span>optional</span>
            <input
              value={goal}
              maxLength={400}
              placeholder="Exam revision, a lecture week, a skill you want"
              onChange={(event) => setGoal(event.target.value)}
            />
          </label>
          <div className="depth" role="group" aria-label="Lesson depth">
            <button className={depth === "guided" ? "on" : ""} type="button" onClick={() => setDepth("guided")}>
              Guided
            </button>
            <button className={depth === "overview" ? "on" : ""} type="button" onClick={() => setDepth("overview")}>
              Overview
            </button>
          </div>
        </div>

        <div className="generate-row">
          <p>{busy || (items.length ? "Ready to arrange a path." : "Add at least one source to start.")}</p>
          <button
            className="button"
            disabled={!items.length || !!busy}
            onClick={() =>
              void run("Starting", async () => {
                const created = await api<{ id: string }>("/api/courses", {
                  method: "POST",
                  body: JSON.stringify({ item_ids: items.map((item) => item.id), goal, depth }),
                });
                navigate(`/course/${created.id}`);
              })
            }
          >
            Generate Learning Path
          </button>
        </div>
      </section>

      <section className="steps">
        <h2>Three steps</h2>
        <ol>
          <li>
            <strong>Add materials</strong>
            <span>Files and public links land on the shelf as source cards.</span>
          </li>
          <li>
            <strong>Generate the path</strong>
            <span>Concepts have to quote the source before they become a chapter.</span>
          </li>
          <li>
            <strong>Start learning</strong>
            <span>Read the chapter, check the citation, then take the quiz.</span>
          </li>
        </ol>
      </section>

      {courses.length > 0 && (
        <section className="history">
          <h2>Your paths</h2>
          <ul>
            {courses.map((course) => (
              <li key={course.id}>
                <button className="history-item" onClick={() => navigate(`/course/${course.id}`)}>
                  <strong>{course.title}</strong>
                  <span>{course.status === "ready" ? "Ready to study" : course.status}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <footer className="foot">
        Open edition of the Lynote learning path. Lecture video, image reading, and the shared study workspace
        are on <a href={PRODUCT_URL}>lynote.ai/learning-path</a>.
      </footer>
    </div>
  );
}
