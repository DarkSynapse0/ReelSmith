# ADR-003: Use ASS subtitles for captions

**Status:** Accepted
**Context step:** Step 6 (Captions)

## Context
We need captions that:
- highlight the **current word** as it's spoken (we have per-word timestamps),
- can be **animated** (e.g. the `bigword` pop), and
- render **Nepali/Devanagari** correctly, including complex conjuncts.

## Options considered
1. **Plain SRT, burned in.** Simple, but SRT has **no styling** — it can't color
   a single word differently or animate anything. Dead end for our goal.
2. **drawtext filter per word.** FFmpeg's `drawtext` can place styled text, but
   orchestrating many timed, highlighted, animated words by hand is painful and
   hard to read.
3. **ASS (Advanced SubStation Alpha), rendered with libass.** A plain-text
   subtitle format with rich styling and an animation system (`\t`, `\fscx`,
   `\fscy`, `\move`, `\fad`, `\pos`, per-word color overrides). FFmpeg renders
   it via the `ass` filter.

## Decision
Use **ASS**. `src/videoclipper/captions.py` writes an ASS file; `video.burn_captions()` renders
it with FFmpeg's `ass` filter.

## Rationale
- Per-word color change is trivial (`{\1c&...&}word{\1c&...&}`).
- Animation is built in — the `bigword` pop is just `\fscx/\fscy` + `\t`, no
  extra tooling.
- **libass shapes Devanagari correctly** — we verified the stacked conjunct in
  **महत्त्वपूर्ण** renders properly with Noto Sans Devanagari.
- One `CAPTION_STYLE` dict centralizes all look-and-feel settings.

## Consequences
- ✅ Powerful, readable, and all appearance is in one place.
- ✅ New styles are just new event-builder functions (see `_events_bigword`).
- ⚠️ ASS has its own quirks: time format is `H:MM:SS.cc` (two-decimal
  centiseconds), colors are `&HAABBGGRR`, and `{`/`}` are special (we escape
  stray ones). These are handled in `src/videoclipper/captions.py`.
- ⚠️ **Color emoji** don't render well in libass — any emoji/sticker effect
  would need an image-overlay approach instead (noted in `ROADMAP.md`).
