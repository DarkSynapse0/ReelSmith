# Step 9 — Animated captions (`bigword` style)

## Goal
Add an animated caption style on top of the existing calm one — specifically the
"one big word pops onto the screen at a time" look — as a selectable option,
without breaking the current style.

## Background (the research)
We first researched a menu of ~11 caption effects achievable for free with ASS
tags (word pop, karaoke color sweep, keyword emphasis, highlight box, slide-up,
fade, tilt, etc.). The user then asked to **implement one**: the big-word pop.
The rest of the menu is tracked in `ROADMAP.md`.

## What was built
- `captions.generate_ass(...)` gained an `animation` parameter and the
  event-building was split:
  - `_events_classic(...)` — the original: a short line of words with the
    active word highlighted (unchanged behavior).
  - `_events_bigword(...)` — one large word, centered, popping in. Uses only
    standard ASS override tags:
    - `\an5` + `\pos(540,960)` — anchor by the middle, center of a 1080×1920
      frame.
    - `\fs<big>` — larger font (`font_size × 1.9`).
    - `\fscx140\fscy140\t(0,120,\fscx100\fscy100)` — start at 140 % size and
      shrink to 100 % over 120 ms → a snappy "pop".
    - Active word drawn in the highlight color.
- `src/videoclipper/cli.py` gained `--caption-style {classic,bigword}` (default `classic`),
  threaded into `generate_ass(..., animation=caption_style)`.
- README updated with the new option.

## How it was tested
Rendered a `bigword` clip from the sample's real word timestamps and extracted
a frame.

## Result / what worked
The frame showed a single large word (e.g. "That") centered in the highlight
color — the expected big-word layout. The pop itself is motion, so it's visible
on playback rather than in a still. Because it reuses the same text engine,
Nepali/Devanagari works here too. ✅
