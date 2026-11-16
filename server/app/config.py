"""Environment configuration. Keys are read at call time and never logged."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_dotenv() -> None:
    """Load .env without overriding variables already set in the process."""
    candidates = [
        repo_root() / ".env",
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[1] / ".env",
    ]
    seen: set[Path] = set()
    for path in candidates:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in seen or not resolved.is_file():
            continue
        seen.add(resolved)
        for raw in resolved.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    model: str
    transcribe_model: str
    data_dir: Path
    port: int

    @property
    def llm_configured(self) -> bool:
        return bool(self.api_key)


def settings() -> Settings:
    load_dotenv()
    data_dir = Path(os.environ.get("DATA_DIR", "./data"))
    if not data_dir.is_absolute():
        data_dir = (Path.cwd() / data_dir).resolve()
    return Settings(
        api_key=os.environ.get("LLM_API_KEY", "").strip(),
        base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/"),
        model=os.environ.get("LLM_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini",
        transcribe_model=os.environ.get("LLM_TRANSCRIBE_MODEL", "whisper-1").strip() or "whisper-1",
        data_dir=data_dir,
        port=int(os.environ.get("PORT", "8080") or "8080"),
    )
