# Architecture

How the whole tool fits together. This is the "big picture" document — read it
first if you want to understand the project before diving into any single file.

---

## What it does, in one sentence

Take **one long video** (a local file or a URL) and produce **several short
vertical (9:16) clips** with **burned-in, word-by-word captions**, picking the
"best" moments automatically — all **locally and for free**.

---

## Data flow

```
          ┌─────────────────────────────┐
  INPUT   │  local file  OR  video URL   │
          └──────────────┬──────────────┘
                         │
              is it a URL (http/https)?
                         │
             ┌───────────┴───────────┐
            yes                      no
             │                        │
             ▼                        │
     ┌───────────────┐                │
     │ download.py   │  yt-dlp, ≤1080p│
     │ (Step 0)      │                │
     └───────┬───────┘                │
             └───────────┬────────────┘
                         ▼
             ┌───────────────────────┐
             │ transcribe.py         │  FFmpeg extracts 16kHz mono WAV
             │ (Steps 1–2)           │  → read WAV with numpy
             │                       │  → faster-whisper (word timestamps)
             └───────────┬───────────┘
                         │  transcript (segments + per-word timings)
                         ▼               saves: <name>.transcript.json, <name>.srt
             ┌───────────────────────┐
             │ moments.py            │  build 20–60s sentence-aligned candidates
             │  + scoring.py         │  score each, pick top-N non-overlapping
             │ (Step 3)              │
             └───────────┬───────────┘
                         │  list of chosen clips (start, end, score, text, words)
                         ▼
             ┌───────────────────────┐   for each chosen clip:
             │ video.cut_clip        │  (Step 4) cut with buffer, re-encode
             │ video.make_vertical   │  (Step 5) 1080×1920 crop / blur / track
             │   └─ reframe.py       │  (track mode) build a crop path that pans to the speaker
             │ captions.generate_ass │  (Step 6) build ASS word-highlight file
             │ video.burn_captions   │  (Step 6) render captions into the clip
             └───────────┬───────────┘
                         ▼
          ┌─────────────────────────────┐
  OUTPUT  │ clip_01.mp4, clip_02.mp4 …   │
          │ summary.txt, summary.json    │
          │ <name>.transcript.json, .srt │
          └─────────────────────────────┘
```

`cli.py` (Step 7) is the conductor that calls everything above in order. In the
diagram above, each labelled module (`download.py`, `transcribe.py`, …) lives
inside the package folder `src/reelsmith/` — the short names are used as
labels to keep the boxes readable.

`cache.py` sits beside the download and transcribe steps: before downloading or
transcribing, the pipeline checks `clips/<name>/cache/` and reuses a previous
`source.<ext>` / `transcript.json` when present (the transcript only if its
saved language + model match). `--no-cache` bypasses it.

There are **two front-ends** that feed this pipeline:

- **Flags** — `reelsmith my_video.mp4 --language ne …` (parsed by `cli.main`),
  which calls `cli.run(...)`.
- **Interactive TUI** — `reelsmith` with no video (or `-i`) launches
  `interactive.launch()`. In a real terminal it shows a **rich + questionary**
  menu (banner, arrow-key option lists, a job-configuration panel) and then runs
  the pipeline with **staged progress bars** via `interactive.run_with_progress()`.
  When the program is **not a TTY** (piped/non-interactive) it falls back to
  simple typed prompts and the normal logging pipeline `cli.run(...)`.

Either way the same building-block modules (`download`, `transcribe`, `moments`,
`video`, `captions`) do the actual work.

---

## Project layout

```
OpenSourceClipping/
├── src/reelsmith/        ← the package (all the code)
│   ├── cli.py               ← the one command (formerly clipper.py)
│   ├── interactive.py       ← the polished TUI menu (rich + questionary)
│   ├── __main__.py          ← enables `python -m reelsmith`
│   ├── __init__.py          ← package marker + version
│   ├── download.py  transcribe.py  moments.py  scoring.py
│   ├── video.py  captions.py  reframe.py  utils.py
│   └── models/             ← bundled YuNet face model (face_detection_yunet.onnx)
├── tests/                   ← test_basic.py (no video needed)
├── docs/                    ← this documentation
├── samples/                 ← test inputs (git-ignored)
├── clips/                   ← generated output, one folder per video (git-ignored)
├── pyproject.toml           ← installable; defines the `reelsmith` command
├── requirements.txt
└── README.md  LICENSE  CHANGELOG.md  ROADMAP.md  PROGRESS.md
```

Run it with the installed command `reelsmith ...` or equivalently
`python -m reelsmith ...` (after `pip install -e .`).

### External dependencies

All free and open source; installed automatically by `pip install -e .`.
FFmpeg/ffprobe are separate **system** programs (not pip packages).

| Package | Used for |
|---------|----------|
| `faster-whisper` | speech-to-text with word timestamps (pulls in NumPy) |
| `yt-dlp` | downloading a video from a URL |
| `opencv-python-headless` | face detection for `--vertical track` |
| `rich` | the TUI banner, panels, and progress bars |
| `questionary` | the arrow-key option menus |

