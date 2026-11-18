# Step 8 — Clip straight from a URL

## Goal
Let the user paste a video URL (YouTube, Shorts, Reels, …) and have the tool
download it automatically, then run the normal pipeline — no manual file needed.

## What was built
- `src/videoclipper/download.py` using **yt-dlp** (free, open source, local — no account or API
  key):
  - `is_url(text)` — treats input starting with `http://`/`https://` as a URL.
  - `download_video(url, output_dir)` — runs yt-dlp as
    `python -m yt_dlp ...` (so it always uses this venv), downloads best MP4
    video + audio **capped at 1080p**, merges to `source.mp4`, shows progress,
    and returns the file path.
- `src/videoclipper/cli.py` gained a **Step 0: Download** stage. Its `video` argument now
  accepts a local path **or** a URL; URLs are downloaded into `work/` first.
- `requirements.txt` gained `yt-dlp`; README updated with URL examples.

## Why the 1080p cap
We only ever output 1080-wide vertical video, so downloading 4K just wastes time
and disk. A first test accidentally pulled a **466 MB 4K** file (Big Buck Bunny)
before finishing — which is exactly why the format string now limits to
`height<=1080`.

## Friendly errors
Clear message for a bad/private/age-restricted/removed link or no internet.

## How it was tested
Ran the full pipeline with **only a URL** (no local file): the first-ever
YouTube video, `"Me at the zoo"`:
```
videoclipper "https://www.youtube.com/watch?v=jNQXAC9IVRw" --language en --model tiny --clips 1
```

## Result / what worked
It **downloaded → transcribed correctly** ("Alright, so here we are, one of the
elephants…") → produced a valid **1080×1920** captioned clip → and cleaned up
the download afterward. ✅

## Note
Downloads are for personal/local use; be mindful of each platform's terms and
creators' rights before republishing someone else's content.
