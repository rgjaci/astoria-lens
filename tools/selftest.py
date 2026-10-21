#!/usr/bin/env python3
"""End-to-end offline test for Astoria Lens. No network, no real API key.

    python tools/selftest.py

Starts tools/mock_gemini.py on 127.0.0.1:8902, then runs server.py as a
subprocess on 127.0.0.1:8901 with GEMINI_API_BASE pointed at the mock and a
dummy GEMINI_API_KEY. Posts static/samples/menu.png through all four modes and
asserts the whole contract: HTTP status, answer text, the exact request the
server sent (key header, inline image, system instruction, thinking config),
static files, health, and the plain-language 400/404 error paths.

Prints one PASS/FAIL line per check and exits nonzero on any failure. Cleans up
both subprocesses and their ports on exit.
"""

from __future__ import annotations

import base64
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
MOCK_PORT = 8902
APP_PORT = 8901
MOCK_BASE = "http://127.0.0.1:%d" % MOCK_PORT
APP_BASE = "http://127.0.0.1:%d" % APP_PORT
MODEL = "gemma-4-26b-a4b-it"
DUMMY_KEY = "selftest-dummy-key-not-real"
PNG_PATH = ROOT / "static" / "samples" / "menu.png"
PNG = PNG_PATH.read_bytes()
PNG_B64 = base64.b64encode(PNG).decode("ascii")
PNG_HEADER = b"\x89PNG\r\n\x1a\n"
THINKING = "minimal"

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    line = ("PASS  " if ok else "FAIL  ") + name
    if detail and not ok:
        line += "  <- " + str(detail)[:400]
    print(line)


def http(method, url, body=None, headers=None, timeout=20):
    """Return (status, bytes, headers). HTTP errors are returned, not raised."""
    if isinstance(body, (bytes, bytearray)) or body is None:
        data = body
    else:
        data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)


