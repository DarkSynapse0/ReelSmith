# ADR-009: Dynamic speaker tracking via an FFmpeg `sendcmd` crop path

**Status:** Accepted (v1.3.0) — supersedes the fixed-crop part of
[ADR-006](adr-006-yunet-face-detection.md)
**Context:** `--vertical track` used **one fixed crop** (the median face
position) for a whole clip. On a real video a user reported that "in clip 4 the
person [is] cut off" — because the speaker moved, or the shot changed within the
clip, so no single crop position kept them in frame.

## Decision
Make the track crop **follow the speaker over time**:

1. **`reframe.compute_crop_plan()`** samples ~6 frames/sec and, for each sample,
   picks a target horizontal position:
   - a detected face → its centre,
   - a **brief gap** (≤ 2 s with no face) → **hold** the last face position
     (covers quick look-aways),
   - a **long gap** → **drift to centre** (e.g. a screen-recording stretch).
2. **Scene-cut snap:** if the face jumps more than ~30 % of the width between
   samples (≈ a shot change or a big move), **reset** the smoother so the crop
   *snaps* instead of sliding awkwardly across the cut.
3. **Smoothing:** an exponential moving average (α ≈ 0.25) so the pan **glides**
   rather than jitters frame-to-frame.
4. **Keyframes:** emit a `(time, crop_x)` keyframe only when the crop actually
   moves. These are written to a tiny **`sendcmd`** file.
5. **`video.make_vertical()` (`track`)** renders with
   `sendcmd=f=…,crop=…,scale=1080×1920`, which animates the crop's `x` over
   time. It runs FFmpeg **from the file's folder** with a bare filename (via the
   new `run_ffmpeg(cwd=…)`), so unusual folder names can't break the filter.
   No face at all → falls back to a plain centre crop.

## Rationale
- **It fixes the actual bug.** A moving speaker (or a within-clip cut) now stays
  framed; a fixed crop cannot.
- **Reuse FFmpeg, don't reinvent it.** `sendcmd` + `crop` already animate a crop
  over time, so we express the plan as keyframes and let FFmpeg do the work — no
  new heavy dependency, fast, deterministic.
- **Smoothing + snapping = watchable.** Raw per-frame detections jitter; EMA
  smoothing makes gentle pans, and cut-snapping avoids a nauseating slide across
  a shot change.
- **Graceful degradation.** Brief look-aways hold; long faceless stretches
  centre; no face at all falls back to centre. It never produces an empty crop.

## Consequences
- ✅ The speaker is kept in frame even when they move or the shot changes.
- ✅ Still free/local/offline; adds no new dependency (FFmpeg + OpenCV already
  present).
- ✅ Robust to odd folder names (the `sendcmd` file is referenced by bare name
  with `cwd`).
- ⚠️ Slightly slower than the fixed crop (samples ~6 fps and detects per sample),
  but still a few seconds for a short clip.
- ⚠️ Still **largest-face**, not true active-speaker selection (planned).
- ⚠️ **Screen-recording / b-roll-heavy** videos have little to track — `crop` or
  `blur` is better; the `diagnose()` tool reports which case a video is.
- ℹ️ The old `compute_crop_box()` (fixed crop) stays in the code for reference /
  tests but is no longer used by `track`.

## Alternatives considered
- **A single `crop` expression** with a huge nested `if(t<…)` over `t` — works
  but unreadable and fragile for many keyframes; `sendcmd` is purpose-built.
- **Re-cropping frame-by-frame in OpenCV and re-encoding ourselves** — far
  slower and re-implements what FFmpeg already does well.
- **Full scene-detection (e.g. PySceneDetect / FFmpeg `select=scene`)** — more
  accurate cut detection, but a big-jump heuristic on the face position is
  simpler and good enough here; can be revisited if needed.
