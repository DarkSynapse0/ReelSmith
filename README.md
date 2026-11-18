# Open Source Clipping — a free, local video-to-shorts tool

Turn one long video into several short **vertical (9:16)** clips with **burned-in,
word-by-word captions**. Everything runs **locally and free** on your own
computer — no paid APIs, no uploads. Works with **Nepali** (and many other
languages).

It is a command-line prototype, in the spirit of tools like Opus Clip, built
to be simple and easy to modify.

---

## Project layout

The code lives in a package under `src/videoclipper/`:

```
OpenSourceClipping/
├── src/videoclipper/      ← all the code (the package)
│   ├── cli.py             ← the one command: runs the whole pipeline
│   ├── interactive.py     ← the step-by-step menu (no flags to memorise)
│   ├── download.py        ← download a video from a URL (yt-dlp)
│   ├── transcribe.py      ← audio → text + word timings (faster-whisper)
│   ├── moments.py         ← split into 20–60s segments, pick the best N
│   ├── scoring.py         ← the heuristics (SWAP THIS to get smarter)
│   ├── video.py           ← FFmpeg: cut, make vertical, burn captions
│   ├── reframe.py         ← find the speaker's face (for --vertical track)
│   ├── captions.py        ← builds the ASS subtitles (all caption styling)
│   ├── utils.py           ← shared helpers (friendly errors, FFmpeg checks)
│   ├── models/            ← bundled face-detection model (YuNet .onnx)
│   ├── __main__.py        ← lets you run `python -m videoclipper`
│   └── __init__.py
├── tests/                 ← quick tests that don't need a video
├── docs/                  ← full documentation (see docs/README.md)
├── samples/               ← put test videos here
├── clips/                 ← generated clips, one folder per video (git-ignored)
├── pyproject.toml         ← makes it installable (`pip install -e .`)
├── requirements.txt
└── README.md  LICENSE  CHANGELOG.md  ROADMAP.md  PROGRESS.md
```

The single most important file to know about is **`scoring.py`** — it is kept
separate on purpose so you can make the clip-picking smarter without touching
anything else.

---

## Setup

You need **Python 3** and **FFmpeg** installed.

