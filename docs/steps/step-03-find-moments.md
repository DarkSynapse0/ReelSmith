# Step 3 — Find the best moments

## Goal
Split the transcript into clip-sized chunks (20–60 s) that start and end on
natural sentence boundaries, score them, and pick the top N — with the scoring
kept in its own file so it can be upgraded later.

## What was built
- `src/reelsmith/scoring.py` — five local, free heuristics, each returning roughly 0–1:
  | Heuristic | Rewards |
  |-----------|---------|
  | `score_opening` | a hooky first word + short punchy opener |
  | `score_question` | a `?` or question-starting word (English **and** Nepali) |
  | `score_emphasis` | emotional/emphatic words (English + Devanagari lists) |
  | `score_pace` | a comfortable speaking pace (~2.0–3.3 words/sec) |
  | `score_silence` | few long silent gaps between words |

  These are combined with editable `WEIGHTS` into `score_segment(segment) ->
  (total, breakdown)`.
- `src/reelsmith/moments.py`:
  - `build_candidates()` — a sliding window over sentences; joins consecutive
    transcript segments until the clip is within `MIN_SECONDS`–`MAX_SECONDS`
    (20–60), so clips never cut a word in half.
  - `pick_best()` — scores all candidates, sorts best-first, and **greedily**
    picks the top N that don't overlap, then returns them in time order.

## Key design decision
Scoring sits behind **one function** (`score_segment`) and lives in its own
file. `src/reelsmith/moments.py` doesn't care how the score is produced — so a smarter method
(e.g. a local LLM) can be dropped in later without touching the selection logic.
See `docs/decisions/` and `ROADMAP.md`.

## How it was tested
- **(a) Real transcript**, smaller limits (the sample was short): correctly
  ranked the "Always back up your files… the most important thing" clip highest
  (hook opening + emphasis words).
- **(b) Synthetic 2-minute transcript**, default 20–60 s limits, pick 3:
  verified **automatically** that all chosen clips are 20–60 s, non-overlapping,
  and chronological, and that question/emphatic lines outscored "boring filler".

## Result / what worked
Both tests passed. The picker favored hooky/question/emphatic moments and
produced clean, non-overlapping, sentence-aligned clips.