def port_is_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def wait_for(url, timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            status, _, _ = http("GET", url, timeout=2)
            if status == 200:
                return True
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
        time.sleep(0.15)
    return False


def stop(process, name):
    if process is None:
        return
    if process.poll() is None:
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
        except OSError:
            pass
    print("cleanup: %s stopped" % name)


def post_analyze(payload):
    return http(
        "POST",
        APP_BASE + "/api/analyze",
        body=payload,
        headers={"Content-Type": "application/json"},
    )


def get_last_mock_request():
    status, raw, _ = http("GET", MOCK_BASE + "/_last", timeout=5)
    if status != 200:
        raise RuntimeError("mock _last returned HTTP %s" % status)
    return json.loads(raw.decode("utf-8"))


def assert_request_contract(tag, mode):
    data = get_last_mock_request()
    last = data.get("last") or {}
    recorded = (last.get("body") or {})
    parts = ((recorded.get("contents") or [{}])[0].get("parts") or [{}])

    check("[%s] mock received x-goog-api-key" % tag, last.get("headers", {}).get("x-goog-api-key") == DUMMY_KEY,
          last.get("headers"))
    check("[%s] mock received expected model in path" % tag,
          last.get("path", "").endswith("/models/%s:generateContent" % MODEL), last.get("path"))
    system = ((recorded.get("systemInstruction") or {}).get("parts") or [{}])[0].get("text", "")
    check("[%s] systemInstruction present" % tag, "Astoria Lens" in system, system[:120])

    inline = parts[0].get("inlineData") or {}
    check("[%s] inlineData.mimeType is image/png" % tag, inline.get("mimeType") == "image/png",
          inline.get("mimeType"))
    try:
        decoded = base64.b64decode(inline.get("data") or "", validate=True)
    except Exception as exc:  # noqa: BLE001
        decoded = b""
        check("[%s] inline image is valid base64" % tag, False, exc)
    else:
        check("[%s] inline image is valid base64" % tag, True)
    check("[%s] inline image decodes to a valid PNG header" % tag, decoded.startswith(PNG_HEADER),
          decoded[:8])
    check("[%s] inline image is the sample photo" % tag, decoded == PNG,
          "%d bytes" % len(decoded))

    gen = recorded.get("generationConfig") or {}
    check("[%s] generationConfig.thinkingConfig.thinkingLevel == %s" % (tag, THINKING),
          (gen.get("thinkingConfig") or {}).get("thinkingLevel") == THINKING,
          gen.get("thinkingConfig"))
    check("[%s] generationConfig has temperature/maxOutputTokens" % tag,
          "temperature" in gen and "maxOutputTokens" in gen, gen)


def main():
    print("Astoria Lens offline selftest - python %s" % sys.version.split()[0])
    print("repo: %s" % ROOT)
    if not PNG_PATH.exists():
        print("FAIL  sample photo missing: %s" % PNG_PATH)
        return 1
    check("sample photo exists and is a PNG", PNG.startswith(PNG_HEADER), str(PNG_PATH))

    for port in (APP_PORT, MOCK_PORT):
        if not port_is_free(port):
            print("FAIL  port %d is already in use - stop that process and rerun" % port)
            return 1

    mock = None
    app = None
    env = os.environ.copy()
    env["GEMINI_API_BASE"] = MOCK_BASE + "/v1beta"
    env["GEMINI_API_KEY"] = DUMMY_KEY
    env["HOST"] = "127.0.0.1"
    env.pop("GEMMA_MODEL", None)
    env.pop("GEMMA_THINKING", None)

    try:
        mock = subprocess.Popen(
            [PY, str(ROOT / "tools" / "mock_gemini.py"), "--port", str(MOCK_PORT), "--quiet"],
            cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        check("mock gemini starts on 127.0.0.1:%d" % MOCK_PORT,
              wait_for(MOCK_BASE + "/_health", 15), "mock never answered /_health")

        app = subprocess.Popen(
            [PY, str(ROOT / "server.py"), str(APP_PORT)],
            cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        check("server.py starts on 127.0.0.1:%d" % APP_PORT,
              wait_for(APP_BASE + "/api/health", 20), "server never answered /api/health")

        # ------------------------------------------------------- static + health
        status, raw, _ = http("GET", APP_BASE + "/api/health")
        try:
            health = json.loads(raw.decode("utf-8"))
        except Exception:  # noqa: BLE001
            health = {}
        check("GET /api/health returns 200 JSON", status == 200 and health.get("ok") is True,
              "HTTP %s %s" % (status, raw[:120]))
        check("health reports the model", health.get("model") == MODEL, health.get("model"))
        check("health reports a loaded key (not demo mode)",
              health.get("key") is True and health.get("demo") is False, health)

        status, raw, _ = http("GET", APP_BASE + "/")
        check("GET / serves the app", status == 200 and b"Astoria Lens" in raw,
              "HTTP %s, %d bytes" % (status, len(raw)))

        status, raw, _ = http("GET", APP_BASE + "/samples/menu.png")
        check("GET /samples/menu.png serves the PNG",
              status == 200 and raw.startswith(PNG_HEADER), "HTTP %s, %d bytes" % (status, len(raw)))

        status, _, _ = http("GET", APP_BASE + "/nope-does-not-exist.txt")
        check("GET unknown path is a 404", status == 404, "HTTP %s" % status)

        # ------------------------------------------------------------- four modes
        mode_payloads = [
            ("explain", {"image": PNG_B64, "mime": "image/png", "mode": "explain", "lang": "en"}),
            ("translate", {"image": PNG_B64, "mime": "image/png", "mode": "translate", "lang": "es"}),
            ("read", {"image": PNG_B64, "mime": "image/png", "mode": "read", "lang": "en"}),
            ("ask", {"image": PNG_B64, "mime": "image/png", "mode": "ask", "lang": "en",
                     "question": "Does this contain nuts?"}),
        ]
        for mode, payload in mode_payloads:
            status, raw, _ = post_analyze(payload)
            try:
                data = json.loads(raw.decode("utf-8"))
            except Exception:  # noqa: BLE001
                data = {}
            check("[%s] POST /api/analyze returns 200" % mode, status == 200,
                  "HTTP %s %s" % (status, raw[:200]))
            text = data.get("text") or ""
            check("[%s] answer is non-empty text" % mode, isinstance(text, str) and len(text.strip()) > 20,
                  text[:120])
            check("[%s] no error field and demo mode is off" % mode,
                  "error" not in data and data.get("demo") is False and data.get("model") == MODEL,
                  {k: data.get(k) for k in ("error", "demo", "model")})
            check("[%s] answer is not marked [DEMO MODE]" % mode, "[DEMO MODE" not in text, text[:80])
            assert_request_contract(mode, mode)

        data = get_last_mock_request()
        check("mock saw exactly 4 model calls (one per mode)", data.get("count") == 4,
              "count=%s" % data.get("count"))

        # ----------------------------------------------------------- error paths
        status, raw, _ = post_analyze({"image": PNG_B64, "mime": "image/png", "mode": "shout"})
        body = json.loads(raw.decode("utf-8")) if raw else {}
        check("bad mode -> 400 with a JSON error", status == 400 and bool(body.get("error")),
              "HTTP %s %s" % (status, raw[:200]))

        status, raw, _ = post_analyze({"image": "", "mime": "image/png", "mode": "explain"})
        check("empty image -> 400", status == 400, "HTTP %s %s" % (status, raw[:200]))

        status, raw, _ = post_analyze({"mode": "explain", "lang": "en"})
        check("no image key -> 400", status == 400, "HTTP %s %s" % (status, raw[:200]))

        status, raw, _ = http(
            "POST", APP_BASE + "/api/analyze", body=b"{this is not json",
            headers={"Content-Type": "application/json"},
        )
        check("bad JSON body -> 400", status == 400, "HTTP %s %s" % (status, raw[:200]))

        status, raw, _ = http(
            "POST", APP_BASE + "/api/analyze",
            body={"image": PNG_B64, "mime": "image/png", "mode": "explain", "lang": "xx"},
            headers={"Content-Type": "application/json"},
        )
        check("bad language -> 400", status == 400, "HTTP %s %s" % (status, raw[:200]))

        status, raw, _ = http("POST", APP_BASE + "/api/not-a-route", body=b"{}",
                              headers={"Content-Type": "application/json"})
        check("unknown POST route -> 404", status == 404, "HTTP %s" % status)

        check("error paths never reached the model", get_last_mock_request().get("count") == 4,
              "count=%s" % get_last_mock_request().get("count"))

    finally:
        stop(app, "server.py")
        stop(mock, "mock_gemini.py")
        time.sleep(0.2)
        for port, name in ((APP_PORT, "server.py"), (MOCK_PORT, "mock_gemini.py")):
            if not port_is_free(port):
                print("WARN  port %d still in use after stopping %s" % (port, name))

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = [(name, detail) for name, ok, detail in RESULTS if not ok]
    print("-" * 62)
    if failed:
        print("FAILED  %d passed, %d failed" % (passed, len(failed)))
        for name, detail in failed:
            print("  x %s%s" % (name, ("  [%s]" % detail) if detail else ""))
        print("selftest: FAIL")
        return 1
    print("PASS  %d/%d checks passed" % (passed, len(RESULTS)))
    print("selftest: PASS - offline harness, four modes, request contract and error paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
