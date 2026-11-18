# Roadmap

Where the project is heading. Everything here keeps the core rules:
**free, open source, and runs locally — no paid APIs.**

**Status legend**
- 🟡 **Planned** — agreed we want it, clear path to build it.
- ⏸️ **Deferred** — good idea, consciously postponed until it's actually needed.
- 💡 **Idea** — on the radar, not fully scoped yet.

---

## ✅ Shipped — speaker-tracking reframe (fixed crop)

The first version of smart reframing landed in **0.5.0** as `--vertical track`.
It detects the speaker's face with OpenCV's YuNet detector and crops a 9:16
window around them (instead of the middle), falling back to a center crop when
no face is found. See `docs/steps/step-11-speaker-tracking.md` and
`docs/decisions/adr-006-yunet-face-detection.md`.

What it does **not** do yet is listed under Planned below.

---

## ✅ Shipped — mixed-language transcription (segment-level)

Landed in **1.1.0** as `--language mixed`, for videos that switch languages
(e.g. Hindi + English). It splits the audio into utterances (VAD), **detects the
language of each utterance** on its own, and transcribes each in that language —
so a Hindi sentence is written in Devanagari and an English sentence in English.
It handles switching **between** sentences; switching **within** one sentence is
still detected as a single language (see the Idea below). See
`docs/steps/step-14-mixed-language.md` and
`docs/decisions/adr-008-mixed-language-vad.md`.

---

## ✅ Shipped — dynamic panning (follow a moving speaker)

Landed in **1.3.0**. `track` mode no longer uses one fixed position — it builds
a **per-time path** of the face, **smooths** it so the crop glides, **snaps** at
scene cuts (big jumps), **holds** through brief look-aways, and **drifts to
centre** during faceless stretches. FFmpeg animates the crop with `sendcmd`.
See `docs/steps/step-16-dynamic-tracking.md` and
`docs/decisions/adr-009-dynamic-tracking.md`.

> Note: **screen-recording / b-roll-heavy** videos have little or no face to
> follow — `crop` or `blur` is the right choice there. The diagnostic
> `python -m reelsmith.reframe "<video.mp4>"` reports which case a video is.
> The diagnostic reads video directly, so it can't decode AV1/VP9 `.webm`
> sources (the normal pipeline re-encodes clips to H.264 first, so this only
> affects running the diagnostic on a raw download).

## 🟡 Planned

### Active-speaker selection among multiple faces
When several faces are on screen (an interview/panel), today we just pick the
**largest** face. Smarter: detect **who is actually talking** (e.g. mouth
movement, or correlate with the audio) and track that person. Harder, but a big
quality jump for multi-person videos.

