"""Ask a vision model about images or a video through OpenRouter (stdlib only)."""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_MODEL = "elorian/glimpse"
API = "https://openrouter.ai/api/v1/chat/completions"
VIDEO_EXT = {".mp4", ".webm", ".mov", ".mkv"}

REVIEW_PROMPT = """You are the eyes of a coding agent that cannot see. Look at what it built and report what a
careful human reviewer would notice, as if you were about to ship it.

Check: layout breaks, elements overlapping or cut off, text overflowing its box or truncated, horizontal scroll or
content leaving the viewport, misalignment between siblings, broken or missing images/icons, unreadable contrast,
wrong or inconsistent colours, typos and placeholder text (lorem ipsum, TODO, undefined, NaN, [object Object]),
empty states that look broken, and anything that does not match the stated intent. For video or frame sheets also:
flicker, jumps, frames out of place, timing.

Only report what you can actually see. Quote visible text exactly. Say where (region, element, text near it,
frame/timestamp). Do not invent problems to look thorough: a clean result is a valid answer.

Answer with JSON only, no prose around it:
{"verdict": "ok" | "issues",
 "summary": "<one sentence>",
 "issues": [{"severity": "blocker" | "major" | "minor", "where": "...", "what": "...", "fix": "..."}],
 "observations": ["<neutral facts about what is shown, max 5>"]}"""


def _data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def build_prompt(intent: str | None = None, ask: str | None = None, context: str | None = None) -> str:
    parts = [REVIEW_PROMPT]
    if intent:
        parts.append(f"Intent (what this is supposed to be): {intent}")
    if context:
        parts.append(f"Measured facts from the page (trust these):\n{context}")
    if ask:
        parts.append(f"Also answer this specific question inside \"summary\": {ask}")
    return "\n\n".join(parts)


def parse_json(text: str) -> dict | None:
    """Pull the first JSON object out of a model reply (tolerates ```json fences and prose)."""
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def look(files: list[str | Path], prompt: str, model: str = DEFAULT_MODEL, max_tokens: int = 24000,
         timeout: int = 420, temperature: float = 0.1, effort: str | None = None) -> dict:
    """effort: reasoning effort (low/medium/high) for reasoning models; their thinking counts against max_tokens."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set (only needed for --model / review / look)")
    content: list[dict] = [{"type": "text", "text": prompt}]
    for f in map(Path, files):
        if f.suffix.lower() in VIDEO_EXT:
            content.append({"type": "video_url", "video_url": {"url": _data_url(f)}})
        else:
            content.append({"type": "text", "text": f"[image: {f.name}]"})
            content.append({"type": "image_url", "image_url": {"url": _data_url(f)}})
    body = {"model": model, "messages": [{"role": "user", "content": content}],
            "max_tokens": max_tokens, "temperature": temperature, "usage": {"include": True},
            "response_format": {"type": "json_object"}}
    if effort:
        body["reasoning"] = {"effort": effort}
    req = urllib.request.Request(API, data=json.dumps(body).encode(), headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json",
        "X-Title": "eyeproof"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors="replace")
        files = list(map(Path, files))
        videos = [f for f in files if f.suffix.lower() in VIDEO_EXT]
        if "mixed modalities" in err and videos and len(videos) < len(files):
            # some backends (Glimpse on vLLM) take a video or images, never both in one request
            note = "\n\n(Only the video is attached; the contact sheet was left out because this model takes video alone.)"
            return look(videos, prompt + note, model, max_tokens, timeout, temperature, effort)
        raise RuntimeError(f"OpenRouter {e.code}: {err[:400]}") from None
    if "error" in data:
        raise RuntimeError(f"OpenRouter: {data['error']}")
    choice = data["choices"][0]
    text = choice["message"].get("content") or ""
    usage = data.get("usage", {})
    if not text.strip() and choice.get("finish_reason") == "length":
        raise RuntimeError(f"{model} spent all {max_tokens} tokens thinking and gave no answer; raise max_tokens or lower effort")
    return {"model": model, "text": text, "result": parse_json(text), "seconds": round(time.time() - t0, 1),
            "cost_usd": usage.get("cost"), "tokens_in": usage.get("prompt_tokens"),
            "tokens_out": usage.get("completion_tokens"),
            "tokens_reasoning": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")}
