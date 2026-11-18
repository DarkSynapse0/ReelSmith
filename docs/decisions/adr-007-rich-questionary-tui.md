# ADR-007: Use rich + questionary for the interactive terminal UI

**Status:** Accepted (v1.0.0)
**Context:** The interactive mode (run `reelsmith` with no arguments) should
feel like a polished product — a banner, arrow-key option lists, a configuration
summary, and live progress — not a wall of bare text prompts.

## Context
Version 0.6.0 built the interactive menu on Python's built-in `input()` with **no
extra dependencies**. It worked, but it could only print plain lines and read
typed numbers. There was no way to:
- draw boxes/panels or use colour,
- offer true **arrow-key** selection (● highlight, ○ others),
- show **progress bars** for the long-running stages.

Doing all of that by hand (raw terminal control codes, cursor handling, SIGWINCH,
etc.) is a lot of fragile code to maintain, especially for a beginner-friendly
project.

## Decision
Adopt two small, widely-used, MIT-licensed libraries:
- **rich** — for the banner `Panel`, the **📋 JOB CONFIGURATION** panel, the
  results panel, and the staged **progress bars**.
- **questionary** — for the **arrow-key option menus** and text/confirm prompts.

Design points:
- **`launch()` detects the terminal.** If `stdin`/`stdout` are a real TTY it uses
  the fancy UI; otherwise it falls back to simple typed prompts and the normal
  logging pipeline. This keeps piped/scripted/non-interactive use working (and
  testable) without a terminal.
- **A `utils.QUIET` flag keeps output clean.** The pipeline's normal
  `info()`/`ok()` chatter (and the per-segment transcript print) would otherwise
  scroll underneath the progress bars, so `run_with_progress()` silences them for
  the duration and `download_video(quiet=True)` hides yt-dlp's text.
- **The TUI is only a front-end.** It calls the same building-block functions as
  the flags path, so there's no duplicated pipeline logic — just a nicer way to
  collect settings and show progress.

## Rationale
- **rich and questionary are the standard tools** for exactly this and are both
  free, open source, pure-Python, and offline — fully consistent with the
  project's "local & free" rule (they don't make any network calls).
- **Far less code, far more robust** than hand-rolling terminal control.
- **Graceful degradation** means the tool still works when piped or run in an
  environment without a real terminal.

## Consequences
- ✅ A genuinely polished interactive experience: banner, arrow-key menus, job
  panel, live progress bars, results panel.
- ✅ Non-TTY use still works via the plain fallback.
- ✅ No duplicated pipeline code — the TUI reuses the same functions.
- ⚠️ Adds **two dependencies** (`rich`, `questionary`, which pulls in
  `prompt_toolkit`). Small and pure-Python, judged worth it for a 1.0 UI. This is
  a reversal of 0.6.0's deliberately dependency-free choice — justified now that
  the UX goal is a product-quality interface rather than a minimal prototype.
- ⚠️ The **live arrow-key menu can't be auto-tested** without a real terminal, so
  that part relies on questionary's own maturity; the rendering, progress
  pipeline, and fallback are tested.

## Alternatives considered
- **Stay dependency-free with `input()`** (the 0.6.0 approach) — no boxes, no
  arrow keys, no progress bars; not the product feel we wanted for 1.0.
- **Hand-rolled ANSI/terminal control** — maximum control, but a lot of fragile,
  hard-to-maintain code for no real benefit over rich.
- **A full-screen TUI framework (e.g. Textual, urwid)** — more powerful than
  needed; a full-screen app is heavier and less "command-line native" than the
  inline banner + prompts + progress bars we chose.
