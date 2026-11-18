"""
captions.py
-----------
Step 6: build word-by-word highlighted captions.

We write an ".ass" subtitle file (Advanced SubStation Alpha). ASS is a
plain-text subtitle format that, unlike plain SRT, lets us control font,
colour, outline, position AND change the colour of individual words at
exact times. That is what gives the lively "karaoke" look where the word
currently being spoken is highlighted.

FFmpeg (via the `ass` video filter in video.py) then burns these captions
permanently into the video.

Everything you are likely to want to change — font, size, colours,
position — is in the CAPTION_STYLE dictionary near the top.
"""

from . import utils


# -------------------------------------------------------------------------
# Caption appearance. Edit these to restyle every caption.
# -------------------------------------------------------------------------
#
# A note on ASS colours: they are written as &HAABBGGRR (hex) where the
# pairs are Alpha, Blue, Green, Red. Alpha 00 = fully opaque. So:
#   white  = &H00FFFFFF
#   yellow = &H0000FFFF   (red+green on, blue off)
#   black  = &H00000000
# The helper rgb() below lets you think in normal R, G, B instead.

def rgb(r, g, b, alpha=0):
    """Make an ASS colour string from ordinary 0-255 R, G, B values."""
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"


CAPTION_STYLE = {
    # Two fonts: a punchy one for Latin text (English, etc.) and a
    # Devanagari-capable one for Nepali/Hindi. We pick automatically per clip
    # based on whether the text contains Devanagari characters.
    "font": "Noto Sans Devanagari",  # used when the text is Devanagari
    "latin_font": "Poppins",         # punchy modern font for English/Latin
    "font_size": 100,                # size in pixels (frame is 1080x1920) — big
    "normal_color": rgb(255, 255, 255),   # white, for inactive words
    "highlight_color": rgb(255, 221, 0),   # warm yellow, for the active word
    "outline_color": rgb(0, 0, 0),          # black outline around letters
    "outline_width": 6,              # thick outline so it reads on busy footage
    "shadow": 2,                     # drop-shadow depth (helps on busy footage)
    "bold": True,
    "margin_vertical": 420,          # distance (px) from the bottom (lower-mid)
    "words_per_line": 4,             # how many words show on screen at once
    # Used only by the "highlight-box" style: the colour of the text that sits
    # ON the coloured box (dark text reads well on the bright default box).
    "box_text_color": rgb(0, 0, 0),
}


# Per-style presets: each caption style gets its OWN font, size and colours,
# which is what makes them feel distinct (one shared look reads as generic).
# Values adapted from 2026 short-form research. `latin_font` is used for
# English/Latin; Nepali/Devanagari always falls back to the Devanagari font.
STYLE_PRESETS = {
    # Clean yellow highlight, condensed display font.
    "classic": {"latin_font": "Bebas Neue", "font_size": 104,
                "highlight_color": rgb(255, 255, 0), "outline_width": 6,
                "shadow": 3},
    # Bold geometric sans, cyan highlight, snappy pop (the real Hormozi look).
    "hormozi": {"latin_font": "Poppins", "font_size": 104,
                "highlight_color": rgb(0, 255, 255), "outline_width": 5,
                "shadow": 4},
    # MrBeast: condensed, yellow body + orange highlight, extra-thick outline.
    "mrbeast": {"latin_font": "Bebas Neue", "font_size": 118,
                "normal_color": rgb(255, 255, 0),
                "highlight_color": rgb(255, 102, 0), "outline_width": 8,
                "shadow": 5},
    # Smooth blue colour-wipe.
    "karaoke": {"latin_font": "Poppins", "font_size": 104,
                "highlight_color": rgb(0, 128, 255), "outline_width": 4,
                "shadow": 3},
    # Word on a bright plate.
    "highlight-box": {"latin_font": "Poppins", "font_size": 96,
                      "highlight_color": rgb(255, 221, 0), "outline_width": 5,
                      "shadow": 2},
    # One big word at a time.
    "bigword": {"latin_font": "Poppins", "font_size": 100,
                "highlight_color": rgb(255, 221, 0), "outline_width": 6,
                "shadow": 3},
}


