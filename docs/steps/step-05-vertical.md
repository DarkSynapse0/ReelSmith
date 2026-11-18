# Step 5 — Make it vertical (9:16)

## Goal
Convert each clip into a **1080×1920** vertical video, with a center-crop by
default and a blurred-background fit as an option.

## What was built
- `video.make_vertical(input, output, mode="crop")`, target size
  `VERTICAL_WIDTH=1080` × `VERTICAL_HEIGHT=1920`.
- **`crop` mode (default):** zoom in and center-crop — fills the whole 9:16
  frame with no bars, but the left/right edges are cut. FFmpeg filter:
  ```
  scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920
  ```
- **`blur` mode:** fit the whole frame inside 9:16 (nothing cut) and fill the
  space above/below with a blurred, zoomed copy. FFmpeg `filter_complex`:
  ```
  [0:v]split=2[bg][fg];
  [bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:3[bgblur];
  [fg]scale=1080:1920:force_original_aspect_ratio=decrease[fgfit];
  [bgblur][fgfit]overlay=(W-w)/2:(H-h)/2
  ```

## How it was tested
- Ran both modes and confirmed output resolution with `ffprobe`.
- Rendered the `blur` mode on a distinct **test pattern** and extracted a frame
  to visually verify the composition (sharp fitted center + blurred background).

## Result / what worked
Both modes output exactly **1080×1920**. The blurred-background frame showed the
sharp original fitted in the middle with the blurred, zoomed copy filling the
top and bottom — exactly as intended. ✅

## Known limitation (by design, for now)
The crop is always **centered** — it does not detect or follow the person. If
the subject is off to one side they can be cut off; use `blur` mode in that case.
Speaker-tracking is planned — see `docs/decisions/adr-002-center-crop-vs-tracking.md`
and `ROADMAP.md`.
