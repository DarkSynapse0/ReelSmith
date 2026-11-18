# Step 12 — Interactive menu mode + captions on/off

## Goal
Typing long commands with lots of flags is error-prone and unfriendly for a
beginner. This step adds a **step-by-step menu** so you can run the tool by
answering a few simple questions instead of memorising options — and a toggle to
**skip captions** when you don't want them.

## What was built
- **`src/reelsmith/interactive.py`** — a friendly wizard built only on
  Python's built-in `input()` (no extra libraries). It asks, in order, for:
  1. the **video** (a URL or a local file path),
  2. the **language** (auto / ne / en / hi),
  3. the **model size** (tiny / base / small / medium / large-v3),
  4. the **number of clips**,
  5. the **vertical style** (crop / blur / track),
  6. **captions on/off**, and — if on — the **caption style** (classic / bigword),
  7. optional **advanced settings** (shortest/longest clip length).

  It then prints a **summary** and asks for confirmation before starting the
  (slow) work. For every question, pressing **Enter accepts the shown
  `[default]`**. Each menu accepts the list **number**, the **value** itself, or
  Enter.
  - Helper functions: `_ask_text`, `_ask_choice`, `_ask_yes_no`, `_ask_int`.
  - Entry point `collect_settings()` returns a settings dict, or `None` if the
    user cancels at the final confirmation.
- **`src/reelsmith/cli.py`:**
  - The `video` argument is now **optional** (`nargs="?"`). If **no video is
    given**, or **`-i`/`--interactive`** is passed, the wizard runs and then
    calls `run(...)`. `interactive` is imported **lazily** inside `main()`.
  - Added **`--no-captions`**.
- **`cli.run()`** gained a **`captions_on=True`** parameter. When captions are
  off, the vertical clip becomes the final clip directly (via `shutil.move`),
  skipping the ASS-generation and burn-in steps.

## How it was tested
1. **Wizard run (piped answers).** Drove the menu with: local file → English →
   `tiny` → 1 clip → `crop` → captions yes/`classic` → advanced yes (8–14 s) →
   start. It showed the numbered menus, printed a correct summary
   (`Captions: yes — classic`, `Clip length: 8–14 s`), ran the full pipeline, and
   produced a **1080×1920** clip.
2. **No-argument launch.** Running `reelsmith` with no arguments correctly
   opens the wizard (the `video` argument defaults to `None`).
3. **Captions toggle.** `reelsmith … --no-captions` produced a clip with **no
   captions** — the vertical clip was moved straight to the final output with no
   ASS/burn step.
4. **Regression.** The 3 unit tests still pass, and `reelsmith --help` lists
   `-i/--interactive` and `--no-captions` and notes that leaving the video out
   launches the interactive menu.

## Result / what worked
You can now run the tool with **zero flags** — just `reelsmith` — and be
guided through every choice, or skip captions entirely when you only want the
cut/vertical clips. Both front-ends (flags and menu) funnel into the exact same
`run(...)` pipeline. ✅

## Limitation / future
The wizard chooses settings **before** anything runs. A natural next step (see
`ROADMAP.md`) is **post-generation clip selection**: after the clips are made,
list them with their scores and let you pick which to **keep or delete** — a
direct extension of the "what I need / what I don't need" idea.
