---
name: astoria-lens
description: Turn a photo of anything in the neighborhood — a menu, a sign, a flyer taped to a pole, a notice, a receipt, a label, a handwritten note — into clear, practical guidance in the reader's own language. Use when someone needs to understand a real-world document but the language, print, or context is a barrier.
version: 0.1.0
license: MIT
model: gemma-4-26b-a4b-it   # open-weights Gemma 4 via the Gemini API
---

# Astoria Lens

A vision skill for a multilingual neighborhood. The model is shown one photo and asked one small,
practical question: *what does this mean, and what should I do about it?*

Astoria, Queens is one of the most linguistically diverse places on earth. The gap this closes is
not "read text" — it is "the sign is in Greek, the flyer is bureaucratic, the notice is taped at
chest height and the reader is 80 years old."

## When to use this skill

Use it when **all** of the following are true:

- The input is an image of a real-world artifact: menu, storefront sign, poster, flyer, notice,
  receipt, product label, business card, handwritten note, transit sign, mail.
- The user needs the *meaning* or the *next action*, not a description of the pixels.
- The output should be short enough to read on a phone, standing on a sidewalk.

Do **not** use it for: purely aesthetic captioning, interior design critique, identifying people,
scanning long documents (use an OCR/document skill), or anything where the image contains sensitive
personal data the user has not agreed to share.

## Inputs

| Field | Required | Notes |
| --- | --- | --- |
| `image` | yes | JPEG/PNG/WebP, downscaled to ≤ 1280 px on the long edge, ≤ 8 MB. |
| `mode` | yes | One of `explain`, `translate`, `read`, `ask`. |
| `lang` | no | Output language: `en`, `es`, `el`, `ar`, `bn`, `zh`. Defaults to `en`. |
| `question` | when `mode=ask` | Free text, ≤ 500 chars. |

## Modes

- **`explain`** — *what is this and what do I do?* One-line identification, up to three bullets on
  the facts that change behavior (prices, dates, deadlines, fees, allergens, hours, phone number,
  who to call), then the next action.
- **`translate`** — detect the language, transcribe the legible text exactly in its original script,
  translate it into `lang`, then one line on what the reader must know or do.
- **`read`** — a clean read-aloud script for a screen reader or a tired pair of eyes: plain
  sentences only, no markup, numbers and addresses spoken the way a person says them, under ~60
  words, one short line at the end on what to do.
- **`ask`** — answer only the question that was asked: direct answer first, one line on where in the
  image it is written; if the image does not answer it, say so and name what is missing.

## How to run it

The skill is packaged two ways, and both use the same prompt contract:

1. **Local web app** (the hackathon demo): `python server.py`, open `http://localhost:8000`,
   point a camera or drop a photo. The server holds the API key and calls
   `POST {API_BASE}/models/gemma-4-26b-a4b-it:generateContent` with `inline_data` for the image.
2. **Agent tool**: expose `analyze(image, mode, lang, question)` as a single tool. Any agent
   harness that can call a vision model can load this file and use the same modes.

## Instructions

1. Always open with what the object actually is, in one short line. Never start with "This image
   shows" or an apology.
2. Transcribe exactly what is legible. Do **not** invent, complete, or translate text you cannot
   read. Name the part that is unreadable (e.g. "the last line is out of focus").
3. Prefer the practical reading over the literal one: a sale price, a deadline, an allergy risk,
   a phone number that is actually staffed, a door that is actually open.
4. Keep it under ~120 words unless the reader asks for more — Read aloud under ~60, Ask under ~80.
   No preamble, no closing offer to help.
5. Stay in the requested output language, including headers.
6. For `read`, emit plain sentences only — no markdown, no bullets, no symbols — with numbers,
   prices, times, and addresses spoken the way a person says them, ending with one short line on
   what to do. For `ask`, answer only the question asked; do not summarize the whole image.

## Output contract

```
WHAT IT IS              <- one line (explain)
WHAT MATTERS            <- up to three bullets, only facts on the page
WHAT TO DO NEXT         <- one or two concrete lines

LANGUAGE: <detected>    <- translate, then three blocks:
ORIGINAL                <- legible text exactly, in its original script
TRANSLATION (<lang>)    <- the same text in the requested language
WHAT TO DO              <- one line

<plain sentences>       <- read, under ~60 words, no headers or lists

<direct answer>         <- ask, two to four plain sentences, no headers
```

The web app renders light markdown (`###`, `-`, `**bold**`) and treats plain `ALL-CAPS` lines as
section headers, so the model may use those markers.

## Failure behaviour

- Unreadable image → say so plainly and ask for a sharper photo; do not guess.
- Model blocked or rate-limited → surface the reason to the user, keep the photo on screen so a
  retry costs one click.
- No API key → run in demo mode with recorded sample output, clearly labelled `[DEMO MODE]`, so a
  live demo never dies on a missing environment variable.

## Why this is an open-source AI project

- The model is **Gemma 4**, released under Apache 2.0 open weights; this app calls the hosted
  Gemini API today and can point at a self-hosted Gemma endpoint by changing one environment
  variable (`GEMINI_API_BASE`).
- The app itself is MIT licensed, standard-library only, and designed to be read end-to-end in one
  sitting — the prompt, the wrapper, and the UI all ship together.
- The skill file is framework-agnostic on purpose: no vendor SDK is required to reuse it.
