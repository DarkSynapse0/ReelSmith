# Step 1 — Setup

## Goal
Make sure the machine has everything needed, and create an isolated Python
environment so the project's packages don't interfere with the rest of the
system.

## What was built
- `requirements.txt` — the dependency list. At this stage just
  `faster-whisper`, which pulls in `ctranslate2`, `numpy`, `tokenizers`, etc.
- `venv/` — a virtual environment created with `python3 -m venv venv`.

## How it was tested
- Checked versions on the machine (Arch Linux):
  - Python **3.14.9**, pip, `venv` module — all present.
  - **FFmpeg n9.0.2** and **ffprobe** — both present.
- Installed `faster-whisper` into the venv.
- Ran `from faster_whisper import WhisperModel` to confirm the import works.

## Result / what worked
Everything was already installed — nothing had to be added to the OS. The venv
was created and `faster-whisper` imported successfully.

## Note / concern that turned out fine
Python 3.14 is very new, so we worried `ctranslate2`/`faster-whisper` might not
have prebuilt "wheels" for it yet (which would force a slow, error-prone source
build). **It was fine** — proper `cp314` wheels existed and installed cleanly.

## Install reference (other systems)
- **Arch:** `sudo pacman -S python ffmpeg`
- **Ubuntu/Debian:** `sudo apt install python3 python3-venv python3-pip ffmpeg`
- **macOS:** `brew install python ffmpeg`
- **Windows:** Python from python.org + `winget install Gyan.FFmpeg`
