# Step 10 — Restructure into a standard `src/` package

## Goal
Turn the flat pile of scripts (everything in the repo root) into the standard
Python **`src/` package layout** so the project is a proper, installable
product — discoverable, testable, and runnable as a real command — without
changing any behavior.

## What changed
- **Moved all modules into `src/videoclipper/`**: `transcribe.py`, `moments.py`,
  `scoring.py`, `video.py`, `captions.py`, `download.py`, `utils.py`.
- **Renamed `clipper.py` → `src/videoclipper/cli.py`** (its `main()` is the
  console entry point).
- **Imports became package-relative**: `import utils` → `from . import utils`,
  `import scoring` → `from . import scoring`, and the same in `cli.py` for all
  the modules it drives.
- Added **`src/videoclipper/__init__.py`** (holds `__version__ = "0.3.0"`) and
  **`src/videoclipper/__main__.py`** (so `python -m videoclipper` works).
- Added **`pyproject.toml`**: makes the project installable with
  `pip install -e .`, declares dependencies (`faster-whisper`, `yt-dlp`), sets
  the MIT license and Python ≥ 3.9, and defines the console command
  `videoclipper` → `videoclipper.cli:main`.
- Added **`LICENSE`** (MIT), **`.gitignore`**, a **`tests/`** folder with
  `test_basic.py`, and **`samples/`** + **`output/`** folders.

## How to run now
```bash
pip install -e .                         # once
videoclipper my_video.mp4 --language ne  # the console command
python -m videoclipper my_video.mp4      # identical, via the module
```
(Previously this was `python clipper.py my_video.mp4`.)

## How it was tested
1. **`pip install -e .`** — completed successfully (`videoclipper-0.3.0`), and
   the `videoclipper` command appeared in `venv/bin/`.
2. **Unit tests** — `python tests/test_basic.py` → all **3 tests pass**
   (timestamp formatting; `score_segment` returns `(float, dict)` and rewards a
   question; `pick_best` keeps clips within 20–60 s and non-overlapping).
3. **Both run methods** — `videoclipper --help` and
   `python -m videoclipper --help` both print the usage correctly.
4. **End-to-end** — a full run via the installed `videoclipper` command
   (transcribe → find moment → cut → vertical → captions) produced a valid
   **1080×1920** captioned clip, confirming the package-relative imports didn't
   break the pipeline.

## Result / what worked
The project is now a clean, installable package. All three run methods work, the
unit tests pass, and the full pipeline still produces correct vertical captioned
clips. ✅

See also: [`adr-005-src-layout.md`](../decisions/adr-005-src-layout.md).
