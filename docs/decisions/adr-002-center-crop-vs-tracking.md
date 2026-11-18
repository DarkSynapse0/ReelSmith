# ADR-002: Center crop now, speaker-tracking later

**Status:** Accepted (tracking is Planned)
**Context step:** Step 5 (Vertical)

## Context
To make a wide video vertical (9:16), we must throw away part of the frame. The
"smart" approach is to detect the person and crop to follow them. The simple
approach is to take the middle.

Important clarification captured here because it confused us at one point:
**Whisper does not do any cropping.** Whisper only listens to audio and produces
text + timings. All cropping is pure FFmpeg geometry in `src/reelsmith/video.py`.

## Decision
Ship a **fixed center crop** as the default (`crop` mode), plus a **blurred-fit**
mode (`blur`) that cuts nothing. Defer face/speaker tracking to a later version.

## Rationale
- Center crop is a few lines of FFmpeg, works well for the common case
  (centered talking-head videos), and has no extra dependencies.
- `blur` mode covers the "subject is off to the side" case safely — nothing is
  cut off, the whole frame is fitted with a blurred background.
- Speaker-tracking needs a computer-vision library (OpenCV/MediaPipe), frame
  sampling, path smoothing, and edge-case handling (multiple faces, scene cuts,
  no face). That's the most complex feature on the roadmap and shouldn't block a
  working v0.1.

## Known limitation
With center crop, a subject in the left/right corner **gets cut off** — the crop
will not move to them. Workaround today: use `--vertical blur`.

## Planned follow-up
Add `--vertical track`: sample frames → detect face (OpenCV/MediaPipe) → build a
position path → smooth it → FFmpeg crop at the moving X → **fall back to center**
if no face is found. Start minimal (fixed average position, no panning). Details
in `ROADMAP.md`.
