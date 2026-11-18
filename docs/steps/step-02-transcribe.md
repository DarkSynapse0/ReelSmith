# Step 2 — Transcribe

## Goal
Turn a video's speech into text **with word-level timestamps**, and save it in
useful formats.

## What was built
- `src/videoclipper/utils.py` — shared helpers used by every later step:
  - `fail()` / `info()` / `ok()` — friendly messages (no scary tracebacks).
  - `check_ffmpeg()`, `check_file_exists()` — up-front checks with clear errors.
  - `run_ffmpeg()` — runs FFmpeg, hides its noise unless it fails.
  - `ffprobe_duration()` — media length in seconds.
  - `seconds_to_timestamp()` — formats time for SRT (`,`) and ASS (`.`).
- `src/videoclipper/transcribe.py` — the transcription pipeline:
  1. `extract_audio()` — FFmpeg → **16 kHz mono WAV** (what Whisper expects).
  2. `load_wav_as_array()` — read that WAV into a NumPy float array ourselves.
  3. `transcribe_audio()` — faster-whisper with `word_timestamps=True` and
     `vad_filter=True`.
  4. `save_json()` + `save_srt()` — write `<name>.transcript.json` (with every
     word's start/end) and a standard `<name>.srt`.

## Options
- `--language` — default `auto`; e.g. `ne` (Nepali), `en`, `hi`.
- `--model` — default `small`; `tiny`/`base`/`small`/`medium`/`large-v3`.
- `--output-dir` — where to save the JSON/SRT.

## Bug fixed — the PyAV / faster-whisper clash
On the first test run, faster-whisper crashed **inside its own audio loader**:

```
TypeError: open() got an unexpected keyword argument 'metadata_errors'
```

The newly installed **PyAV 19** changed an argument that faster-whisper's
`decode_audio` relies on. Rather than fight version pinning (older `av` may lack
Python 3.14 wheels), we **side-stepped the broken path entirely**: FFmpeg
already gives us a clean 16 kHz mono WAV, so we read it with Python's built-in
`wave` module into a NumPy array (16-bit samples ÷ 32768 → floats in −1..1) and
pass the **array** to `model.transcribe(...)`. No `av` in our path, no new
dependency. Full rationale: `docs/decisions/adr-001-read-wav-ourselves.md`.

## How it was tested
Generated a 14-second spoken sample video (via `espeak-ng` + FFmpeg) and ran:
```
python -m videoclipper.transcribe sample.mp4 --language en --model tiny
```

## Result / what worked
- All five spoken sentences transcribed correctly.
- The JSON contained **per-word start/end times** (e.g. `Hello` 0.00–0.42 s) —
  exactly what the caption step later depends on.
- A valid `.srt` was written.
- Nepali/Devanagari is preserved in the JSON because we write with
  `ensure_ascii=False`.
