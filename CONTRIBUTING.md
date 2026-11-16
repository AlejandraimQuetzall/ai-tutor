# Contributing

Issues and pull requests are welcome for the open edition: parsers, deployment, the study UI, docs, and the sample course.

The hosted product on [Lynote](https://lynote.ai/learning-path) keeps accounts, billing, and the production prompts. Those do not belong in this repository.

## Before you open a pull request

1. Copy `.env.example` to `.env` only on your machine. Do not commit `.env`, a database, `.venv`, or `__pycache__`.
2. From `server/`, install `requirements.txt` and run `python -m pytest`.
3. From `web/`, run `npm ci` and `npm run build` when you change the UI.
4. Keep a sample quote as a continuous excerpt of `examples/memory/`. `test_sample_quotes_are_verbatim` fails when a quote is no longer in its note.

## Good pull requests

- A new document type, with a locator (page, slide, cue, or section) and a test.
- A deploy fix for Windows, macOS, Linux, or Docker.
- Clearer docs, including a translation that stays in step with the English page.

## 中文

欢迎为开源版提 issue 和 pull request：解析器、部署、学习界面、文档、示例课。

主站上的账号、扣费和生产提示词留在 Lynote，不进这个仓库。提交前跑 `server/` 下的 `python -m pytest`。改了界面再在 `web/` 下执行 `npm run build`。示例课的引文必须仍是 `examples/memory/` 里的连续原文。
