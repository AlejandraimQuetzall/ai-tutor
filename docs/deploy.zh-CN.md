# 部署

[English](deploy.md) · [打开 Lynote 正式版](https://lynote.ai/learning-path?utm_source=github&utm_medium=docs&utm_campaign=learning_path_oss)

这份说明从一份新克隆的仓库写到「页面能打开、示例课能学、配上自己的密钥后能用自己的文件生成路径」。书架、生成和学习页跑在你自己的机器上。模型密钥用你在模型服务商那里创建的 OpenAI 兼容密钥。仓库里没有 Lynote 的密钥。

有两种跑法：

| | Docker | 本地两个进程 |
| --- | --- | --- |
| 需要 | Docker Desktop，或带 Compose v2 的 Docker Engine | Python 3.11+ 和 Node.js 20+ |
| 打开 | <http://localhost:8080> | <http://localhost:5173> |
| 接口 | 同一个地址，端口 8080 | <http://127.0.0.1:8000> |
| 适合 | 部署后一直开着 | 改界面或改接口 |

示例课不调用模型。用自己的文件生成、失败后重试、音视频转写、以及章节提问，都需要密钥。

## 1. 密钥不要进仓库

1. 复制示例文件。不要直接把 `.env.example` 改名后提交。

   ```bash
   cp .env.example .env
   ```

   ```powershell
   Copy-Item .env.example .env
   ```

2. 打开仓库根目录的 `.env`，把 `LLM_API_KEY` 写成你自己的密钥。只想看示例课时，这一行留空。
3. 确认 Git 看不到它：

   ```bash
   git status --short
   ```

   列表里不能出现 `.env`。它已经写在 `.gitignore` 里。`.env.example` 会留在仓库中，密钥那一行为空。
4. 不要把密钥写进 Pull Request、截图、日志或 README。下面的健康检查可以公开：它只说明有没有读到密钥，不会把密钥打出来。
5. 密钥一旦提交或粘贴出去，就到服务商后台作废并新建一把。删掉那次提交并不能收回已经发出去的密钥。

服务从仓库根目录读取 `.env`。进程环境里已经存在的变量优先于文件。如果 shell 里导出了空的 `LLM_API_KEY`，文件里的密钥不会生效。先取消这个环境变量，或把它设成真正的密钥，再启动。

密钥只放在发往 `LLM_BASE_URL` 的 `Authorization: Bearer …` 头里。它不会写入 `learning-path.db`，不会出现在 `/api/health`，也不会写进应用日志。

## 2. Docker

在仓库根目录，确认 `.env` 已经存在：

```bash
docker compose up --build
```

Compose 读取 `.env`，并把容器的 8080 端口发布到本机。数据库在宿主机的 `./data/learning-path.db`（容器内是 `/app/data`）。打开 <http://localhost:8080>。

改完 `.env` 后，正在跑的容器不会自己重读。停掉再启动：

```bash
docker compose up --build
```

没有 `.env` 时，`docker compose` 会因为找不到 env 文件失败。先复制 `.env.example`。密钥留空也是一份合法的 `.env`。

## 3. 本地接口和界面

开两个终端。下面的命令都从仓库根目录开始，再按提示进入子目录。

### 接口

Windows PowerShell：

```powershell
cd server
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
$env:PYTHONPATH = "."
.\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000
```

macOS 或 Linux：

```bash
cd server
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

接口监听 8000，是因为命令里写了 `--port 8000`。`.env` 里的 `DATA_DIR=./data` 相对的是这个工作目录，所以数据库在 `server/data/learning-path.db`。仓库根目录的 `.env` 仍会被读到。

### 界面

```bash
cd web
npm install
npm run dev
```

打开 <http://localhost:5173>。Vite 把 `/api` 转到 `127.0.0.1:8000`。本地开发用 5173 这个地址。只开 8000 时，除非已经把前端构建进 `server/app/static`，否则看不到书架。

改完 `.env` 要停掉 uvicorn 再启动。

## 4. 确认密钥已被读到

Docker：

```bash
curl http://127.0.0.1:8080/api/health
```

本地接口：

```bash
curl http://127.0.0.1:8000/api/health
```

已配置密钥：

```json
{"status":"ok","llm_configured":true}
```

没有密钥：

```json
{"status":"ok","llm_configured":false}
```

返回的 JSON 里不能出现密钥本身。书架上 `llm_configured: false` 对应那条「没有配置模型密钥」的提示。示例课按钮仍然可用。

## 5. 把学习闭环走通

1. 打开页面，点 **Try 3 samples**。应进入 “Memory: encoding, storage, and retrieval”，Encoding 可学，Storage 锁定。
2. 阅读讲解。紫色引用是 `examples/memory` 里的原句。
3. 打开 **Quick check**，答完两题，点 **Continue**。Storage 解锁。Storage 的小测做完之前，Retrieval 保持锁定。
4. 要用自己的材料生成：写好密钥并重启，然后加入文本、Markdown、PDF、`.docx` 或 `.pptx`。选择 **Guided** 或 **Overview**，再点 **Generate Learning Path**。
5. 页面会经过 Read、Extract concepts、Arrange chapters、Write lessons。一份短笔记通常是几次模型调用。生成结果写在第 2 步或第 3 步所说的 SQLite 文件里。

Guided 的章节比 Overview 长。可选的学习目标只改变侧重点。两者都不能补进上传文本里没有的事实。规则见 [pipeline.md](pipeline.md)。

## 6. 接到你自己的模型服务

`LLM_BASE_URL` 是根地址，服务会在后面接上 `/chat/completions`。官方 OpenAI 保持默认即可：

```text
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

其他 OpenAI 兼容服务同样写法。OpenRouter 的例子：

```text
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openai/gpt-4o-mini
```

`LLM_API_KEY` 填该服务商给你的密钥，不要把这一行提交到 Git。

不要把 `/chat/completions` 写进 `LLM_BASE_URL`，程序会自己加。不接受 OpenAI chat-completions JSON 的服务无法使用。密钥在该服务商的控制台创建。这里没有可以抄的 Lynote 密钥。

上传音频或视频时，请求发到 `{LLM_BASE_URL}/audio/transcriptions`，模型名用 `LLM_TRANSCRIBE_MODEL`。对方没有这个路径时，上传会失败，改传 `.srt` 或 `.vtt`。

变量的完整表在 [configuration.md](configuration.md)。

## 7. 可以上传什么

| 输入 | 结果 |
| --- | --- |
| `.pdf`、`.docx`、`.pptx`、`.xlsx`、`.txt`、`.md`、`.html`、`.csv` | 在本地抽出文本。没有文字层的扫描版 PDF 会被拒绝。 |
| `.srt`、`.vtt` | 直接读字幕，不需要转写密钥。 |
| 公网 `http` / `https` 页面 | 抽出正文。内网、本机和链路本地地址会被拒绝。 |
| 带公开字幕的 YouTube 链接 | 抽出字幕。没有公开字幕则拒绝。 |
| `.mp3`、`.wav`、`.m4a`、`.mp4`、`.webm` | 发给你的转写接口。需要 `LLM_API_KEY`。 |
| `.doc`、`.ppt` | 另存为 `.docx` 或 `.pptx` 再上传。 |
| 图片 | 这一版不做图片 OCR。 |

限制：书架最多 20 份材料，单文件 20 MB，每份大约保存 20 万字符，一门课大约把 5.6 万字符送给模型。更长的材料会被抽样，课程上会写出这条提示。最多保留 40 个可回溯知识点和 8 章。

## 8. 生成停住时

失败课程的进度页上有原因。部署时常见的是这些：

| 提示 | 处理 |
| --- | --- |
| Set `LLM_API_KEY` to generate a path from your own files | 健康检查是 `llm_configured: false`。改仓库根目录的 `.env`，确认 shell 没有导出空密钥，然后重启。 |
| The model rejected `LLM_API_KEY` | 服务商返回 401 或 403。密钥、根地址或模型名和该账号不一致。 |
| The model endpoint could not be reached | `LLM_BASE_URL` 不对，或这台机器访问不到它。 |
| The chat completions path was not found | 根地址里已经写了 `/chat/completions`，或对方用了别的路径。 |
| The model endpoint is rate limiting requests | 等一会儿，在失败课程上点 **Try again**。 |
| Not enough learnable content was grounded in the sources | 正文太少，或模型给出的引文对不上原文。换一段有完整句子的短文。 |
| No readable text was found | PDF 是扫描件，或幻灯片里没有文字。 |
| Private and local links are not fetched | 改用公网 `https` 地址。 |
| No public captions were found for that video | 改传 `.srt` 或 `.vtt`，或在 [Lynote](https://lynote.ai/learning-path?utm_source=github&utm_medium=docs&utm_campaign=learning_path_oss) 打开这节讲座。 |

**Try again** 会把这门课的流水线再跑一遍。示例课已经完成，没有重试。

## 9. 数据和清空

课程、笔记和作答都在 `learning-path.db`。上传的原始文件只在内存里解析，不落盘。要清空本机课程，先停服务，再删这个数据库文件。

## 10. 测试

测试不需要密钥，也不会请求模型：

```bash
cd server
python -m pip install -r requirements.txt
python -m pytest
```

Windows 上，第 3 步的虚拟环境已经建好时：

```powershell
cd server
.\.venv\Scripts\python -m pytest
```

## 部署核对

- 仓库根目录有 `.env`，`git status` 里没有它。
- `/api/health` 按你的意图返回 `llm_configured` 为 true 或 false，正文里没有密钥。
- **Try 3 samples** 能打开记忆课程，后面的章节是锁定的。
- 配上密钥后，一份短文本能走完 Read → Extract → Arrange → Write，讲解里的引文来自这份文本。
- `learning-path.db` 留在 `data/` 下，没有被提交。
