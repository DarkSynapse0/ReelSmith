# Contributing / Developer Guide

This is a beginner-friendly project, and this guide is written to match. If
you're new to Python, you can still follow along — each section is small.

---

## 1. Set up your environment

You need **Python 3** and **FFmpeg** installed (see [README](README.md) for OS
install commands). Then:

```bash
# Create the virtual environment (once)
python3 -m venv venv

# Activate it (do this every new terminal session)
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install the tool in editable mode. This reads pyproject.toml, pulls in the
# dependencies, and creates the `reelsmith` command. "-e" (editable) means
# any code change you make takes effect immediately, with no reinstall.
pip install -e .
```

(If you only want the libraries without installing the command, `pip install
-r requirements.txt` still works — but `pip install -e .` is the recommended
way, since it gives you the `reelsmith` command used throughout these docs.)

For Nepali captions, make sure a Devanagari font is installed (e.g. **Noto Sans
Devanagari** — usually already present on Linux; `sudo pacman -S noto-fonts` or
`sudo apt install fonts-noto`).

---

## 2. Project layout

The code is a Python package under `src/reelsmith/`:

```
OpenSourceClipping/
├── src/reelsmith/
│   ├── cli.py          The one command. Runs the whole pipeline. (was clipper.py)
│   ├── interactive.py  The polished TUI menu (rich + questionary) + progress bars.
│   ├── download.py     Downloads a video from a URL (yt-dlp).
│   ├── transcribe.py   Audio extract + faster-whisper → JSON + SRT.
│   ├── moments.py      Split into 20–60 s segments, pick the best N.
│   ├── scoring.py      The scoring heuristics — the part you'll most often tweak.
│   ├── video.py        FFmpeg: cut, make vertical (crop/blur/track), burn captions.
│   ├── reframe.py      Face detection (OpenCV YuNet) for `--vertical track`.
│   ├── captions.py     Build the ASS caption file; caption styling lives here.
│   ├── utils.py        Shared helpers (friendly errors, FFmpeg, time, QUIET flag).
│   ├── models/         Bundled YuNet face model (face_detection_yunet.onnx).
│   ├── __main__.py     Enables `python -m reelsmith`.
│   └── __init__.py     Marks the folder as a package (holds the version).
├── tests/              Quick tests that don't need a video (test_basic.py).
├── docs/               This documentation.
├── samples/            Put test videos here (ignored by git).
├── clips/              Generated output — one folder per video (ignored by git).
├── pyproject.toml      Makes it installable; defines the `reelsmith` command.
├── requirements.txt    The libraries (faster-whisper, yt-dlp, opencv, rich, questionary).
└── README.md  LICENSE  CHANGELOG.md  ROADMAP.md  PROGRESS.md
```

Deeper explanations: [ARCHITECTURE.md](ARCHITECTURE.md) and `docs/`.

---

## 3. Run it

```bash
# From a local file
reelsmith my_video.mp4 --language en --clips 3

# From a URL
reelsmith "https://www.youtube.com/watch?v=XXXX" --language en

# Fast iteration while developing: use a tiny model and few clips
reelsmith my_video.mp4 --model tiny --clips 1
```

Tip: during development, add `--keep-intermediate` to inspect the `work/` files
(raw cut, vertical version, and the generated `.ass` caption file).

You can also run a single stage on its own, e.g.:
```bash
python -m reelsmith.transcribe my_video.mp4 --language ne --model small
```

---

## 4. Common tasks

### Add a new caption style
Caption look-and-feel lives in `src/reelsmith/captions.py`.

1. Add a new event-builder function next to `_events_classic` and
   `_events_bigword`, e.g. `_events_karaoke(clip_words, timings, style)`. It
   returns a list of `Dialogue: ...` lines (ASS events).
2. In `generate_ass(...)`, add a branch:
   ```python
   elif animation == "karaoke":
       lines += _events_karaoke(clip_words, timings, style)
   ```
3. In `src/reelsmith/cli.py`, add your style name to the `--caption-style` `choices`.

ASS animation reference used so far: `\t` (animate over time), `\fscx`/`\fscy`
(scale %), `\pos`/`\an` (position/anchor), `\1c` (text color), `\fad` (fade).

### Change how captions look (no new style)
Edit the `CAPTION_STYLE` dict at the top of `src/reelsmith/captions.py`: `font`, `font_size`,
`highlight_color`, `margin_vertical`, `words_per_line`, etc. Use the `rgb(r,g,b)`
helper for colors.

### Swap in smarter moment-picking
`src/reelsmith/scoring.py` is **deliberately swappable**. Keep the same contract:
```python
def score_segment(segment) -> (total_score: float, breakdown: dict):
    ...
```
`segment` has `start`, `end`, `text`, and `words` (each word with `start`/`end`).
As long as you return a number and a dict, `src/reelsmith/moments.py` needs no changes. You
could replace the heuristics with a local LLM call (e.g. Ollama) here.

### Tune which clips get picked (without rewriting scoring)
Edit the `WEIGHTS` dict in `src/reelsmith/scoring.py`, or extend the word lists
(`EMPHATIC_WORDS`, `EMPHATIC_DEVANAGARI`, `QUESTION_DEVANAGARI`, …).

### Add a command-line option
Options are defined in `main()` in `src/reelsmith/cli.py` with `argparse`. Add the
`add_argument(...)`, then pass it through to `run(...)`.

---

## 5. Coding style

This codebase intentionally favors clarity over cleverness:

- **Simple and readable** — plain Python, small functions, obvious names. The
  author is a beginner; keep it approachable.
- **Comment the "why"** — explain *why* a line exists (especially FFmpeg flags
  and ASS tags), not just what it does.
- **Friendly errors** — never dump a raw traceback at the user. Use
  `utils.fail("plain-language message")` for anything a user could hit (missing
  file, missing FFmpeg, bad URL). Use `utils.info()` / `utils.ok()` for progress.
- **Keep FFmpeg in `src/reelsmith/video.py`** and run commands via `utils.run_ffmpeg()` so
  errors are handled consistently.
- **One job per module** — don't mix, say, scoring logic into `src/reelsmith/moments.py`.
- **Preserve Unicode** — write JSON with `ensure_ascii=False` so Devanagari
  stays intact.

---

## 6. Testing as you go

There's a small test suite for the logic that doesn't need a video
(`tests/test_basic.py`): timestamp formatting, that scoring returns
`(float, dict)` and rewards a question, and that `pick_best` respects the
20–60 s length limits and never overlaps clips. Run it two ways:

```bash
python tests/test_basic.py      # plain, no extra tools needed
python -m pytest                # if you have pytest installed
```

Beyond that, we test each change by running it end-to-end on a short clip and
checking the output (resolution with `ffprobe`, a burned frame with
`ffmpeg -frames:v 1`, the transcript JSON/SRT, and `summary.txt`). When you add
a feature, run both the unit tests and a small sample before moving on — that's
how every existing step was verified (see `docs/steps/`). If you add logic that
can be checked without a video, add a `test_...` function to
`tests/test_basic.py`.
