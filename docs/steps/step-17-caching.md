# Step 17 — Caching downloads & transcripts

**Version:** 1.4.0 · **Module:** `src/reelsmith/cache.py`

## Goal
Stop re-doing the two slowest steps when the same video is processed more than
once: the **download** and the **transcription** (which can take ~20 minutes).

## What was built
A small `cache.py` module. Everything is stored inside each video's own folder:

```
clips/<video-name>/cache/
├── source.<ext>      ← the downloaded video (reused on the next run)
├── transcript.json   ← the transcription
└── meta.json         ← { "language": ..., "model": ... }
```

- `download_video()` now saves the download into `cache/`, and the pipeline
  reuses it on a re-run via `cache.find_source()`.
- The transcript is reused via `cache.load_transcript()` **only if the language
  and model match** the current request (stored in `meta.json`), so changing
  `--model` or `--language` correctly re-transcribes.
- `--no-cache` skips all of this and redoes the work from scratch.
- Wired into both the flag pipeline (`cli.run`) and the interactive TUI
  (`interactive.run_with_progress`), which shows "reused cached download /
  transcript" instead of running those stages.

## How it was tested
- **Run 1** (model `tiny`): transcribed and wrote `cache/` (`meta.json` +
  `transcript.json`; for a URL, also `source.mp4`).
- **Run 2** (same settings): printed "Using cached transcript" (and, for a URL,
  "Using cached download") and jumped straight to clipping — seconds instead of
  minutes.
- **Run 3** (model `base`): re-transcribed (cache correctly missed on model).
- **Run 4** (`--no-cache`): re-transcribed.
- Unit tests still pass.

## Result
Re-running a video to try different clip counts, vertical modes, or caption
styles is now nearly instant, because the download and transcript are reused.

## Limitations / future
- The cache lives in the output folder; deleting `clips/<name>/` clears it.
- It is keyed by language + model only — other transcription parameters are not
  part of the key (they don't currently change between runs).
