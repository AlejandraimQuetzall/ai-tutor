# Configuration

Deploy steps, including where `.env` is read and how to restart after an edit, are in [deploy.md](deploy.md) ([中文](deploy.zh-CN.md)).

Copy `.env.example` to `.env` in the repository root. The server reads that file without overriding variables that are already set in the process. The key is used as a bearer token and is not written to the database, the health check, or the logs.

| Variable | Required | Purpose |
| --- | --- | --- |
| `LLM_API_KEY` | For your own files | Sent only to `LLM_BASE_URL`. Leave it empty to run the sample path. |
| `LLM_BASE_URL` | No | OpenAI-compatible root. The app calls `{LLM_BASE_URL}/chat/completions`. Default `https://api.openai.com/v1`. Do not include `/chat/completions` in this value. |
| `LLM_MODEL` | No | Chat model for extract, arrange, lessons, and Ask. Default `gpt-4o-mini`. |
| `LLM_TRANSCRIBE_MODEL` | No | Model for `POST {base}/audio/transcriptions` when you upload audio or video. Default `whisper-1`. |
| `DATA_DIR` | No | Directory for `learning-path.db`. A relative path is resolved from the process working directory. Default `./data`. Docker Compose sets this to `/app/data` and mounts the host `./data` directory there. |

The listen port is not an environment variable. Docker Compose publishes container port 8080. The local uvicorn command in the deploy guide uses `--port 8000`, and the Vite dev server proxies `/api` to that port.

## Endpoints that accept the key

Chat calls go to `{LLM_BASE_URL}/chat/completions`. Gateways that reject JSON mode are retried once without `response_format`. Transcription goes to `{LLM_BASE_URL}/audio/transcriptions`. If that route is missing, upload a `.srt` or `.vtt` file, or open the lecture on [Lynote](https://lynote.ai/learning-path?utm_source=github&utm_medium=docs&utm_campaign=learning_path_oss).

After editing `.env`, start the process again. A container or uvicorn that is already running keeps the previous environment.

## Limits in this edition

- 20 sources on the shelf
- 20 MB per upload
- about 200,000 characters stored per source
- about 56,000 characters sent through the model for one course, sampled when the source is longer
- 40 grounded points and 8 chapters

## Security

- Do not commit `.env`.
- A key already exported in the shell overrides `.env`. An empty exported `LLM_API_KEY` hides the file.
- The link fetcher allows `http` and `https` only, and it refuses loopback, private, link-local, and reserved addresses before the request.
- Quiz answers, explanations, and later chapter lessons are omitted until the learner has reached them.
- `GET /api/health` reports `llm_configured` and does not echo the key.
