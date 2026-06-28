#!/usr/bin/env python3
"""Shared client for opencode's Zen Go endpoint — subscription-based, no per-key billing.

Used by runner.py (generation) and judge.py (rubric scoring) so there's one
place that knows how to authenticate and call opencode instead of two.
"""

import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path

SSL_CONTEXT = ssl.create_default_context()
try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    pass

BASE_URL = "https://opencode.ai/zen/go/v1"
# ponytail: Cloudflare 403s requests with no User-Agent (error code 1010).
# Any UA string works — this just needs to look like a real client.
HEADERS_UA = "opencode-ai-engineering-gates/1.0"


def load_key() -> str:
    """OPENCODE_GO_API_KEY from env, falling back to ~/.hermes/.env."""
    k = os.environ.get("OPENCODE_GO_API_KEY", "").strip()
    if k:
        return k
    try:
        for line in Path("~/.hermes/.env").expanduser().read_text().splitlines():
            if line.startswith("OPENCODE_GO_API_KEY="):
                k = line.split("=", 1)[1].strip()
                if k:
                    return k
    except Exception:
        pass
    return ""


def chat(model: str, system_prompt: str, user_prompt: str, key: str,
         temp: float = 0.3, retries: int = 3) -> dict:
    """Call opencode's OpenAI-compatible chat endpoint.

    Returns {"text": str, "usage": dict} or {"text": "API_ERROR: ...", "usage": {}} on failure.
    """
    body = json.dumps({
        "model": model,
        "temperature": temp,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions", data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": HEADERS_UA,
        },
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=180, context=SSL_CONTEXT) as r:
                resp = json.loads(r.read())
            return {"text": resp["choices"][0]["message"]["content"], "usage": resp.get("usage", {})}
        except Exception as e:
            if attempt == retries - 1:
                return {"text": f"API_ERROR: {e}", "usage": {}}
            import time
            time.sleep(2 * (attempt + 1))


if __name__ == "__main__":
    key = load_key()
    print(f"key loaded: {bool(key)} (len={len(key)})")
    if key:
        r = chat("deepseek-v4-pro", "Reply with one word.", "Say: ok", key, temp=0)
        print(r)
