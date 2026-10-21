# Submission pack

Everything you need at 8:45pm, in paste order.

> **How you actually submit:** on the event page (<https://www.mlh.com/events/astoria-tech-meetup-x-hacktoberfest-hack-day>),
> **Challenges → Add Submission**. Devpost or a bare form does not replace this flow. One teammate
> submits for the team; every teammate still has to be registered and checked in to be judged.

## Project name

**Astoria Lens** — point at anything in the neighborhood, understand it.

## One-line pitch

> Your neighbor's phone camera, the neighborhood's most patient translator: a photo of a menu, a
> flyer, or a notice becomes the practical meaning, in your language, in about two seconds.

## Short description (paste into the submission form)

Astoria is one of the most linguistically diverse places on earth — and its menus, flyers, and
notices are still mostly paper. Astoria Lens is an open-source **Gemma 4** vision companion: point a
camera at anything in front of you and get the practical meaning back in the language you read, not
just a literal translation. Four modes — Explain, Translate, Read aloud, Ask — cover the four
things people actually need on a sidewalk: *what is this, what does it say, read it to me, and
answer my question about it.* The front end is three static files; the backend is a
standard-library Python proxy that keeps the API key server-side, downscales the photo in the
browser, calls `gemma-4-26b-a4b-it` on the Gemini API, and falls back to a labelled demo mode so a
live demo never dies on a missing environment variable. It ships with a framework-agnostic
`skills.md`, so the same prompt contract can be dropped into any agent harness. Built in an evening
at Hacktoberfest Hack Day with the Astoria Tech Meetup.

## Technologies used (form field)

Python 3 (standard library only) · vanilla JavaScript / HTML / CSS · Gemma 4
(`gemma-4-26b-a4b-it`) via the Gemini API · Web Speech API.

## Category mapping

**Best Open-Source AI Project**
- Original project, built tonight, MIT licensed, public repo that stays public.
- Open-weight AI is the load-bearing part: every answer is a Gemma 4 vision call; the app is a thin,
  readable harness around an open model, with the prompt, the proxy, and the UI in one repo.
- Ships a `skills.md` — the skill is reusable outside this app, in any agent framework.
- No vendor SDK, no build step, no dependencies: `python server.py` is the whole install.
- Built for the "open source AI belongs to everyone" frame: swap the API base for a local
  Ollama/vLLM Gemma and it runs offline.

**Best Use of Gemma 4**
- **Model identified in the README** (judges are told to verify the Gemma model in the README and
  the integration in code/demo — it's the first thing in the architecture section).
- **Multimodal experience:** one photo in, text answer out — the app is useless without vision.
- **Focused AI tool for the community:** not a chatbot, a four-mode street instrument with a
  practical output contract.
- **Rapid prototyping:** Gemma 4 via the Gemini API took the idea from photo to working demo in one
  evening; `thinkingLevel: minimal` keeps street-corner latency.
- **Language coverage:** answers in six languages, chosen for Astoria's actual demographics.

## What judges score (MLH Hack Day rubric — equal weight)

| Criterion | What they're looking for | Our evidence |
| --- | --- | --- |
| **Technology** | Does it work, is the use of tech interesting? | Vision model as the load-bearing component; stdlib-only proxy; browser-side downscale; demo fallback. |
| **Design** | Is it usable and considered? | Four modes instead of a chat box; big tap targets; read-aloud; six output languages; projector-readable result typography. |
| **Completion** | Is it finished, not a stub? | Runs end to end from a clean clone with no install; sample photos included; errors explained in plain language. |
| **Learning** | Did the team learn something real? | The prompt-engineering story: teaching the model to refuse to guess, lead with the consequence, and stay under 120 words. |

Pitch quality and code quality are **not** scored — demo a working thing, don't narrate the stack.

## Demo video script (60–90 seconds)

Host sets the demo format; keep a 60–90 s recording anyway as a backup and for the submission's
"demo URL" field.

| Time | Shot | Line |
| --- | --- | --- |
| 0:00 | Title card: Astoria Lens | "Astoria is one of the most multilingual places on earth. Its paper isn't." |
| 0:08 | Hold a real Greek menu / click Sample: menu | "This is a menu a few blocks from here. I can't read it." |
| 0:15 | Click **Explain** | "Explain gives me what it is and what actually matters — prices, and that I order at the counter." |
| 0:28 | Switch to **Translate** | "Translate gives me the original text, the English, and the one thing I have to do." |
| 0:38 | Switch language to Ελληνικά / Español | "Same photo, my grandmother's language." |
| 0:48 | Click **Read aloud** | (browser speaks) "For anyone who'd rather be read to." |
| 0:58 | Switch to **Ask**, type "does this contain nuts?" | "And it answers the question the document doesn't spell out." |
| 1:10 | Cut to repo + `skills.md` | "MIT, no dependencies, and the same skill drops into any agent. Gemma 4 is doing the seeing — open weights, my laptop is just the window." |
| 1:20 | Kill the key / show demo mode | "And if the API dies mid-demo, it degrades to a labelled demo mode instead of a blank screen." |

Record with the browser window maximized and one window only. If the host allows a live demo, the
same sequence works with a real menu from the venue.

## Judge Q&A — have these answers ready

- **"Why not just Google Lens / Translate?"** Those translate words. This is scoped to *the next
  action* — the deadline, the fee, the allergen, the counter-vs-table rule — and it's four modes in
  one tap, in the reader's language, with a read-aloud path for people who can't parse fine print.
- **"Which model, and is it really Gemma?"** `gemma-4-26b-a4b-it`, called through
  `generativelanguage.googleapis.com/v1beta/models/...:generateContent` with an inline image part;
  the call is ~20 lines in `server.py` and the model ID is in the README.
- **"What's actually open source here?"** The app (MIT), the prompt contract, and a
  framework-agnostic `skills.md`; the model is Apache 2.0 Gemma 4. The whole loop is inspectable and
  the backend is swappable to a local checkpoint.
- **"Is the API key safe?"** It never touches the browser. The page only talks to a local proxy.
- **"What was the hard part?"** Restraint. The prompt is engineered to refuse to invent unreadable
  text, stay under 120 words, and lead with the practical consequence instead of a caption.
- **"What would you do with a week?"** Offline Gemma on-device (E2B/E4B are downloadable weights),
  multi-page documents, and community-maintained prompts for local document types (311 notices,
  landlord letters, school forms) — that's the real open-source contribution path.
- **"Does it handle [language X]?"** The model detects and transcribes; output languages tonight are
  the six most common in Astoria. Adding one is one line of config.
- **"What's the Gemini API project number?"** If asked (Best Use of Gemini API prize forms):
  AI Studio → Get API Key → Project Number. Have it on screen.

## Pre-submit checklist

- [ ] Submitted through the event page's **Challenges → Add Submission**, before the host's deadline.
- [ ] **Project link** = public GitHub repo (or the README URL) — public during judging and after.
- [ ] **Project name**, **description**, **technologies used**, **challenge(s) entered** filled in.
- [ ] **Demo URL** attached if you recorded one (keep it 60–90 s).
- [ ] Repo has a visible **LICENSE** and `.env` is **not** committed.
- [ ] README first screen says what it is, how to run it, and which Gemma model it uses.
- [ ] One or two screenshots in the README (menu photo + result) — lets judges see it without video.
- [ ] Every teammate registered + checked in on the event page.
- [ ] Test the exact demo path once on the presenting machine, on venue wifi. Then record the backup
      video before demos start at 9:15.

## Tonight's run sheet (demos at 9:15pm ET)

| Time | Do exactly this |
| --- | --- |
| **7:30** | PowerShell: `$env:GEMINI_API_KEY="..."` then `python tools/check_api.py`. It must print **PASS**. If not, follow the hint before touching anything else. |
| **7:45** | `python tools/selftest.py` → **69/69 PASS** offline (no key, no network). This proves the request shape. |
| **8:00** | `python server.py`, open <http://localhost:8000/?sample=menu>, click all four modes once on venue wifi. |
| **8:20** | **FREEZE** — no code changes after this point. Repo public, README first screen names `gemma-4-26b-a4b-it`, no `.env`. |
| **8:35** | Record the 60–90 s video (`static/samples/titlecard.png` → Explain → Translate → Read aloud → Ask). |
| **8:50** | Submit via the event page: **Challenges → Add Submission**. Attach the video URL, then open it once. |
| **9:15** | Demo with `?sample=menu` pre-loaded; recorded video one click away. |

Go/no-go at 8:20: `check_api.py` PASS → live demo with the key. FAIL → run in labeled demo mode and
say the word "demo" out loud; the UI labels it. Don't fight the network on stage.

## 20-minute emergency path (if 8:20 arrives and it's not working)

Do these five things in order and stop. Do not start a new feature or a refactor.

1. Keep the repo as is; delete nothing. Run `python server.py` with **no key** — the app returns labeled
   `[DEMO MODE]` output and the UI shows a "demo mode" pill. That is a legitimate, honest fallback.
2. Demo from `?sample=menu` (auto-loads the photo); no camera permission, no venue wifi needed.
3. Record 60 s in demo mode: Explain → Translate → Read aloud → Ask. Use it as the demo URL.
4. Confirm the submission minimums: public GitHub repo, visible LICENSE, README names
   `gemma-4-26b-a4b-it`, `.env` not committed.
5. Add one honest line to the submission: "Answers shown in labeled demo mode; the Gemma 4 vision
   path is in `server.py` and enabled by `GEMINI_API_KEY`." Judges score tech/design/completion/learning.
   A working, labeled fallback beats a blank screen.

If the key works by demo time, still present live — the fallback is for recording and for the stage.