Install FFmpeg (if you don't have it):

- **Arch Linux:** `sudo pacman -S ffmpeg`
- **Ubuntu/Debian:** `sudo apt install ffmpeg`
- **macOS (Homebrew):** `brew install ffmpeg`
- **Windows:** `winget install Gyan.FFmpeg`

Then set up the project:

```bash
# 1. Create an isolated Python environment (once)
python3 -m venv venv

# 2. Activate it
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install the tool (this reads pyproject.toml and creates the
#    `videoclipper` command). The -e means "editable", so any code change
#    you make takes effect immediately with no reinstall.
pip install -e .
```

That last step gives you a `videoclipper` command to use below.

For **Nepali captions** you also need a Devanagari font. Most Linux systems
already have **Noto Sans Devanagari**. If captions show empty boxes, install it:

- **Arch:** `sudo pacman -S noto-fonts`
- **Ubuntu/Debian:** `sudo apt install fonts-noto`

---

## Usage

### Easiest: the interactive menu

Don't want to remember any flags? Just run the command with nothing after it:

```bash
videoclipper
```

You get a polished menu: a title banner, **arrow-key option lists** (↑/↓ then
Enter), a job-configuration summary, and clean **progress bars** for each stage.

```
╭──────────────────────────────────────────────────────────────────╮
│  🎬  VIDEOCLIPPER v1.0  •  AI-Powered Vertical Clip Generator     │
╰──────────────────────────────────────────────────────────────────╯

  ? Speech language:
    ● auto   ○ ne   ○ en   ○ hi

  [1/4] ⬇  Downloading video...   ━━━━━━━━━━━━━━━━━━━━ 100%
  [2/4] 🎙  Transcribing audio...  ━━━━━━━━━━━━━━━━━━━━ 100%
  [3/4] 🧠 Finding best moments... ━━━━━━━━━━━━━━━━━━━━ 100%
  [4/4] ✂  Rendering clips...      ━━━━━━━━━━━╸━━━━━━━   62%
```

Press Enter to accept the sensible default for any question. (If you pipe input
or run without a real terminal, it automatically falls back to simple typed
prompts.)

### Or type the options directly

```bash
# Simplest: auto-detect language, make 5 clips
videoclipper my_video.mp4

# Straight from a URL — YouTube, Shorts, Reels, etc. (downloads it first)
videoclipper "https://www.youtube.com/watch?v=XXXXXXXXXXX" --language en

# Nepali, 5 clips (the main example)
videoclipper my_video.mp4 --language ne --clips 5

# Nepali — automatically uses the Nepali fine-tuned model (best accuracy)
videoclipper my_video.mp4 --language ne --clips 5

# Or force a bigger general model (slower)
videoclipper my_video.mp4 --language ne --model medium --clips 5

# Blurred-background style, or the animated "big word" captions
videoclipper my_video.mp4 --language ne --vertical blur --caption-style bigword

# Follow the speaker's face (the crop PANS to follow them through the clip)
videoclipper my_video.mp4 --language ne --vertical track
```

**Face-tracking not framing well?** Some videos (screen-recording / b-roll heavy,
or no clear face) just can't be tracked. To see what the detector finds on a
video, run the diagnostic — it prints stats and saves annotated frames:

```bash
python -m videoclipper.reframe "my_video.mp4"
```

`videoclipper ...` and `python -m videoclipper ...` are exactly the same thing,
so use whichever you like.

### All options

| Option | Default | Meaning |
|--------|---------|---------|
| *(no video given)* | — | launches the interactive menu |
| `-i`, `--interactive` | off | force the interactive menu |
| `--no-captions` | off | skip burned-in captions entirely |
| `--language` | `auto` | `auto`, `ne` (Nepali), `en`, `hi`, …, or `mixed` (switches languages) |
| `--model` | `small` | `tiny`, `base`, `small`, `medium`, `large-v3` (bigger = slower, more accurate); **`nepali`** (a Nepali-fine-tuned model — *much* better for Nepali); or any Hugging Face model id |
| `--clips` | `5` | how many clips to make |
| `--vertical` | `crop` | `crop` (center-crop), `blur` (blurred-background fit), or `track` (follow the speaker's face) |
| `--caption-style` | `classic` | `classic`, `bigword`, `hormozi` (cyan bold caps), `mrbeast` (yellow/orange Bebas), `karaoke` (colour sweep), `highlight-box` (word on a plate). Each has its own font/colour; English uses Poppins/Bebas, Nepali auto-falls back to Noto Sans Devanagari. |
| `--buffer` | `0.4` | seconds of padding before/after each clip |
| `--min-seconds` | `20` | shortest allowed clip |
| `--max-seconds` | `60` | longest allowed clip |
| `--output-dir` | `clips/<video-name>` | where to save the results (each video gets its own folder) |
| `--keep-intermediate` | off | keep the raw/vertical/caption working files |
| `--no-cache` | off | ignore the cached download/transcript and redo them |

### Mixed-language videos (e.g. Hindi + English)

If your video switches languages, use `--language mixed` (or pick **mixed** in
the menu):

```bash
videoclipper my_video.mp4 --language mixed
```

It splits the audio into utterances and detects each one's language separately,
so a Hindi sentence is written in Hindi (Devanagari) and an English sentence in
English.

**Tip — tell it the main language.** For a mostly-Nepali video with some
English words, use **`--language mixed:ne`** (or `mixed:hi`). It keeps each
utterance in Nepali unless English is clearly detected, so the Nepali stays in
Devanagari and only the real English words come out in English. Plain `mixed`
auto-detects every utterance, which can wrongly flip short Nepali clips to
English. It handles switching **between** sentences well; switching **within** a
single sentence is detected as one language. Mixed mode is a bit slower.

### What you get

Each video gets **its own folder** under `clips/`, so different videos never
mix together:

```
clips/
└── <video-name>/              ← named after the file, or a URL's title + id
    ├── clip_01.mp4            ← finished vertical clip with captions
    ├── clip_02.mp4
    ├── ...
    ├── <video>.transcript.json   ← full transcript with word timings
    ├── <video>.srt               ← plain subtitles
    ├── summary.txt                ← human-readable list (start, end, score, why)
    └── summary.json               ← same, for programs
```

(Use `--output-dir some/path` to choose a specific folder instead.)

You can also run a single step on its own, e.g. just transcribe:

```bash
python -m videoclipper.transcribe my_video.mp4 --language ne --model small
```

---

## Changing the look of the captions

Open `src/videoclipper/captions.py` and edit the `CAPTION_STYLE` dictionary near the top:
font, font size, the normal and highlight colours, outline thickness, and how
far up from the bottom the captions sit (`margin_vertical`), plus how many
words appear at once (`words_per_line`).

## Changing which clips get picked

Open `src/videoclipper/scoring.py`. The weights in `WEIGHTS` decide how much each factor
(strong opening, question, emphasis words, pace, silence) matters. You can also
add your own words to `EMPHATIC_WORDS`, `EMPHATIC_DEVANAGARI`, etc.

---

## Ideas for improving the clip-picking later

The scoring is kept in its own file (`src/videoclipper/scoring.py`) on purpose,
so you can make it smarter **without touching anything else** — just keep the
same `score_segment(segment) -> (score, breakdown)` shape.

Ideas, roughly easiest → most advanced:

1. **Better word lists.** Add real Nepali emphatic/hook words you notice in
   your own videos. This alone helps a lot.
2. **Audio energy / loudness.** Louder, more animated moments are often more
   engaging. Measure volume with FFmpeg and add it as a new heuristic.
3. **Laughter / applause / music detection.** Reward moments the audience
   reacts to.
4. **Keyword & topic focus.** Boost segments that mention the video's main
   topic (e.g. the title words).
5. **Sentence completeness.** Prefer clips that start with a clear new thought
   and end on a complete sentence (you already cut on sentence boundaries;
   you can score this too).
6. **A local language model.** Run a small offline model (e.g. via Ollama) to
   rate how "hooky" or self-contained each candidate is, and blend that score
   with the heuristics. Still 100% free and local.
7. **Learn from yourself.** Keep the clips you actually publish and which ones
   did well, then tune the weights (or train a small model) to match your taste.

---

## Troubleshooting

- **"Could not download that video" / "Sign in to confirm you're not a bot"** →
  YouTube's anti-bot check (common after several downloads). Pass your browser's
  cookies: `videoclipper "<url>" --cookies-from-browser firefox` (or `chrome`,
  `brave`, `zen`, …). For the menu: `export VIDEOCLIPPER_COOKIES_BROWSER=firefox`
  first. YouTube also needs a JS runtime (`deno` or `node`) installed to solve
  its URL challenge — the tool enables the solver automatically.
  If downloads still fail, update yt-dlp: `pip install -U yt-dlp`.
- **"ffmpeg was not found"** → install FFmpeg (see Setup).
- **Captions are empty boxes for Nepali** → install a Devanagari font (see Setup).
- **"No suitable moments were found"** → the video is shorter than `--min-seconds`,
  or has little speech. Try a longer video or lower `--min-seconds`.
- **Transcription is slow** → use a smaller `--model` (e.g. `tiny` or `base`);
  the first run also downloads the model once.
- **Wrong words in the transcript** → use a bigger `--model` and set the correct
  `--language` instead of `auto`.

---

## Tests & documentation

Run the quick tests (no video needed):

```bash
python tests/test_basic.py      # or: python -m pytest  (if you have pytest)
```

Full documentation lives in **`docs/`** — start at
[`docs/README.md`](docs/README.md). See also
[`CHANGELOG.md`](CHANGELOG.md), [`ROADMAP.md`](ROADMAP.md),
[`ARCHITECTURE.md`](ARCHITECTURE.md), [`PROGRESS.md`](PROGRESS.md), and
[`CONTRIBUTING.md`](CONTRIBUTING.md).

---

*Built as a learning project. All code is original and meant to be easy to read
and modify.*