# -------------------------------------------------------------------------
# Time formatting for ASS (hours:minutes:seconds.centiseconds)
# -------------------------------------------------------------------------

def _ass_time(seconds):
    """ASS uses H:MM:SS.cc — note the dot and only two decimal places."""
    if seconds < 0:
        seconds = 0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    whole = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis == 100:
        centis = 0
        whole += 1
    return f"{hours:d}:{minutes:02d}:{whole:02d}.{centis:02d}"


def _escape(text):
    """Make text safe to place inside an ASS line."""
    # Curly braces mean "override tag" in ASS, so neutralise any stray ones.
    return text.replace("{", "(").replace("}", ")").strip()


def _has_devanagari(words):
    """True if any word contains a Devanagari character (U+0900–U+097F)."""
    for w in words:
        for ch in w["word"]:
            if "ऀ" <= ch <= "ॿ":
                return True
    return False


def _pick_font(clip_words, style):
    """
    Choose the font for this clip: the Devanagari font when the text is
    Nepali/Hindi, otherwise the punchier Latin font for English, etc.
    """
    if _has_devanagari(clip_words):
        return style["font"]
    return style.get("latin_font") or style["font"]


# -------------------------------------------------------------------------
# Build the ASS file
# -------------------------------------------------------------------------

def _header(style):
    """
    The top part of the ASS file: resolution and the caption style.

    PlayResX/Y must match our vertical video (1080x1920) so positions and
    sizes line up correctly.

    Alignment 2 = bottom-centre. Combined with MarginV, this places the
    captions in the lower part of the frame.
    """
    bold = -1 if style["bold"] else 0  # ASS uses -1 for bold, 0 for not
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style['font']},{style['font_size']},{style['normal_color']},{style['highlight_color']},{style['outline_color']},&H64000000,{bold},0,0,0,100,100,0,0,1,{style['outline_width']},{style['shadow']},2,60,60,{style['margin_vertical']},1
Style: Box,{style['font']},{style['font_size']},{style['box_text_color']},{style['box_text_color']},{style['highlight_color']},&H64000000,{bold},0,0,0,100,100,0,0,3,16,0,2,60,60,{style['margin_vertical']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _chunk_words(words, per_line):
    """
    Split the list of words into small groups ("lines") so the screen is
    never overcrowded. Returns a list of groups, each group a list of the
    original word dictionaries.
    """
    chunks = []
    for start in range(0, len(words), per_line):
        chunks.append(words[start:start + per_line])
    return chunks


def generate_ass(words, clip_start, clip_end, ass_path, style=None,
                 animation="classic"):
    """
    Write an ASS caption file for one clip.

    `words`      : list of {"word", "start", "end"} using the ORIGINAL
                   video's timeline (absolute seconds).
    `clip_start` : when this clip begins in the original video. We subtract
                   it so caption times are relative to the clip itself.
    `clip_end`   : when the clip ends (used to trim the last word).
    `ass_path`   : where to write the .ass file.
    `animation`  : the caption style to use:
                     "classic" -> a line of words, active word highlighted
                                  (calm, readable; the original style).
                     "bigword" -> ONE large word on screen at a time, in the
                                  middle, that "pops" in with a quick scale
                                  bounce (punchy, viral-short style).

    For every word we work out when it starts and ends (each word stays on
    screen until the next word begins, so captions never flicker). The two
    styles differ only in HOW each word is drawn.
    """
    if style is None:
        style = CAPTION_STYLE
    # Apply this style's preset (font/size/colours) on top of the base style.
    style = {**style, **STYLE_PRESETS.get(animation, {})}

    # Keep only words that fall inside this clip, and shift them so the
    # clip starts at time 0.
    clip_words = []
    for w in words:
        if w["end"] <= clip_start or w["start"] >= clip_end:
            continue
        clip_words.append({
            "word": _escape(w["word"]),
            "start": max(0.0, w["start"] - clip_start),
            "end": max(0.0, w["end"] - clip_start),
        })

    # Pick the font for this clip (Latin vs Devanagari) and apply it to a
    # working copy of the style so the header and events use it.
    style = dict(style)
    style["font"] = _pick_font(clip_words, style)

    lines = [_header(style)]

    if not clip_words:
        # No speech in this clip; still write a valid (empty) file.
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write("".join(lines))
        return ass_path

    clip_length = clip_end - clip_start

    # Work out each word's on-screen start and end time (shared by both
    # styles). A word shows until the next word begins.
    timings = []
    for i, w in enumerate(clip_words):
        start_time = w["start"]
        if i + 1 < len(clip_words):
            end_time = clip_words[i + 1]["start"]
        else:
            end_time = clip_length
        if end_time <= start_time:
            end_time = start_time + 0.1  # guard against zero-length events
        timings.append((start_time, end_time))

    builders = {
        "bigword": _events_bigword,
        "hormozi": _events_hormozi,
        "mrbeast": _events_hormozi,   # same bold-caps rendering, own colours/font
        "karaoke": _events_karaoke,
        "highlight-box": _events_highlightbox,
        "classic": _events_classic,
    }
    build = builders.get(animation, _events_classic)
    lines += build(clip_words, timings, style)

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write("".join(lines))
    utils.ok(f"Wrote caption file ({animation}): {ass_path}")
    return ass_path


def _events_classic(clip_words, timings, style):
    """
    The original style: show a few words at a time (a "line"), with the
    word being spoken highlighted in the highlight colour.
    """
    highlight = style["highlight_color"]
    normal = style["normal_color"]
    per_line = style["words_per_line"]
    events = []

    for i, word in enumerate(clip_words):
        start_time, end_time = timings[i]
        # Which line (chunk) is this word in, and where inside that line?
        c_index = i // per_line
        w_index = i % per_line
        chunk = clip_words[c_index * per_line:(c_index + 1) * per_line]

        pieces = []
        for k, cw in enumerate(chunk):
            if k == w_index:
                pieces.append(f"{{\\1c{highlight}}}{cw['word']}{{\\1c{normal}}}")
            else:
                pieces.append(cw["word"])
        text = " ".join(pieces)

        events.append(
            f"Dialogue: 0,{_ass_time(start_time)},{_ass_time(end_time)},"
            f"Default,,0,0,0,,{text}\n"
        )
    return events


def _events_bigword(clip_words, timings, style):
    """
    The animated "big word" style: one large word in the middle of the
    screen at a time, popping in with a quick scale bounce.

    How the animation works (all standard ASS override tags):
      \\an5          -> anchor the text by its middle (so it grows evenly)
      \\pos(540,960) -> centre of a 1080x1920 frame
      \\fs<size>     -> a bigger font size than normal
      \\fscx/\\fscy   -> horizontal/vertical scale, as a percentage
      \\t(0,120,...) -> over the first 120 ms, animate the scale...
    We start the word at 140% size and shrink it to 100%, which reads as a
    snappy "pop" as each word appears. The active word uses the highlight
    colour to make it stand out.
    """
    big_size = int(style["font_size"] * 1.9)   # noticeably larger
    highlight = style["highlight_color"]
    events = []

    for i, word in enumerate(clip_words):
        start_time, end_time = timings[i]
        text = (
            f"{{\\an5\\pos(540,960)\\fs{big_size}\\1c{highlight}"
            f"\\fscx140\\fscy140\\t(0,120,\\fscx100\\fscy100)}}"
            f"{word['word']}"
        )
        events.append(
            f"Dialogue: 0,{_ass_time(start_time)},{_ass_time(end_time)},"
            f"Default,,0,0,0,,{text}\n"
        )
    return events


def _events_hormozi(clip_words, timings, style):
    """
    The "Hormozi" style: bold UPPERCASE words, only 1–3 on screen at a time,
    the active word in the highlight colour, and the whole line gives a quick
    "snap" (a small scale pop) each time a new group of words appears.

    Scaling the WHOLE line (not a single word) means the words don't reflow —
    they just punch in together, which is the signature snappy look.
    """
    highlight = style["highlight_color"]
    normal = style["normal_color"]
    per_line = 3
    events = []

    for i, word in enumerate(clip_words):
        start_time, end_time = timings[i]
        w_index = i % per_line
        base = (i // per_line) * per_line
        chunk = clip_words[base:base + per_line]

        pieces = []
        for k, cw in enumerate(chunk):
            token = cw["word"].upper()   # upper() is a no-op for Devanagari
            if k == w_index:
                pieces.append(f"{{\\1c{highlight}}}{token}{{\\1c{normal}}}")
            else:
                pieces.append(token)
        text = " ".join(pieces)

        # When a NEW group of words first appears, punch the whole line in.
        if w_index == 0:
            text = "{\\fscx112\\fscy112\\t(0,130,\\fscx100\\fscy100)}" + text

        events.append(
            f"Dialogue: 0,{_ass_time(start_time)},{_ass_time(end_time)},"
            f"Default,,0,0,0,,{text}\n"
        )
    return events


def _events_karaoke(clip_words, timings, style):
    """
    The "karaoke" style: the whole line is shown, and the colour sweeps across
    each word left-to-right exactly as it is spoken (ASS \\kf karaoke fill).

    Each line is ONE event. Inside it, every word carries a `\\kf<cs>` tag
    whose duration (in centiseconds) is how long until the NEXT word begins,
    so the fill stays in sync even across small gaps. We set the primary /
    secondary colours so a word fills FROM white TO the highlight colour.
    """
    highlight = style["highlight_color"]
    normal = style["normal_color"]
    per_line = style["words_per_line"]
    events = []

    chunks = _chunk_words(clip_words, per_line)
    for chunk in chunks:
        line_start = chunk[0]["start"]
        line_end = chunk[-1]["end"]
        parts = []
        for j, cw in enumerate(chunk):
            if j + 1 < len(chunk):
                dur = chunk[j + 1]["start"] - cw["start"]
            else:
                dur = cw["end"] - cw["start"]
            centis = max(1, int(round(dur * 100)))
            parts.append(f"{{\\kf{centis}}}{cw['word']}")
        # \1c = colour a word becomes once "sung"; \2c = colour before.
        text = f"{{\\1c{highlight}\\2c{normal}}}" + " ".join(parts)
        events.append(
            f"Dialogue: 0,{_ass_time(line_start)},{_ass_time(line_end)},"
            f"Default,,0,0,0,,{text}\n"
        )
    return events


def _events_highlightbox(clip_words, timings, style):
    """
    The "highlight-box" style: a line of words, and the active word sits inside
    a filled coloured plate (the TikTok auto-caption look).

    The box is done with a second ASS style called "Box" (BorderStyle 3 = an
    opaque box instead of an outline). We switch the active word to it with
    `\\rBox` and switch back to the normal style with `\\r`.
    """
    per_line = style["words_per_line"]
    events = []

    for i, word in enumerate(clip_words):
        start_time, end_time = timings[i]
        c_index = i // per_line
        w_index = i % per_line
        chunk = clip_words[c_index * per_line:(c_index + 1) * per_line]

        pieces = []
        for k, cw in enumerate(chunk):
            if k == w_index:
                pieces.append(f"{{\\rBox}}{cw['word']}{{\\r}}")
            else:
                pieces.append(cw["word"])
        text = " ".join(pieces)

        events.append(
            f"Dialogue: 0,{_ass_time(start_time)},{_ass_time(end_time)},"
            f"Default,,0,0,0,,{text}\n"
        )
    return events
