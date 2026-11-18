# Step 15 — Per-video output folders (`clips/<name>/`)

## Goal
Keep each video's results **separate**. Different videos should never share a
folder or overwrite each other's files.

## What changed
**The problem.** Every URL download went into a single shared `downloaded_clips/`
folder, writing `source.mp4`, `clip_01.mp4`, `summary.txt`, etc. So running the
tool on a **second** URL video **overwrote** the first one's results. Local files
went to `<base>_clips/` in the current directory.

**The fix.** Every video now gets its **own folder** under a top-level `clips/`
directory:

```
clips/
├── My_Talk/                       ← a local file "My Talk.mp4"
│   ├── clip_01.mp4 …
│   ├── summary.txt / summary.json
│   └── <video>.srt / .transcript.json
└── Me_at_the_zoo_jNQXAC9IVRw/     ← a URL (named by title + id)
    └── …
```

- New helpers in **`src/videoclipper/download.py`**:
  - **`CLIPS_ROOT = "clips"`** — the single parent folder for all output.
  - **`_sanitize_name(name)`** — makes a safe folder name (removes illegal
    characters, turns spaces into underscores, caps the length ~60).
  - **`url_video_name(url)`** — asks yt-dlp for the video's **title + id**
    (`--skip-download --print %(title)s --print %(id)s`) and combines them (the
    id guarantees uniqueness even if two videos share a title). If that lookup
    fails, it falls back to a **YouTube-id regex** from the URL, then the URL's
    last path part.
  - **`default_output_dir(video_path)`** — returns `clips/<name>`: the **filename**
    for a local file, or the **title + id** for a URL.
- **`cli.run()`** and **`interactive.run_with_progress()`** now both call
  `download.default_output_dir(video_path)` when no `--output-dir` is given
  (replacing the old `downloaded_clips` / `<base>_clips` logic).
- **`.gitignore`** now also ignores `clips/`.
- **`--output-dir some/path`** still overrides the folder explicitly.

## How it was tested
1. **Naming logic (no network).**
   `"/home/me/My Talk.mp4"` → `clips/My_Talk`;
   `"/tmp/sample.mp4"` → `clips/sample`;
   `_sanitize_name("My Video: Part 2 / HD")` → `My_Video_Part_2_HD`.
2. **URL naming (yt-dlp metadata).** A real URL →
   `clips/Me_at_the_zoo_jNQXAC9IVRw` (title + id).
3. **No mixing.** Ran two different local videos; they produced **two separate
   folders** — `clips/sample/` and `clips/long_sample/` — each with its own
   `clip_01.mp4`, `.srt`, `.transcript.json`, and `summary.txt`/`.json`.
4. **Regression.** The 3 unit tests still pass.

## Result / what worked
Different videos are now cleanly isolated under `clips/<video-name>/`, so a new
run never clobbers an earlier one. ✅
