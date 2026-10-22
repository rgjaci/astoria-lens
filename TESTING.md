# Testing Astoria Lens

Three levels: **automated** (no key, no network), **live API** (needs the key), and the **browser
pass** you should run once before demos. Total time: under 5 minutes.

---

## 0. Automated offline — 30 seconds, no key, no network

```powershell
cd astoria-lens
python tools\selftest.py
```

**Expect:** `PASS  69/69 checks passed`, then `selftest: PASS`, exit code 0.

**What it proves:** all four modes return 200 with non-empty text against a mock Gemini endpoint;
the request carries `x-goog-api-key`, the right model in the path, `inlineData` with a valid PNG,
`systemInstruction`, and `thinkingConfig.thinkingLevel == "minimal"`; `/api/health`, the static
files, and every error path (bad mode / missing image / bad JSON / bad language / unknown route) are
correct; the mock saw exactly four model calls; its ports are cleaned up afterwards.

Run this after any code change — it is the regression test.

## 1. Live API — 10 seconds, needs the key

```powershell
$env:GEMINI_API_KEY="your-key"
python tools\check_api.py
```

**Expect:** `status HTTP 200`, latency roughly 2–7 s, `tokens … prompt / … output`, an answer
mentioning Taverna Astoria and the menu, and `check_api: PASS`.

- Try the other model: `python tools\check_api.py --model gemma-4-31b-it`
- Failure hints are built in: **402** = that key's project is on prepay with no balance (Gemma 4 is
  free-tier only — make a key in a new project); **403** = bad/legacy key; **404** = wrong model id;
  **429** = quota, wait a minute.

## 2. Browser smoke test — 2 minutes

```powershell
python server.py
```

Open <http://localhost:8000/?sample=menu> (the `?sample=menu` shortcut skips the camera).

| # | Do this | Pass looks like |
| --- | --- | --- |
| 1 | Look at the top-right pills | `GEMMA 4 LIVE` — not `DEMO MODE`. If it says demo, the key isn't in this shell. |
| 2 | Watch the first answer arrive | ~3 s; `WHAT IT IS` / `WHAT MATTERS` / `WHAT TO DO NEXT`; mentions cash-only under $10, the allergen note, the address |
| 3 | Click **Ask**, type `does this contain nuts?` | ~2 s; answers the question, says the menu doesn't list allergens and to ask staff |
| 4 | Click **Read aloud** | Browser speaks the script; numbers read as words ("five dollars and fifty cents") |
| 5 | Change language to **Ελληνικά** while in Read aloud | ~3–5 s; Greek output; the speak button now uses a Greek voice if one is installed |
| 6 | Click **Translate** | ~10–13 s (the slow mode); `LANGUAGE: Greek`, `ORIGINAL` in Greek script, `TRANSLATION`, `WHAT TO DO` |
| 7 | Click **Copy** | Button flashes "Copied"; paste into an editor |
| 8 | Click **Retake** | Camera preview returns (or the camera note if this machine has no webcam) |
| 9 | Click **Sample: flyer**, then **Explain** | ~3.5 s; extracts "Saturday, October 25", "Registration closes Friday, October 23 at 6:00 PM", and 718-555-0142 |

**Pass criteria:** no red error banner, every answer arrives in 2–13 s, output is formatted (not raw
markdown/markup).

> Auto-answered: if you open <http://localhost:8000> without `?sample=`, the page asks for camera
> permission. Grant it, or use **Choose photo** / the sample buttons.

## 3. Demo-mode fallback — 30 seconds

This is what the stage falls back to if the key or network dies. Test it once so you have seen it.

```powershell
Remove-Item Env:GEMINI_API_KEY      # same shell window
python server.py
```

Open <http://localhost:8000/?sample=menu>. **Expect:** an amber `DEMO MODE` pill, output starting
with `[DEMO MODE - no GEMINI_API_KEY set]`, still fully formatted, ~150 ms (no network).

## 4. Error-path check — 15 seconds (optional, don't demo in this state)

```powershell
$env:GEMINI_API_KEY="bogus"
python server.py
```

**Expect:** a readable error banner with a hint (HTTP 400/403), the app stays usable, no crash. Then
restart with the real key.

## 5. Demo rehearsal — 2 minutes

Run the beats in [SUBMISSION.md](SUBMISSION.md) with a stopwatch: **Explain → Ask → Read aloud →
language switch → Translate last**. Target under 90 seconds. Do it twice — the second time on venue
wifi — then keep the recording as backup.

---

## Known-good environment

- Python **3.14.2** on Windows 11 (code claims 3.9+); Edge/Chrome for the headless screenshot.
- Camera requires a secure context — `http://localhost` qualifies; a LAN IP does not without HTTPS.
  The file/sample path needs no camera at all.
- Read-aloud uses the browser's built-in voices. English always works; Greek/Arabic/Bengali/Chinese
  voices may be missing on a given machine — the text still renders, which is what judges score.
- Server binds `127.0.0.1:8000` and auto-increments if the port is busy. The harness uses 8901–8903.
- Free-tier quotas are real: a 429 is possible under heavy clicking. The server retries once; if it
  persists, switch to demo mode rather than debugging on stage.