---

## The modules

All modules live in `src/reelsmith/`.

| File | Role | Key functions |
|------|------|---------------|
| **`cli.py`** | The one command (was `clipper.py`). Parses flags, orchestrates the whole pipeline, writes outputs + summary. `run()` takes a `captions_on` flag (off ⇒ the vertical clip becomes the final clip). | `run(...)`, `main()` |
| **`interactive.py`** | Alternate front-end: a **rich + questionary** TUI (banner, arrow-key menus, job panel, staged progress bars, results panel). In a real terminal it collects settings and runs the pipeline with progress bars; when not a TTY it falls back to simple typed prompts + `cli.run()`. Launched when no video is given or `-i`/`--interactive` is passed. | `launch()`, `run_with_progress()`, `_pretty_collect_settings()`, `_plain_collect_settings()` |
| **`download.py`** | If the input is a URL, download it with yt-dlp (≤1080p). Also decides each video's output folder: every video gets its own `clips/<video-name>/` (local ⇒ filename; URL ⇒ title + id), so results never mix. | `is_url()`, `download_video()`, `default_output_dir()`, `url_video_name()`, `_sanitize_name()` |
| **`transcribe.py`** | Extract audio, transcribe with faster-whisper, save JSON + SRT. Also a **mixed-language** path (`--language mixed`): VAD-split into utterances → detect + transcribe each in its own language → stitch (each segment tagged with its `language`). | `extract_audio()`, `load_wav_as_array()`, `transcribe_audio()`, `transcribe_audio_multilang()`, `transcribe_video()` |
| **`moments.py`** | Build sentence-aligned 20–60s candidates and pick the best N (non-overlapping). | `build_candidates()`, `pick_best()` |
| **`scoring.py`** | The heuristics that score a segment. **Deliberately swappable.** | `score_segment()` + per-heuristic helpers, `WEIGHTS` |
| **`video.py`** | All FFmpeg video operations: cut, vertical (`crop`/`blur`/`track`), burn captions. | `cut_clip()`, `make_vertical()`, `burn_captions()` |
| **`reframe.py`** | Speaker tracking: detect the main face (OpenCV YuNet) and build a **time-varying** crop path that pans to follow them (smoothing, cut-snap, centre-fallback). Also a `diagnose()` CLI, and quietens OpenCV's log output. Used by `--vertical track`. | `compute_crop_plan()` (dynamic), `compute_crop_box()` (legacy fixed), `diagnose()`, `_MODEL_PATH` |
| **`captions.py`** | Build the ASS caption file (word highlighting + animation styles). | `generate_ass()`, `_events_classic()`, `_events_bigword()`, `CAPTION_STYLE` |
| **`utils.py`** | Shared helpers: friendly errors, environment checks, running FFmpeg, time formatting. | `fail/info/ok`, `check_ffmpeg()`, `run_ffmpeg()`, `ffprobe_duration()`, `seconds_to_timestamp()` |
| **`models/`** | Bundled face-detection model (`face_detection_yunet.onnx`, ~232 KB). Not code — ships via `package-data`. | — |

---

## How the modules connect

- **`cli.py`** imports and drives `download`, `transcribe`, `moments`,
  `video`, and `captions` (via package-relative `from . import ...`). It is
  mostly glue — the heavy logic lives in the other modules, which keeps the
  pipeline readable. `cli.run()` skips the caption step when `captions_on` is
  `False` (it just moves the vertical clip to the final output).
- **`interactive.py`** is an alternate front-end, **imported lazily** inside
  `cli.main()` (only when the menu is actually needed). `launch()` picks the UI:
  in a real terminal it uses the **rich + questionary** menu and then
  `run_with_progress()` (which calls the same building-block functions as
  `cli.run()`, just wrapped in progress bars); when not a TTY it gathers settings
  with simple prompts and calls `cli.run(...)`. Either way the flags path and the
  menu path share the same pipeline code.
- **`utils.py`** is imported by nearly everything; it's the single place for
  friendly error messages and FFmpeg calls so behavior is consistent. It also
  holds the **`QUIET`** flag: when `True`, `info()`/`ok()` (and the per-segment
  transcript print) stay silent, which lets `interactive.run_with_progress()`
  show clean progress bars without log lines underneath. Likewise
  `download.download_video(..., quiet=True)` hides yt-dlp's own output.
- **`moments.py`** imports **`scoring.py`** and calls `score_segment()` on each
  candidate. This is the one seam designed for replacement.
- **`transcribe.py`** produces the transcript dictionary (`segments`, each with
  `words` that have absolute `start`/`end` times). Everything downstream relies
  on those **per-word timings** — captions especially. When `--language mixed`
  is used, it instead splits the audio into utterances (VAD), auto-detects and
  transcribes each on its own, and stitches them back with offset timings — each
  segment also carries a `language`, and the top-level language is `"mixed"`.
  (Handles switching **between** utterances; not **within** one.)
