# Step 16 — Dynamic speaker tracking (+ face diagnostic, warning fix, smooth ETA)

## Goal
Make `--vertical track` actually keep the speaker in frame. The first version
(Step 11) used **one fixed crop** for a whole clip, so when the speaker moved —
or the shot changed within the clip — the person got **cut off** (reported as
"in clip 4 the person cut off"). This step makes the crop **follow** them.

## What was built

### 1. Dynamic tracking (the fix)
- **`reframe.compute_crop_plan(video_path, sample_fps=6)`** builds a crop that
  moves over time instead of one fixed position:
  - samples ~6 frames/sec and finds the main face (YuNet, largest face);
  - per sample, chooses a target x: the **face centre**, or — if there's no
    face — **holds** the last position through brief (≤ 2 s) look-aways, or
    **drifts to centre** during long faceless stretches;
  - **snaps** at big jumps (> 30 % of the width ≈ a scene cut) instead of
    sliding across them;
  - **smooths** the motion with an exponential moving average (α ≈ 0.25);
  - emits `(time, crop_x)` **keyframes** only where the crop actually moves.
  - Returns `None` if no face is ever found.
- **`video.make_vertical()` `track` mode** writes those keyframes to a tiny
  FFmpeg **`sendcmd`** file and renders with
  `sendcmd=f=…,crop=…,scale=1080×1920` — animating the crop's `x` over time. It
  runs FFmpeg **from the file's folder** with a bare filename (via the new
  `run_ffmpeg(cwd=…)`), so unusual folder names can't break the filter. No face
  → **center-crop fallback**.
- The old `compute_crop_box()` (fixed crop) stays in the file for reference but
  is no longer used by `track`.

### 2. Face diagnostic
`python -m reelsmith.reframe "<video.mp4>"` (→ `reframe.diagnose()`) reports
what the detector actually sees: frames checked, **% with a face**, face x
min/median/max and **horizontal spread**, the number of **big jumps** (≈ cuts),
and a plain-language **verdict** (few faces → use `crop`/`blur`; moves a lot →
tracking helps; fairly still → fixed is fine). It also saves up to **8 annotated
frames** (green box = detected face, red box = chosen crop) and prints a clear
message if the file can't be decoded (e.g. AV1/VP9 `.webm`).

### 3. OpenCV warning silenced
`reframe.py` sets `OPENCV_LOG_LEVEL=ERROR` **before** importing `cv2` (and calls
`cv2.setLogLevel`), so the detector's harmless `setPreferableTarget …` warning
no longer leaks to stderr and garbles the live display.

### 4. Smooth ETA
The TUI's time-remaining is now a custom `_SmoothETA` column that extrapolates
`elapsed × (1 − done) / done` — it shows `--:--` until there's progress, then a
steady countdown (and `H:MM:SS` for long jobs), replacing rich's built-in
estimate which flickered and sometimes vanished.

## How it was tested
1. **Moving-face video.** A clip with a face sliding **left → right** was
   tracked: the crop `x` climbed **119 → 226 → …** across **50 keyframes** (face
   in **49/50** frames), and extracted frames at start / middle / end all kept
   the face in frame — where the old fixed crop would have cut him off at the
   ends.
2. **Diagnostic.** On a steady face clip it reported 100 % face frames, median
   x ≈ 81 % of width, 0 jumps, and saved annotated frames showing the green
   face box inside the red crop box. On an AV1 `.webm` it correctly reported it
   couldn't decode the codec directly.
3. **Fallback + integration.** A no-face clip fell back to a center crop; the
   full pipeline (cut → re-encode H.264 → dynamic track → captions) produced a
   1080×1920 clip; the 3 unit tests still pass.
4. **ETA math.** 25 % done after 10 s → `0:30`; `--:--` before any progress.

## Result / what worked
Speakers who move (or clips with a shot change) now stay in frame — the crop
pans and snaps to follow them — and the diagnostic makes it clear when a video
simply can't be face-tracked. ✅

## Limitation / future
- Still **largest-face**, not true **active-speaker** selection when several
  faces are present (planned — see `ROADMAP.md`).
- **Screen-recording / b-roll-heavy** videos have little to track; `crop`/`blur`
  is the right choice (the diagnostic says which).
- The diagnostic reads video directly, so it **can't decode AV1/VP9 `.webm`**
  (the pipeline avoids this by re-encoding clips to H.264 first).
- Design rationale: `docs/decisions/adr-009-dynamic-tracking.md`.
