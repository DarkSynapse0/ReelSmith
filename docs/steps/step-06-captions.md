# Step 6 — Word-by-word captions

## Goal
Burn in captions that highlight each word as it's spoken, using the word
timestamps — and make sure **Nepali (Devanagari)** displays correctly.

## What was built
- `src/reelsmith/captions.py` — generates an **ASS** subtitle file (Advanced SubStation
  Alpha). ASS, unlike plain SRT, can change the color of individual words at
  exact times and animate them.
  - All appearance settings live in one editable `CAPTION_STYLE` dict: `font`
    (default **Noto Sans Devanagari**), `font_size`, `normal_color`,
    `highlight_color`, `outline_color`, `outline_width`, `shadow`, `bold`,
    `margin_vertical`, `words_per_line`.
  - `rgb(r, g, b)` helper so you can pick colors in normal 0–255 values.
  - `generate_ass(...)` filters words to the clip, shifts them to start at 0,
    groups them into short lines, and writes one event per word (each stays on
    screen until the next word begins → no flicker or gaps).
- `video.burn_captions(input, ass, output)` — renders the ASS permanently into
  the video with FFmpeg's `ass` filter (`_escape_filter_path()` keeps unusual
  paths safe).

## Font check
Confirmed the system has **Noto Sans Devanagari** (ideal for Nepali), plus Noto
Serif Devanagari and FreeSans. libass resolves it by family name.

## How it was tested
- **English:** burned captions from the real sample's word timestamps, grabbed
  a frame. Showed a 4-word line with the active word highlighted in yellow,
  bold, black outline, lower third.
- **Nepali:** built a synthetic Devanagari line
  "यो सबैभन्दा महत्त्वपूर्ण कुरा हो" and burned it.

## Result / what worked
Both rendered correctly. The Nepali frame showed
"यो सबैभन्दा **महत्त्वपूर्ण** कुरा" with the active word highlighted — and the
**complex stacked conjunct in महत्त्वपूर्ण rendered correctly**, confirming
proper Devanagari shaping end-to-end. ✅
