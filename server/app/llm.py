"""OpenAI-compatible chat client. The key stays in the Authorization header."""

from __future__ import annotations

import json
import re

import httpx

from .config import Settings


class LLMError(Exception):
    pass


def parse_json_object(raw: str) -> dict:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise LLMError("The model did not return JSON.")
        value = json.loads(text[start : end + 1])
    if not isinstance(value, dict):
        raise LLMError("The model did not return a JSON object.")
    return value


async def chat_json(settings: Settings, system: str, user: str, max_tokens: int = 2500) -> dict:
    raw = await chat_text(settings, system, user, max_tokens=max_tokens, json_mode=True)
    try:
        return parse_json_object(raw)
    except (json.JSONDecodeError, LLMError):
        raw = await chat_text(
            settings,
            system,
            user + "\n\nReturn the JSON object only.",
            max_tokens=max_tokens,
            json_mode=False,
        )
        try:
            return parse_json_object(raw)
        except json.JSONDecodeError as exc:
            raise LLMError("The model did not return JSON.") from exc


async def chat_text(
    settings: Settings,
    system: str,
    user: str,
    max_tokens: int = 800,
    json_mode: bool = False,
) -> str:
    if not settings.api_key:
        raise LLMError("Set LLM_API_KEY to generate a path from your own files.")
    payload: dict = {
        "model": settings.model,
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user[:48000]},
        ],
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    url = f"{settings.base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.api_key}"}
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code >= 400 and json_mode:
                payload.pop("response_format", None)
                response = await client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        raise LLMError("The model endpoint could not be reached. Check LLM_BASE_URL.") from exc
    if response.status_code >= 400:
        raise LLMError(_public_http_error(response.status_code))
    try:
        body = response.json()
        content = body["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise LLMError("The model endpoint returned an unexpected response.") from exc
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    if not isinstance(content, str) or not content.strip():
        raise LLMError("The model returned an empty response.")
    return content


async def transcribe(settings: Settings, filename: str, data: bytes, content_type: str) -> str:
    if not settings.api_key:
        raise LLMError("Set LLM_API_KEY to transcribe audio or video.")
    url = f"{settings.base_url}/audio/transcriptions"
    headers = {"Authorization": f"Bearer {settings.api_key}"}
    files = {"file": (filename or "audio.mp3", data, content_type or "application/octet-stream")}
    form = {"model": settings.transcribe_model}
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(url, headers=headers, data=form, files=files)
    except httpx.HTTPError as exc:
        raise LLMError("The transcription endpoint could not be reached.") from exc
    if response.status_code >= 400:
        raise LLMError(
            "This endpoint did not transcribe the file. Upload a .srt or .vtt transcript, "
            "or use a base URL that supports audio transcriptions."
        )
    try:
        body = response.json()
    except ValueError as exc:
        raise LLMError("The transcription endpoint returned an unexpected response.") from exc
    text = body.get("text") if isinstance(body, dict) else ""
    if not text or not str(text).strip():
        raise LLMError("The transcription was empty.")
    return str(text)


def _public_http_error(status: int) -> str:
    if status in {401, 403}:
        return "The model rejected LLM_API_KEY. Check the key and the base URL."
    if status == 429:
        return "The model endpoint is rate limiting requests. Wait a moment and generate again."
    if status == 404:
        return "The chat completions path was not found. Check LLM_BASE_URL."
    return f"The model endpoint returned HTTP {status}."
