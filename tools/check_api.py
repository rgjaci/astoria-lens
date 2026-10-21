#!/usr/bin/env python3
"""One REAL call to Gemma 4 on the Gemini API - the 7:30pm key check.

    PowerShell:  $env:GEMINI_API_KEY="..."; python tools/check_api.py
    bash:        GEMINI_API_KEY=... python tools/check_api.py

Sends static/samples/menu.png to gemma-4-26b-a4b-it exactly the way server.py
does and prints model, HTTP status, latency, and the first 200 characters of the
answer. On failure it prints the API message plus an actionable hint. Supports
--model to try the other valid model id.

    python tools/check_api.py --model gemma-4-31b-it

Exit codes: 0 = got a real answer, 1 = call failed, 2 = no key set.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "static" / "samples" / "menu.png"
DEFAULT_MODEL = "gemma-4-26b-a4b-it"
VALID_MODELS = ("gemma-4-26b-a4b-it", "gemma-4-31b-it")
DEFAULT_BASE = "https://generativelanguage.googleapis.com/v1beta"

SYSTEM = (
    "You are Astoria Lens, a neighborhood copilot for Astoria, Queens. "
    "Explain what the image is, the three things that matter, and what to do next. "
    "Under 120 words. Never invent text you cannot read."
)
PROMPT = (
    "TASK: EXPLAIN. Explain what this is and what it means for the person holding it. "
    "Give: WHAT IT IS (one line), THE THREE THINGS THAT MATTER (bullets), "
    "WHAT TO DO NEXT (one or two lines). Skip anything that is not on the page."
)

HINTS = {
    400: (
        "The request was rejected. Usually a bad or legacy API key, or the key's project does\n"
        "        not have the Generative Language API enabled. Re-copy the key from\n"
        "        https://aistudio.google.com/apikey with no quotes or spaces, and try\n"
        "        --model gemma-4-31b-it."
    ),
    401: "No key reached the API. Set GEMINI_API_KEY in this same shell, then rerun.",
    403: (
        "The key was refused. It is likely invalid, revoked, restricted, or a legacy key that\n"
        "        cannot reach this model. Create a fresh key in AI Studio and put it in\n"
        "        $env:GEMINI_API_KEY for THIS shell window (a new window loses it)."
    ),
    404: (
        "Wrong model id or endpoint. Valid model ids tonight: gemma-4-26b-a4b-it or\n"
        "        gemma-4-31b-it. Try: python tools/check_api.py --model gemma-4-31b-it"
    ),
    429: (
        "Rate limited or out of quota. Wait ~60 seconds and rerun - and if it repeats,\n"
        "        switch to a different key before the demo, not during it."
    ),
    500: "Gemini API server error - retry once in a minute; the app will also retry once.",
    503: "Gemini API is busy/unavailable - retry once in a minute.",
}


def sniff_mime(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"


def main() -> int:
    parser = argparse.ArgumentParser(description="One real Gemma 4 vision call - the pre-demo key check.")
    parser.add_argument("--model", default=os.environ.get("GEMMA_MODEL", DEFAULT_MODEL),
                        help="Gemma model id (default: %s)" % DEFAULT_MODEL)
    parser.add_argument("--image", default=str(SAMPLE), help="image to send (default: static/samples/menu.png)")
    parser.add_argument("--base", default=os.environ.get("GEMINI_API_BASE", DEFAULT_BASE),
                        help="API base URL (default: %s)" % DEFAULT_BASE)
    parser.add_argument("--timeout", type=float, default=120.0, help="seconds to wait (default: 120)")
    args = parser.parse_args()

    key = os.environ.get("GEMINI_API_KEY", "").strip().strip('"').strip("'")
    if not key:
        print("FAIL  GEMINI_API_KEY is not set in this shell.")
        print("      PowerShell: $env:GEMINI_API_KEY=\"your-key\"; python tools/check_api.py")
        print("      Get a free key: https://aistudio.google.com/apikey")
        return 2

    image_path = Path(args.image).expanduser().resolve()
    if not image_path.exists():
        print("FAIL  image not found: %s" % image_path)
        return 1
    data = image_path.read_bytes()
    mime = sniff_mime(data)
    model = args.model
    url = "%s/models/%s:generateContent" % (args.base.rstrip("/"), model)

    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [
            {"inlineData": {"mimeType": mime, "data": base64.b64encode(data).decode("ascii")}},
            {"text": PROMPT},
        ]}],
        "generationConfig": {
            "temperature": 0.35,
            "maxOutputTokens": 900,
            "thinkingConfig": {"thinkingLevel": os.environ.get("GEMMA_THINKING", "minimal")},
        },
    }

    print("Astoria Lens - real API key check")
    print("  model   %s" % model)
    print("  image   %s  (%s, %.0f KB)" % (image_path, mime, len(data) / 1024.0))
    print("  key     %s...%s (%d chars)" % (key[:6], key[-4:], len(key)) if len(key) > 12 else "  key     set")
    print("  sending ...", end="", flush=True)

    started = time.time()
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            status = response.status
            raw = response.read()
    except urllib.error.HTTPError as exc:
        elapsed = time.time() - started
        status = exc.code
        raw = exc.read()
        print("\r  status  HTTP %s   latency %.2fs" % (status, elapsed))
        message = raw.decode("utf-8", "replace")
        try:
            message = json.loads(message)["error"]["message"]
        except Exception:  # noqa: BLE001
            pass
        print("  error   %s" % message[:500])
        hint = HINTS.get(status)
        if hint:
            print("\n  HINT  " + hint)
        if status == 404 and model not in VALID_MODELS:
            print("\n  Valid model ids: %s" % ", ".join(VALID_MODELS))
        print("\ncheck_api: FAIL")
        return 1
    except urllib.error.URLError as exc:
        print("\r  status  no connection (%.2fs)" % (time.time() - started))
        print("  error   %s" % (exc.reason,))
        print("\n  HINT  This is the network, not the key. Check venue wifi / DNS and rerun.")
        print("\ncheck_api: FAIL")
        return 1
    except TimeoutError:
        print("\r  status  timed out after %.0fs" % args.timeout)
        print("\n  HINT  The venue network is slow. Retry, and try --model gemma-4-26b-a4b-it.")
        print("\ncheck_api: FAIL")
        return 1

    elapsed = time.time() - started
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:  # noqa: BLE001
        print("\r  status  HTTP %s   latency %.2fs" % (status, elapsed))
        print("  error   response was not JSON: %s" % raw[:300])
        print("\ncheck_api: FAIL")
        return 1

    feedback = payload.get("promptFeedback") or {}
    candidates = payload.get("candidates") or []
    text = ""
    finish = None
    if candidates:
        finish = candidates[0].get("finishReason")
        for part in (candidates[0].get("content") or {}).get("parts") or []:
            if part.get("text") and not part.get("thought"):
                text += part["text"]
    text = text.strip()
    usage = payload.get("usageMetadata") or {}

    print("\r  status  HTTP %s   latency %.2fs" % (status, elapsed))
    print("  finish  %s%s" % (finish, "  (blocked: %s)" % feedback["blockReason"]
                                if feedback.get("blockReason") else ""))
    if usage:
        print("  tokens  %s prompt / %s output" % (usage.get("promptTokenCount"), usage.get("candidatesTokenCount")))
    print("  answer  %s" % (text[:200].replace("\n", " / ") if text else "(no text returned)"))

    if not text:
        print("\ncheck_api: FAIL  the API answered but returned no text.")
        if feedback.get("blockReason"):
            print("  HINT  Safety filter blocked the sample photo. Demo with a different photo.")
        else:
            print("  HINT  Try --model gemma-4-31b-it; if it also returns no text, use demo mode tonight.")
        return 1

    print("\ncheck_api: PASS  - real Gemma 4 vision call works. Demo risk retired.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
