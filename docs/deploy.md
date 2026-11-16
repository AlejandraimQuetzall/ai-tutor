# Deploy

[简体中文](deploy.zh-CN.md) · [Configuration reference](configuration.md) · [Hosted Lynote](https://lynote.ai/learning-path?utm_source=github&utm_medium=docs&utm_campaign=learning_path_oss)

This page is the path from a fresh clone to a running learning path. One machine runs the shelf, the generator, and the study workspace. You bring an OpenAI-compatible chat key. The repository does not contain one.

Two ways to run it:

| | Docker | Local processes |
| --- | --- | --- |
| You need | Docker Desktop or Docker Engine with Compose v2 | Python 3.11+ and Node.js 20+ |
| Open | <http://localhost:8080> | <http://localhost:5173> |
| API | same origin, port 8080 | <http://127.0.0.1:8000> |
| When to use | A deploy you leave running | Changing the UI or the API |

The sample course does not call a model. Generate, retry, audio transcription, and Ask do.

## 1. Keep your key out of the repository

1. Copy the example file. Do not rename `.env.example` itself.

   ```bash
   cp .env.example .env
   ```

   ```powershell
   Copy-Item .env.example .env
   ```

2. Open `.env` and set `LLM_API_KEY` to a key you created at your model provider. Leave the line empty if you only want the sample course.
3. Confirm Git does not see it:

   ```bash
   git status --short
   ```

   `.env` must not appear. It is listed in `.gitignore`. `.env.example` stays in Git with an empty key.
4. Do not put the key in a pull request, a screenshot, a log paste, or the README. The health check below is the check to share: it says whether a key is loaded and does not print the key.
5. If a key was ever committed or pasted, revoke it at the provider and create a new one. Deleting the commit is not enough.

The server reads `.env` from the repository root. A variable that is already set in the process environment wins over the file. An empty `LLM_API_KEY` exported in the shell therefore hides the value in `.env`. Unset that shell variable, or set it to the real key, then start again.

The key is sent only as `Authorization: Bearer …` to `LLM_BASE_URL`. It is not written to `learning-path.db`, to `/api/health`, or to application logs.

## 2. Docker

From the repository root, after `.env` exists:

```bash
docker compose up --build
```

Compose reads `.env` and publishes port 8080. The database file is `./data/learning-path.db` on the host (`/app/data` inside the container). Open <http://localhost:8080>.

Changing `.env` does not affect an already running container. Stop it and start again:

```bash
docker compose up --build
```

`docker compose` fails with a missing env file when `.env` was not created. Copy `.env.example` first. An empty key is a valid file.

## 3. Local API and UI

Use two terminals. Both commands assume the repository root as the starting point, then `cd` as shown.

### API

Windows PowerShell:

```powershell
cd server
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
$env:PYTHONPATH = "."
.\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000
```

macOS or Linux:

```bash
cd server
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The API listens on port 8000 because that is the `--port` flag. `DATA_DIR=./data` is resolved from this working directory, so the database is `server/data/learning-path.db`. The root `.env` is still loaded.

### UI

```bash
cd web
npm install
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` to `127.0.0.1:8000`. The UI on 5173 is the one to use for local development. Port 8000 alone is the API and does not serve the shelf unless you have built the static files into `server/app/static`.

Stop the process and start uvicorn again after any `.env` edit.

## 4. Check that the key is loaded

Docker:

```bash
curl http://127.0.0.1:8080/api/health
```

Local API:

```bash
curl http://127.0.0.1:8000/api/health
```

A configured key:

```json
{"status":"ok","llm_configured":true}
```

No key:

```json
{"status":"ok","llm_configured":false}
```

The JSON must not contain the key string. On the shelf, `llm_configured: false` is the banner that says no model key is configured. The sample button still works.

## 5. Confirm the product loop

1. Open the UI and choose **Try 3 samples**. You should land on “Memory: encoding, storage, and retrieval” with Encoding open and Storage locked.
2. Read the lesson. The purple quotes are sentences from `examples/memory`.
3. Open **Quick check**, answer both questions, and choose **Continue**. Storage unlocks. Retrieval stays locked until Storage’s quiz is finished.
4. To generate from your own material, set a key, restart, and add a text, Markdown, PDF, `.docx`, or `.pptx` file. Choose **Guided** or **Overview**, then **Generate Learning Path**.
5. The page moves through Read, Extract concepts, Arrange chapters, and Write lessons. A short note usually finishes in a few model calls. The finished course is stored in the SQLite file from step 2 or 3.

A guided chapter is longer than an overview chapter. The optional goal changes emphasis. Neither one may add facts that are not in the uploaded text. The rules are in [pipeline.md](pipeline.md).

## 6. Point the app at your provider

`LLM_BASE_URL` is the root the server joins with `/chat/completions`. For the official OpenAI API leave it as:

```text
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

Another OpenAI-compatible root looks the same. Example for OpenRouter:

```text
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openai/gpt-4o-mini
```

Set `LLM_API_KEY` to the key from that provider. Leave the value out of Git.

Do not put `/chat/completions` in `LLM_BASE_URL`. The app adds that path. A provider that does not accept the OpenAI chat-completions JSON will not work. Create the key in that provider’s console. There is no Lynote key to copy.

Audio and video uploads call `{LLM_BASE_URL}/audio/transcriptions` with `LLM_TRANSCRIBE_MODEL`. If that route is missing, the upload fails and a `.srt` or `.vtt` file is the replacement.

## 7. What you can upload

| Input | Result |
| --- | --- |
| `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.txt`, `.md`, `.html`, `.csv` | Text is extracted locally. A scanned PDF with no text layer is rejected. |
| `.srt`, `.vtt` | Caption text, with no transcription key. |
| Public `http`/`https` page | Article text. Private, loopback, and link-local addresses are refused. |
| YouTube link with public captions | Caption text. A video with no public captions is refused. |
| `.mp3`, `.wav`, `.m4a`, `.mp4`, `.webm` | Sent to your transcription endpoint. Needs `LLM_API_KEY`. |
| `.doc`, `.ppt` | Save as `.docx` or `.pptx` and upload that. |
| Images | This edition does not OCR images. |

Limits: 20 sources on the shelf, 20 MB per file, about 200,000 stored characters per source, and about 56,000 characters sent to the model for one course. A longer source is sampled, and the course shows that warning. At most 40 grounded points and 8 chapters are kept.

## 8. When generation stops

The failed course shows the message on the progress page. These are the ones deployers hit:

| Message | What to do |
| --- | --- |
| Set `LLM_API_KEY` to generate a path from your own files | The health check is `llm_configured: false`. Edit the root `.env`, make sure the shell is not exporting an empty key, and restart. |
| The model rejected `LLM_API_KEY` | The provider returned 401 or 403. The key, the base URL, or the model name does not match that account. |
| The model endpoint could not be reached | `LLM_BASE_URL` is wrong or the host cannot open it. |
| The chat completions path was not found | The base URL already includes `/chat/completions`, or the provider uses a different path. |
| The model endpoint is rate limiting requests | Wait and choose **Try again** on the failed course. |
| Not enough learnable content was grounded in the sources | The file has too little prose, or the model’s quotes did not match the text. Try a shorter passage with real sentences. |
| No readable text was found | The PDF is a scan, or the slides have no text. |
| Private and local links are not fetched | Use a public `https` URL. |
| No public captions were found for that video | Upload a `.srt` or `.vtt`, or open the lecture on [Lynote](https://lynote.ai/learning-path?utm_source=github&utm_medium=docs&utm_campaign=learning_path_oss). |

**Try again** reruns the pipeline for that course. The sample course has no retry because it is already complete.

## 9. Data and reset

Courses, notes, and quiz answers live in `learning-path.db`. Uploaded binaries are parsed in memory and are not stored. To wipe the local library, stop the server and delete that database file.

## 10. Tests

Tests do not need a key and do not call a model:

```bash
cd server
python -m pip install -r requirements.txt
python -m pytest
```

Windows, after the venv from step 3 exists:

```powershell
cd server
.\.venv\Scripts\python -m pytest
```

## Deploy checklist

- `.env` is present at the repository root and `git status` does not list it.
- `/api/health` returns `llm_configured` true or false on purpose, and the body does not contain the key.
- **Try 3 samples** opens the memory course with later chapters locked.
- With a key, a short text file finishes Read → Extract → Arrange → Write and opens a lesson whose quotes are from that file.
- `learning-path.db` stays under `data/` and is not committed.
