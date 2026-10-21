#!/usr/bin/env python3
"""Offline stand-in for the Gemini API's generateContent endpoint.

    python tools/mock_gemini.py            # listens on 127.0.0.1:8902

Implements POST /v1beta/models/{model}:generateContent and returns realistic
Gemini JSON: a thought part followed by a text part, finishReason STOP, and
usageMetadata. Every request is recorded so a test can assert exactly what the
app sent (x-goog-api-key header, inline image, system instruction, generation
config). Stdlib only, no network, no real key.

Endpoints:
    POST /v1beta/models/{model}:generateContent   the fake model
    GET  /_last                                   last recorded request (JSON)
    GET  /_reset                                  forget recorded requests
    GET  /_health                                 liveness probe
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 8902
MAX_BODY = 64 * 1024 * 1024

STATE = {"requests": []}
LOCK = threading.Lock()

CANNED = {
    "translate": (
        "ORIGINAL\n"
        "ΣΟΥΒΛΑΚΙ ΧΟΙΡΙΝΟ 5.50\n"
        "ΝΤΟΛΜΑΔΕΣ 4.25\n"
        "Παραγγελίες στο ταμείο.\n\n"
        "TRANSLATION (English)\n"
        "Pork souvlaki 5.50\n"
        "Stuffed grape leaves 4.25\n"
        "Order at the counter.\n\n"
        "WHAT TO DO\n"
        "Counter service, and the menu says cash only under $10 - order first, then sit."
    ),
    "explain": (
        "A laminated Greek deli menu taped inside the front window.\n\n"
        "THE THREE THINGS THAT MATTER\n"
        "- Pork souvlaki at 5.50 is the cheapest hot item.\n"
        "- Stuffed grape leaves are rice-based, not meat.\n"
        "- Cash only under $10.\n\n"
        "WHAT TO DO NEXT\n"
        "Order at the counter inside. Ask about today's specials - they are on the "
        "board, not on this menu."
    ),
    "read": (
        "A window menu. Pork souvlaki, five dollars and fifty cents. "
        "Stuffed grape leaves, four dollars and twenty five cents. "
        "Lamb klefiko, twelve dollars. Order at the counter."
    ),
    "ask": (
        "The menu does not list allergens or vegetarian labels. The stuffed grape leaves "
        "are rice-based here; the lamb klefiko is not. Ask the counter about dairy and "
        "gluten before ordering."
    ),
}


def answer_for(body: dict) -> str:
    """Pick a canned answer that matches the task the app asked for."""
    text = ""
    for content in (body or {}).get("contents") or []:
        for part in content.get("parts") or []:
            if isinstance(part.get("text"), str):
                text += part["text"] + "\n"
    upper = text.upper()
    if "TASK: TRANSLATE" in upper:
        return CANNED["translate"]
    if "TASK: EXPLAIN" in upper:
        return CANNED["explain"]
    if "TASK: READ ALOUD" in upper:
        return CANNED["read"]
    if "TASK: ANSWER THE QUESTION" in upper:
        return CANNED["ask"]
    return "The photo shows a Greek deli menu. Ask me what matters and I will tell you."


class Handler(BaseHTTPRequestHandler):
    server_version = "MockGemini/1.0"
    protocol_version = "HTTP/1.0"

    def log_message(self, fmt, *args):  # keep test output readable
        print("[mock] " + (fmt % args), file=sys.stderr)

    def _json(self, obj, status=200):
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/_last":
            with LOCK:
                last = STATE["requests"][-1] if STATE["requests"] else None
                count = len(STATE["requests"])
            return self._json({"count": count, "last": last})
        if path == "/_reset":
            with LOCK:
                STATE["requests"].clear()
            return self._json({"ok": True})
        if path in ("/_health", "/health"):
            return self._json({"ok": True, "mock": True, "count": len(STATE["requests"])})
        return self._json({"error": {"code": 404, "message": "Not found: %s" % path}}, 404)

    def do_POST(self):
        path = self.path.split("?")[0]
        if not path.endswith(":generateContent"):
            return self._json(
                {"error": {"code": 404, "message": "Not found: %s" % path}}, 404
            )
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return self._json(
                {"error": {"code": 400, "message": "Empty request body."}}, 400
            )
        if length > MAX_BODY:
            return self._json(
                {"error": {"code": 413, "message": "Request body too large."}}, 413
            )
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._json(
                {"error": {"code": 400, "message": "Request body was not valid JSON."}},
                400,
            )

        model = path.rsplit("/models/", 1)[-1].split(":", 1)[0]
        record = {
            "method": "POST",
            "path": self.path,
            "model": model,
            "headers": {
                "x-goog-api-key": self.headers.get("x-goog-api-key"),
                "content-type": self.headers.get("content-type"),
            },
            "body": body,
        }
        with LOCK:
            STATE["requests"].append(record)

        answer = answer_for(body)
        response = {
            "candidates": [
                {
                    "content": {
                        "role": "model",
                        "parts": [
                            {"text": "Reading the paper menu and sorting the practical bits.", "thought": True},
                            {"text": answer},
                        ],
                    },
                    "finishReason": "STOP",
                    "index": 0,
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 1180,
                "candidatesTokenCount": 142,
                "totalTokenCount": 1322,
            },
            "modelVersion": model or "gemma-4-26b-a4b-it",
        }
        return self._json(response)


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline mock of the Gemini generateContent endpoint.")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--quiet", action="store_true", help="do not log each request")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    if args.quiet:
        Handler.log_message = lambda *a, **k: None
    print("mock gemini listening on http://%s:%d" % (args.host, server.server_address[1]), file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
