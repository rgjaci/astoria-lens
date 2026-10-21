#!/usr/bin/env python3
"""Astoria Lens - point at anything in the neighborhood, understand it.

Zero-dependency local web app. The browser sends a photo plus a question to
this server; the server calls Gemma 4 on the Gemini API and returns plain text.
The API key never reaches the browser.

    export GEMINI_API_KEY="..."      # PowerShell: $env:GEMINI_API_KEY="..."
    python server.py                 # open http://localhost:8000

Standard library only - no pip install, Python 3.9+.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"

MODEL = os.environ.get("GEMMA_MODEL", "gemma-4-26b-a4b-it")
API_BASE = os.environ.get("GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
THINKING = os.environ.get("GEMMA_THINKING", "minimal")
REQUEST_TIMEOUT = 75
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_BODY_BYTES = 12 * 1024 * 1024
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}

LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "el": "Greek",
    "ar": "Arabic",
    "bn": "Bengali",
    "zh": "Simplified Chinese",
}

MODE_INSTRUCTIONS = {
    "translate": (
        "TASK: TRANSLATE. Detect the language of the text in the image, then reply with exactly four "
        "short blocks, each header on its own line:\n"
        "LANGUAGE: the detected language in English, e.g. 'LANGUAGE: Greek'.\n"
        "ORIGINAL: the legible text transcribed exactly, in its original script, keeping the line "
        "breaks of menus and signs; mark anything unreadable in square brackets.\n"
        "TRANSLATION ({lang}): the same text translated into {lang}, same structure.\n"
        "WHAT TO DO: one line on what the reader must know or do, or 'Nothing to do - information only.'"
    ),
    "explain": (
        "TASK: EXPLAIN. Reply with three short blocks, each header on its own line:\n"
        "WHAT IT IS: one line naming the object and what it is for.\n"
        "WHAT MATTERS: up to three bullets, each quoting a fact that changes behavior - price, date, "
        "deadline, fee, allergen, hours, phone number, who to call. Nothing that is not on the page.\n"
        "WHAT TO DO NEXT: one or two lines - where to go, what to ask, what to bring."
    ),
    "read": (
        "TASK: READ ALOUD. Write a clean read-aloud script in {lang}: plain sentences only, no "
        "headers, no bullets, no markdown, no symbols. Say numbers, prices, times, and addresses the "
        "way a person speaks them. Read the important text in order, add one short sentence at the "
        "end on what to do, and stay under 60 words."
    ),
    "ask": (
        "TASK: ANSWER THE QUESTION ABOUT THE IMAGE. Answer only what was asked: no summary of the "
        "whole image, no advice beyond the question. Lead with the direct answer in one line, then one "
        "line saying where in the image it is written. If the image does not answer it, say so plainly "
        "and name what is missing. Two to four plain sentences, no headers, under 80 words.\n\n"
        "Question: {question}"
    ),
}

SYSTEM = (
    "You are Astoria Lens, a neighborhood copilot for Astoria, Queens - one of the most "
    "linguistically diverse places on earth. A neighbor has pointed a phone camera at something "
    "in front of them: a menu, a storefront sign, a flyer taped to a pole, a notice, a receipt, "
    "a product label, a handwritten note.\n\n"
    "Every reply follows these rules:\n"
    "- Lead with what the object is, in one short line. No preamble, no 'This image shows', no apology.\n"
    "- Practical over literal: surface the dates, deadlines, fees, allergens, hours, phone numbers, "
    "prices, and who to call that actually appear on it, before anything decorative.\n"
    "- Never invent text you cannot read. If part of the image is blurry, cropped, or in shadow, say "
    "exactly which part is unreadable, and ask for a sharper photo when that blocks the answer.\n"
    "- Transcribe exactly what is legible; do not complete, 'fix', or guess missing words.\n"
    "- Keep it under about 120 words unless the reader asks for more. Short lines, light headers, no filler.\n"
    "- Assume the reader may be new to the neighborhood, an elder, or a visitor: give the practical "
    "meaning, not just the literal words.\n"
    "- For read-aloud output use plain sentences only: no headers, no bullets, no symbols, and write "
    "numbers the way you would say them.\n"
    "- Write in {lang} unless the task says otherwise.\n\n"
    "A TASK line below tells you which output shape to use. Use exactly that shape."
)

DEMO_OUTPUT = {
    "translate": (
        "[DEMO MODE - no GEMINI_API_KEY set]\n\n"
        "LANGUAGE: Greek\n\n"
        "ORIGINAL\n"
        "ΣΟΥΒΛΑΚΙ ΧΟΙΡΙΝΟ 5.50\n"
        "ΝΤΟΛΜΑΔΕΣ 4.25\n"
        "ΑΡΝΙ ΚΛΕΦΤΙΚΟ 12.00\n"
        "Παραγγελίες στο ταμείο.\n\n"
        "TRANSLATION (English)\n"
        "Pork souvlaki 5.50\n"
        "Stuffed grape leaves 4.25\n"
        "Lamb klefiko 12.00\n"
        "Order at the counter.\n\n"
        "WHAT TO DO\n"
        "Counter service, prices in dollars - order at the counter first, then take a seat."
    ),
    "explain": (
        "[DEMO MODE - no GEMINI_API_KEY set]\n\n"
        "WHAT IT IS\n"
        "A laminated Greek deli menu taped inside the front window.\n\n"
        "WHAT MATTERS\n"
        "- Souvlaki is 5.50, the cheapest hot item; stuffed grape leaves are 4.25.\n"
        "- No allergens or vegetarian labels are printed anywhere on this menu.\n"
        "- No hours, phone number, or card-payment notice appears on the page.\n\n"
        "WHAT TO DO NEXT\n"
        "Order at the counter inside. Ask about today's specials and allergens - they are on the "
        "board, not on this menu."
    ),
    "read": (
        "[DEMO MODE - no GEMINI_API_KEY set]\n\n"
        "A window menu. Pork souvlaki, five dollars and fifty cents. "
        "Stuffed grape leaves, four dollars and twenty five cents. "
        "Lamb klefiko, twelve dollars. Order at the counter."
    ),
    "ask": (
        "[DEMO MODE - no GEMINI_API_KEY set]\n\n"
        "No allergen or vegetarian labels appear on this menu. "
        "Stuffed grape leaves are rice-based here; the lamb klefiko is not. "
        "Ask the counter about dairy and gluten before ordering."
    ),
}


def extract_text(data: dict) -> str:
    feedback = data.get("promptFeedback") or {}
    if feedback.get("blockReason"):
        return "The model blocked this request (%s). Try a different photo or question." % feedback["blockReason"]
    candidates = data.get("candidates") or []
    if not candidates:
        return "No answer came back from the model. Try again."
    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    chunks = [p.get("text", "") for p in parts if p.get("text") and not p.get("thought")]
    text = "".join(chunks).strip()
    if not text:
        return "The model returned no text (finish reason: %s)." % candidates[0].get("finishReason")
    return text


def build_prompt(mode: str, lang_name: str, question: str) -> str:
    if mode == "ask":
        return MODE_INSTRUCTIONS["ask"].format(question=question).strip()
    return MODE_INSTRUCTIONS[mode].format(lang=lang_name)


def call_gemma(image_b64: str, mime: str, mode: str, lang: str, question: str):
    """Return (text, error)."""
    lang_name = LANGUAGES[lang]
    prompt = build_prompt(mode, lang_name, question)
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM.format(lang=lang_name)}]},
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"inlineData": {"mimeType": mime, "data": image_b64}},
                    {"text": prompt},
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.35,
            "maxOutputTokens": 900,
            "thinkingConfig": {"thinkingLevel": THINKING},
        },
    }
    def _post():
        request = urllib.request.Request(
            "%s/models/%s:generateContent" % (API_BASE, MODEL),
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": API_KEY,
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))

    # One quick retry on rate limits, transient 5xx, and flaky venue wifi.
    for attempt in range(2):
        try:
            return extract_text(_post()), None
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            message = raw
            try:
                message = json.loads(raw)["error"]["message"]
            except Exception:
                pass
            if exc.code in (400, 403):
                return None, ("Request rejected - check GEMINI_API_KEY and that your key can reach "
                              "this model. (%s) %s" % (exc.code, message[:400]))
            if exc.code == 404:
                return None, "Model or endpoint not found - check GEMMA_MODEL (try gemma-4-26b-a4b-it)."
            hint = "Rate limited by the Gemini API" if exc.code == 429 else "Gemini API error %s" % exc.code
            if attempt == 0 and exc.code in (429, 500, 503):
                time.sleep(1.5)
                continue
            return None, "%s %s" % (hint, message[:400])
        except urllib.error.URLError as exc:
            if attempt == 0:
                time.sleep(1.0)
                continue
            return None, "Could not reach the Gemini API (%s). Check the venue wifi, then retry." % exc.reason
        except TimeoutError:
            return None, ("The model took longer than %s seconds. Try again, or keep "
                          "GEMMA_MODEL=gemma-4-26b-a4b-it." % REQUEST_TIMEOUT)
    return None, "Gemini API request failed after a retry."


class Handler(SimpleHTTPRequestHandler):
    server_version = "AstoriaLens/0.1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        if self.path in ("", "/"):
            self.path = "/index.html"
        if self.path.split("?")[0] == "/api/health":
            return self._json({"ok": True, "model": MODEL, "key": bool(API_KEY), "demo": not API_KEY})
        return super().do_GET()

    def do_POST(self):
        if self.path.split("?")[0] != "/api/analyze":
            return self.send_error(404, "Not found")
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return self._json({"error": "Empty request body."}, 411)
        if length > MAX_BODY_BYTES:
            return self._json({"error": "Photo too large - keep it under 8 MB."}, 413)
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._json({"error": "Request body was not valid JSON."}, 400)
        if not isinstance(data, dict):
            return self._json({"error": "Request body must be a JSON object."}, 400)

        image = data.get("image")
        mime = data.get("mime") or "image/jpeg"
        mode = data.get("mode") or "explain"
        lang = data.get("lang") or "en"
        question = (data.get("question") or "").strip()[:500]

        if not isinstance(image, str) or len(image) < 100:
            return self._json({"error": "Missing image data."}, 400)
        if image.startswith("data:"):
            image = image.split(",", 1)[-1]
            try:
                base64.b64decode(image, validate=True)
            except Exception:
                return self._json({"error": "Image data was not valid base64."}, 400)
        if mime not in ALLOWED_MIME:
            return self._json({"error": "Unsupported image type %s." % mime}, 415)
        if mode not in MODE_INSTRUCTIONS:
            return self._json({"error": "Unknown mode %s." % mode}, 400)
        if lang not in LANGUAGES:
            return self._json({"error": "Unknown language %s." % lang}, 400)
        if mode == "ask" and not question:
            return self._json({"error": "Type a question first."}, 400)

        started = time.time()
        if not API_KEY:
            time.sleep(0.15)
            text, error = DEMO_OUTPUT[mode], None
        else:
            text, error = call_gemma(image, mime, mode, lang, question)
        elapsed = int((time.time() - started) * 1000)

        if error:
            print("[error] %s" % error, file=sys.stderr)
            return self._json({"error": error}, 502)
        print("[%s ms] %s/%s -> %s chars" % (elapsed, mode, lang, len(text)), file=sys.stderr)
        return self._json({
            "text": text,
            "mode": mode,
            "lang": lang,
            "model": MODEL,
            "demo": not API_KEY,
            "ms": elapsed,
        })

    def _json(self, obj, status=200):
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)


def banner(port: int, host: str) -> None:
    line = "=" * 62
    print(line)
    print("  ASTORIA LENS  -  Gemma 4 vision, running locally")
    print(line)
    print("  URL     http://%s:%d" % ("localhost" if host == "127.0.0.1" else host, port))
    print("  Model   %s" % MODEL)
    if API_KEY:
        print("  Key     loaded (stays on this machine)")
    else:
        print("  Key     MISSING - running in DEMO MODE with canned output")
        print("          Get one free at https://aistudio.google.com/apikey")
        print("          PowerShell: $env:GEMINI_API_KEY=\"...\"; python server.py")
    print(line)
    print("  Ctrl+C to stop")
    print()


def main() -> None:
    host = os.environ.get("HOST", "127.0.0.1")
    raw_port = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PORT", "8000")
    preferred = int(raw_port) if str(raw_port).isdigit() else 8000
    server = None
    for port in range(preferred, preferred + 20):
        try:
            server = ThreadingHTTPServer((host, port), Handler)
            break
        except OSError:
            continue
    if server is None:
        print("Could not bind a port between %d and %d." % (preferred, preferred + 19), file=sys.stderr)
        raise SystemExit(1)
    banner(server.server_address[1], host)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped. Ship it.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
