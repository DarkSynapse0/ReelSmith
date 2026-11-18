# Step 7 — One command

## Goal
Tie everything together into a single command, save finished clips in an output
folder, and write a summary listing each clip's start, end, and score.

## What was built
- `src/videoclipper/cli.py` — the entry point. `run(...)` executes the full pipeline:
  1. Checks (FFmpeg, file exists).
  2. Transcribe (Steps 1–2).
  3. Find best moments (Step 3).
  4. For each chosen clip: `cut_clip` → `make_vertical` → `generate_ass` →
     `burn_captions`.
  5. Write `summary.txt` + `summary.json`.
- Outputs land in `<video>_clips/` (override with `--output-dir`): finished
  `clip_01.mp4`, `clip_02.mp4`, …, plus the transcript JSON/SRT and the two
  summaries. Intermediate files go in `work/` and are auto-cleaned unless
  `--keep-intermediate`.
- First version of `README.md`.

## Command-line options
| Option | Default | Meaning |
|--------|---------|---------|
| `--language` | `auto` | `auto`, `ne`, `en`, `hi`, … |
| `--model` | `small` | `tiny`/`base`/`small`/`medium`/`large-v3` |
| `--clips` | `5` | how many clips to make |
| `--vertical` | `crop` | `crop` or `blur` |
| `--caption-style` | `classic` | `classic` or `bigword` (added in Step 9) |
| `--buffer` | `0.4` | seconds padding before/after each clip |
| `--min-seconds` | `20` | shortest clip |
| `--max-seconds` | `60` | longest clip |
| `--output-dir` | `<video>_clips` | where to save |
| `--keep-intermediate` | off | keep the raw/vertical/ass working files |

## Bug fixed — NumPy float display
The summary showed `np.float64(0.64)` instead of `0.64`, because faster-whisper
returns NumPy floats for timestamps and they leaked through into the breakdown.
Fixed at the source in `src/videoclipper/transcribe.py` by wrapping word/segment times in
`float(...)`. After the fix the summary reads `'silence': 0.64`.

## How it was tested
Generated a ~53 s spoken video and ran:
```
videoclipper long_sample.mp4 --language en --model tiny --clips 2 --vertical blur
```

## Result / what worked
Produced **two valid 1080×1920 captioned clips**, a readable `summary.txt`
(start/end/length/score/why/text) and `summary.json`, the transcript JSON/SRT,
and auto-cleaned the `work/` dir. ✅ A follow-up single-clip run confirmed the
float fix.
