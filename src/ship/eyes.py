"""The eyes: a local model writes the summary.  It decides nothing.

Zero-config: talks to whatever Ollama is already serving on this machine and
uses the first model it lists.  Override with SHIP_MODEL and OLLAMA_HOST.
Nothing here ever touches any host but that one.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Optional

DEFAULT_HOST = "http://localhost:11434"
SYSTEM = (
    "You write git commit messages. Reply with the commit message only: one subject line "
    "in the imperative mood of at most 50 characters with no trailing period, then a blank "
    "line, then one to five short lines saying what changed and why. No code fences, no "
    "diff syntax, no preamble, no quotation marks."
)
THINK = re.compile(r"<think>.*?</think>", re.S)
FENCE = re.compile(r"^\s*```.*$", re.M)


def host() -> str:
    h = os.environ.get("OLLAMA_HOST", "").strip() or DEFAULT_HOST
    if "://" not in h:
        h = "http://" + h
    return h.rstrip("/")


def _get(url: str, timeout: float):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


def _post(url: str, body: dict, timeout: float):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def pick_model(timeout: float = 5) -> Optional[str]:
    forced = os.environ.get("SHIP_MODEL", "").strip()
    if forced:
        return forced
    try:
        models = _get(host() + "/api/tags", timeout).get("models", [])
    except (urllib.error.URLError, OSError, ValueError):
        return None
    return models[0]["name"] if models else None


def clean(text: str) -> str:
    text = THINK.sub("", text)
    text = FENCE.sub("", text)
    text = text.strip()
    lines = text.splitlines()
    if lines:
        s = lines[0].strip()
        if len(s) > 1 and s[0] == s[-1] and s[0] in "\"'`":
            s = s[1:-1]
        lines[0] = s
    return "\n".join(lines).strip()


def summarize(change, hint: str = "", timeout: float = 120) -> tuple[Optional[str], str]:
    """Return (summary or None, detail).  None means the eyes did not answer."""
    model = pick_model()
    if model is None:
        return None, f"no model: nothing answered at {host()}"
    prompt = ""
    if hint.strip():
        prompt += f"The author describes the change as: {hint.strip()}\n\n"
    prompt += "Files changed:\n" + change.render() + "\n\nWrite the commit message."
    body = {
        "model": model,
        "system": SYSTEM,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0, "num_predict": 256, "num_ctx": 8192},
    }
    t0 = time.monotonic()
    try:
        out = _post(host() + "/api/generate", body, timeout)
    except urllib.error.HTTPError as e:
        return None, f"{model}: HTTP {e.code} from {host()}"
    except (urllib.error.URLError, OSError, ValueError) as e:
        reason = getattr(e, "reason", None) or e
        return None, f"{model}: no answer within {timeout:.0f}s ({reason})"
    text = clean(str(out.get("response", "")))
    return text, f"{model} in {time.monotonic() - t0:.1f}s"