- **`captions.py`** receives the full word list plus a clip's real (buffered)
  start/end, filters to words inside the clip, shifts them to start at 0, and
  writes the ASS file. `video.burn_captions()` then renders it.
- **`reframe.py`** is imported **lazily** by `video.make_vertical()` — only when
  `--vertical track` is used — so the heavy OpenCV library isn't loaded for the
  `crop`/`blur` modes. It returns a **list of crop keyframes** that `track` mode
  feeds to FFmpeg via a `sendcmd` file (run with `run_ffmpeg(cwd=…)` so the
  filter sees a safe bare filename). If it finds no face, `make_vertical()`
  falls back to a
  plain center crop.

---

## Key design decisions (summary)

Full write-ups are in `docs/decisions/`. The headlines:

1. **Read the WAV ourselves (numpy), not via faster-whisper's loader.**
   Avoids a hard crash from a PyAV version clash, and adds no dependency.
   → `adr-001-read-wav-ourselves.md`

2. **Center crop first, then speaker-tracking, then dynamic panning.**
   Started with simple center-crop geometry; `--vertical track` (fixed crop
   around the detected face) landed in 0.5.0; in 1.3.0 it became **dynamic
   panning** that follows a moving speaker via FFmpeg `sendcmd`.
   → `adr-002-center-crop-vs-tracking.md`, `adr-006-yunet-face-detection.md`,
   `adr-009-dynamic-tracking.md`

3. **ASS subtitles for captions.**
   Needed per-word color changes and animation (`\t`, `\fscx`, …) that plain
   SRT can't do; libass renders Devanagari correctly.
   → `adr-003-ass-for-captions.md`

4. **Local & free only — no paid APIs.**
   Privacy, zero cost, works offline after first download; the whole reason the
   project exists.
   → `adr-004-local-free-only.md`

5. **Scoring is swappable.**
   `scoring.py` sits behind one function so the "intelligence" can be upgraded
   (local LLM, learned weights) without disturbing the rest of the pipeline.

6. **YuNet (bundled) for face detection.**
   OpenCV 5 dropped the old Haar cascades, so we use the modern YuNet DNN
   detector and ship its small `.onnx` model inside the package (offline, no
   runtime download). OpenCV is imported only when tracking is used, and its log
   output is quietened (`OPENCV_LOG_LEVEL=ERROR`) so it can't garble the display.
   → `adr-006-yunet-face-detection.md`

7. **Dynamic crop via FFmpeg `sendcmd`.**
   Rather than re-implement video encoding, the panning crop is expressed as a
   list of keyframes written to a `sendcmd` file that drives FFmpeg's `crop`
   filter over time — simple, fast, and reuses the tool we already depend on.
   → `adr-009-dynamic-tracking.md`

7. **rich + questionary for the interactive TUI.**
   The polished menu, panels, and progress bars use `rich`; the arrow-key option
   lists use `questionary`. The UI detects whether it has a real terminal and
   falls back to plain typed prompts otherwise, and uses the `utils.QUIET` flag
   to keep progress output clean.
   → `adr-007-rich-questionary-tui.md`

8. **Mixed-language via VAD + per-utterance auto-detect.**
   For code-switching videos (`--language mixed`), split the audio into
   utterances and let Whisper detect/transcribe each one's language separately,
   then stitch. Handles between-sentence switching; within-sentence is a known
   limit. → `adr-008-mixed-language-vad.md`

---

## Fixed sizes & defaults (so the docs and code agree)

| Thing | Value | Where |
|-------|-------|-------|
| Vertical output | 1080 × 1920 | `video.VERTICAL_WIDTH/HEIGHT` |
| Clip length range | 20–60 s | `moments.MIN_SECONDS/MAX_SECONDS` |
| Cut buffer | 0.4 s each side | `video.DEFAULT_BUFFER` |
| Default model | `small` | `cli.py` |
| Default language | `auto` | `cli.py` |
| Mixed-language mode | `--language mixed` | `transcribe.transcribe_audio_multilang()` |
| Default clips | 5 | `cli.py` |
| Default vertical mode | `crop` | `cli.py` |
| Vertical modes | `crop` / `blur` / `track` | `video.make_vertical()` |
| Default caption style | `classic` | `cli.py` |
| Captions on by default | yes (`--no-captions` to skip) | `cli.run(captions_on=True)` |
| Download cap | ≤ 1080p | `download.py` |
| Output folder | `clips/<video-name>/` | `download.default_output_dir()` |
| Caption font | Noto Sans Devanagari | `captions.CAPTION_STYLE` |
| Face sampling rate | ~6 frames/sec (tracking) | `reframe.compute_crop_plan()` |
| Face model | YuNet (`face_detection_yunet.onnx`) | `reframe._MODEL_PATH` |
