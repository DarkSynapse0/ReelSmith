# Step 13 — Polished interactive TUI (rich + questionary)

## Goal
The 0.6.0 menu (plain `input()` prompts) worked, but typing numbers at bare
prompts still felt clunky. This step turns it into a **polished terminal user
interface (TUI)**: a title banner, **arrow-key** option lists, a job-summary
panel, and clean **progress bars** while it works — the kind of experience you'd
expect from a real product. This is the **1.0 milestone**.

## What was built
- Rewrote **`src/videoclipper/interactive.py`** around two small, free,
  open-source libraries:
  - **rich** — the rounded **banner**, the **📋 JOB CONFIGURATION** panel, a
    final **results panel** (each clip's time + score), and the **staged
    progress bars**.
  - **questionary** — the **arrow-key option lists** (● selected / ○ not) for
    language, model, framing, and caption style, plus text and confirm prompts.
- **`launch()`** is the new entry point and chooses the experience:
  - **Real terminal** → `_pretty_collect_settings()` (the fancy menu) then
    **`run_with_progress(settings)`**.
  - **Not a TTY** (piped / non-interactive) → `_plain_collect_settings()`
    (simple typed prompts) + the normal logging pipeline `cli.run(...)`.
- **`run_with_progress()`** shows a multi-stage display:
  **[1/4] download** (URL only) → **transcribe** → **find moments** →
  **render** (a real per-clip progress bar). A local file shows **3 stages**
  (no download stage). It finishes with the results panel.
- Added a module-level **`utils.QUIET`** flag. When it's on, `utils.info()` /
  `utils.ok()` and the per-segment transcript print in `transcribe.py` stay
  silent, so the progress bars aren't buried under log lines.
  `run_with_progress` turns it on for the progress section and restores it after.
- **`download.download_video(url, dir, quiet=False)`** gained a `quiet` option
  (adds `-q --no-warnings` and captures output) so yt-dlp's text doesn't break
  the bars.
- **`src/videoclipper/cli.py`:** the no-video / `-i` path now just calls
  `interactive.launch()`.
- **Version bumped to 1.0.0** (`__init__.py`, `pyproject.toml`). Added
  dependencies **`rich>=13.0.0`** and **`questionary>=2.0.0`**.

## How it was tested
1. **Rendering.** The banner `Panel` and the **📋 JOB CONFIGURATION** panel both
   render correctly (verified the box output).
2. **Progress pipeline.** `run_with_progress` on a local file ran **3 stages**
   (transcribe / find / render) with percentage + elapsed-time bars, printed the
   results panel (`clip_01.mp4`, its time range, **score 5.033**), and produced a
   **1080×1920** clip.
3. **Non-TTY fallback.** Piping answers into `videoclipper` (no real terminal)
   correctly dropped to "simple mode" and still produced a clip.
4. **Regression.** The 3 unit tests still pass and `videoclipper --help` still
   works.

**Caveat:** the **live arrow-key questionary menu** itself can't be auto-tested
without a real terminal, so that interaction was not exercised in an automated
run. The rendering, the progress pipeline, and the plain fallback were all
verified; the arrow-key selection uses standard, well-tested questionary prompts.

## Result / what worked
Running `videoclipper` with no arguments now gives a genuinely pleasant,
product-like TUI — a banner, arrow-key menus, a configuration summary, and live
progress — while remaining 100% free and local. It gracefully degrades to plain
prompts anywhere a real terminal isn't available. ✅

## Limitation / future
- The download / transcribe / find stages currently fill to 100% on completion
  (the bar isn't a live percentage mid-stage). A nice future touch is a **live
  transcription percentage** (advance the bar using each segment's end time
  against the total duration).
- Still a good pairing for the roadmap's **post-generation clip picker**: after
  rendering, let the user tick which clips to keep or delete.
