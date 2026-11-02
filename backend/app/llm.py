import json
from typing import Callable

import httpx

from .config import settings


class LLMError(RuntimeError):
    pass


def _clean(text: str) -> str:
    """Drop chatty lead-ins like 'Here is a summary of ...:'."""
    lines = text.strip().splitlines()
    if lines and lines[0].lower().startswith(("here is", "here's", "sure")) and lines[0].rstrip().endswith(":"):
        lines = lines[1:]
    return "\n".join(lines).strip()


def chat(prompt: str, system: str = "", schema: dict | None = None, temperature: float = 0.2) -> str:
    payload: dict = {
        "model": settings.model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system or "You are a precise research-paper analyst. Use only the provided text. If something is not stated, say 'Not stated'."},
            {"role": "user", "content": prompt},
        ],
        "options": {"num_ctx": settings.num_ctx, "temperature": temperature},
    }
    if schema:
        payload["format"] = schema
    try:
        r = httpx.post(f"{settings.ollama_url}/api/chat", json=payload, timeout=600)
        r.raise_for_status()
    except httpx.HTTPError as exc:
        raise LLMError(f"Could not reach the language model: {exc}") from exc
    return r.json()["message"]["content"] if schema else _clean(r.json()["message"]["content"])


def chat_json(prompt: str, schema: dict, retries: int = 1) -> dict:
    last: Exception | None = None
    for _ in range(retries + 1):
        raw = chat(prompt, schema=schema, temperature=0.1)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            last = exc
    raise LLMError(f"Model returned invalid JSON: {last}")


def chunk_text(text: str, size: int | None = None) -> list[str]:
    """Split text into roughly size-char chunks on sentence-ish boundaries."""
    size = size or settings.chunk_chars
    chunks, cur = [], ""
    for sentence in text.replace("\n", " ").split(". "):
        piece = sentence + ". "
        if len(cur) + len(piece) > size and cur:
            chunks.append(cur)
            cur = ""
        cur += piece
    if cur.strip():
        chunks.append(cur)
    return chunks


def calls_for(text: str) -> int:
    """Number of model calls summarize_text will make for this text."""
    n = len(chunk_text(text))
    return 1 if n == 1 else n + 1


def summarize_text(
    text: str,
    instruction: str = "Summarize the following text in 3-5 sentences.",
    tick: Callable[[], None] | None = None,
) -> str:
    """Map-reduce summary that fits small context windows. `tick` is called after each model call."""
    tick = tick or (lambda: None)
    chunks = chunk_text(text)
    if len(chunks) == 1:
        out = chat(f"{instruction}\n\n{chunks[0]}")
        tick()
        return out
    parts = []
    for c in chunks:
        parts.append(chat(f"Summarize this excerpt in 2-3 sentences.\n\n{c}"))
        tick()
    out = chat(f"{instruction}\n\nExcerpt summaries:\n" + "\n".join(f"- {p}" for p in parts))
    tick()
    return out


def clip(text: str, chars: int | None = None) -> str:
    chars = chars or settings.chunk_chars
    return text if len(text) <= chars else text[:chars]