### Smarter moment-picking via a local LLM
The current `src/reelsmith/scoring.py` uses simple word-list heuristics. A small **local LLM
(via [Ollama](https://ollama.com/))** could read each candidate segment and
rate how "hooky" / self-contained it is, then blend that with the heuristics.
Still 100 % free and local.

**Why it's clean to add:** `src/reelsmith/scoring.py` is deliberately swappable — anything
that implements `score_segment(segment) -> (score, breakdown)` drops in without
touching `src/reelsmith/moments.py`.

### More animated caption effects
We shipped `bigword`. The researched menu of additional styles (all doable with
free ASS tags, no new dependencies):

| Effect | What it looks like |
|--------|--------------------|
| Word pop / scale bounce | active word briefly grows as spoken |
| Karaoke color sweep | color fills across each word in time (`\kf`) |
| Keyword emphasis | "power words" get extra size/color/glow |
| Highlight box | solid colored bar behind the active word |
| Slide / pop up | new line slides up into place (`\move` + `\fad`) |
| Fade in/out | gentle per-word/line fade (`\fad`) |

Each would be a new `--caption-style` value.

---

## ⏸️ Deferred

### Audio-first + section download (download performance)
Right now a URL input downloads the **whole video** before anything else. For
long videos on slow internet this is wasteful, because we only need:
- the **audio** to transcribe and pick moments (tiny), and
- the **video** only for the clips we actually keep.

**Planned approach when we build it:**
1. Download **audio only** (fast, small) → transcribe → pick best moments.
2. Download **only the selected time ranges** of full-quality video
   (`yt-dlp --download-sections`).

For a 1-hour podcast → five 30 s clips, that's ~2.5 min of video downloaded
instead of 60. **Trade-off:** `--download-sections` reconnects per clip, so for
*short* videos it can be marginally slower than one plain download. Smart rule:
short video → whole download; long video → audio-first + sections.

**Why deferred:** transcription is usually the real bottleneck, not download,
and short videos don't benefit. Revisit when clipping long videos becomes
common.

### Translation (transcribe in one language, caption in another)
*(Note: **transcribing** a multi-language video already works via
`--language mixed`, shipped in 1.1.0. This item is about **translating** the
speech into a different language, which is separate.)*
- **Any language → English:** ✅ easy — Whisper has a built-in translate mode.
  Would be a `--translate` flag.
- **English → Nepali (or other targets):** needs an **extra offline translator**
  (e.g. **Argos Translate** or **NLLB**), because Whisper only translates *into*
  English. Still free/local.
- **Honest catch:** translated word order differs from the audio, so the
  **word-by-word caption highlighting won't line up**. Translated clips would
  fall back to **line/sentence-at-a-time** captions instead of karaoke-style.

### Caching downloads — ✅ Shipped in 1.4.0
Re-processing the same video now reuses the cached download **and** the
transcript (keyed by language + model), in `clips/<name>/cache/`. Use
`--no-cache` to redo from scratch. See the CHANGELOG for details.

---

## 💡 Ideas

### Object / product tracking (instead of a face)
An optional `track` variant that follows a **chosen object** (e.g. a product)
rather than the speaker. This is **harder than face tracking**: OpenCV's
built-in detectors only know generic categories, so following an *arbitrary*
product needs an **open-vocabulary detector** (e.g. Grounding-DINO) or a
vision-language model to identify it, then a fast tracker to follow it between
checks. Heavier and slower — a stretch goal, likely limited to common object
types first.

### Within-sentence (word-level) code-switching
`--language mixed` (1.1.0) detects language **per utterance**, so a single
sentence that mixes languages (e.g. *"यह important point है"*) is still written
in **one** script. True word-level code-switching — keeping each word in its own
script within one sentence — is a research-grade problem. Possible future
approaches: a dedicated code-switching ASR model, or a dual-pass merge (one
Hindi pass + one English pass) reconciled per word by confidence. Harder and
less reliable; a stretch goal.

### "ClipAnything"-style visual search (hard, later)
Find moments by **visual/content** understanding, not just the transcript
(e.g. "find all the laughing reactions"). Needs vision models and is
significantly more complex — a long-term stretch goal.

### Post-generation clip selection
The interactive menu (0.6.0) picks settings **before** anything runs. A natural
extension: **after** the clips are generated, show a list of them with their
scores (and maybe a quick preview) and let the user **keep or delete** each one
— so you choose "what I need / what I don't need" from the actual results, not
just up front. Pairs naturally with the interactive mode and the existing
`summary.txt` scores.

### Learn-from-yourself scoring
Keep the clips you actually publish and how they performed, then tune the
scoring `WEIGHTS` (or train a small local model) to match your taste.

### Extra niceties seen in commercial tools
Auto hook-titles, emoji/stickers (note: color emoji doesn't render well in
ASS/libass — would need image overlays), auto B-roll, direct posting to social
platforms.

---

## How this compares to Opus Clip

This project is a **free, local, private** reimplementation of Opus Clip's core
pipeline. Most of the pipeline already exists, and **speaker-tracking reframe**
now ships with **dynamic panning** too. The biggest remaining quality gaps are
**active-speaker tracking** and **smarter moment-picking** — both on the roadmap
above, both achievable for free and locally.
