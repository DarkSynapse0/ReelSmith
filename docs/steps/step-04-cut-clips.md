# Step 4 — Cut the clips

## Goal
Cut each chosen segment out of the source video, with a small buffer before and
after so the first and last words aren't chopped off.

## What was built
- `src/reelsmith/video.py` was started here (it later also holds Steps 5 and 6).
- `video.cut_clip(source, start, end, output, buffer=0.4, source_duration=None)`:
  - Subtracts `buffer` from the start and adds it to the end.
  - **Clamps** so it never asks for a negative start or goes past the end.
  - **Re-encodes** (libx264 + aac) instead of stream-copying, so the cut is
    accurate to the exact second (stream copy can only cut on keyframes).
  - Returns the real (buffered) start/end so the caption step knows the clip's
    true time range.
- `DEFAULT_BUFFER = 0.4` seconds.

## How it was tested
Asked for 2.0–8.0 s on the sample video and measured the output.

## Result / what worked
The cut correctly expanded to **1.6–8.4 s** and the output file measured
exactly **6.8 s** (6 s requested + 0.4 s buffer on each side). ✅
