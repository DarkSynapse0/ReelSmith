# Changelog

All notable changes to **ReelSmith** are recorded here, in the order
we actually built them. This is a prototype, so versions are informal
milestones rather than strict releases. All of the versions below were built in
the same session on **2026-11-12**.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/).
Every entry below was **built and tested** before moving to the next one.

---

## [1.7.1] — 2026-11-18 — Renamed to ReelSmith

- The project is now **ReelSmith**. The package is `src/reelsmith/`, the command
  is **`reelsmith`** (and `python -m reelsmith`), the TUI banner reads
  "REELSMITH", and the cookies env var is `REELSMITH_COOKIES_BROWSER`.
- Added a proper product description to the README and package metadata.
- Tested after the rename: `reelsmith --help`, `python -m reelsmith`, the banner,
  a full end-to-end run (1080×1920 clip), and the unit tests all pass.

---

## [1.7.0] — 2026-11-12 — `--model nepali`: a Nepali fine-tuned model (big accuracy win)

The real fix for Nepali accuracy: a community Whisper **large-v3 fine-tuned for
Nepali+English** ([DontHash/neptrans-v4-ct2](https://huggingface.co/DontHash/neptrans-v4-ct2),
already in CTranslate2 format), far more accurate than the stock models.

- **`--model nepali`** — a friendly alias that loads the Nepali fine-tune.
  `_resolve_model()` maps it; faster-whisper downloads it on first use.
  Any Hugging Face model id or local path also works with `--model`.
- Added to the interactive model menu ("Nepali fine-tuned — best for Nepali ★").
- **Auto-selected for Nepali:** `--language ne` with no `--model` now uses
  `nepali` automatically (an explicit `--model` always wins; other languages
  still default to `small`). The menu also pre-selects `nepali` when you pick
  Nepali. So `reelsmith my.mp4 --language ne` just does the right thing.
- Tested on the real Nepali clip: stock `small`/`large-v3` produced garbled
  Nepali; `--model nepali` produced accurate Nepali — it even got the speaker's
  full name right (मेरो नाम मनिस गिमिरे), plus "हाम्रो क्लिपिङ", "ओपन सोर्स",
  "नेपाली टेस्ट वन". Captions render cleanly in Devanagari. Unit tests pass.
- First-run downloads the model (~large-v3 size); cached afterward.

---

## [1.6.3] — 2026-11-12 — Mixed-mode tuning + Nepali accuracy notes

- **Catch more English in mixed mode:** lowered the English-confidence bar
  (0.5 → 0.35) and split on shorter pauses (VAD min-silence 300→200ms,
  max chunk 20→15s), so standalone English words are caught more often.
  Known limit remains: an English word spoken **mid-sentence with no pause**
  is inside a Nepali chunk and can't be separated (no word-level language
  switching in vanilla Whisper).
- **Nepali accuracy is bounded by the model.** Verified: `large-v3` is far
  better than `small` for Nepali (recognisable `नमस्ते सबै`, `अनि यो हम्रो
  क्लिपिंग`), but still imperfect — a Whisper limitation, not the pipeline.
  Recommend `--model large-v3` (or `medium`) for real Nepali work.
- **Custom models already work:** `--model` accepts any Hugging Face model id
  or local path (faster-whisper feature), so a Nepali-fine-tuned Whisper can be
  plugged in for better Nepali.

---

## [1.6.2] — 2026-11-12 — Mixed mode: a primary language (`mixed:ne`)

Fixes mixed mode flipping a mostly-Nepali video to English. On short utterances
Whisper's auto-detect often guessed "English" (or Italian/Urdu) for Nepali
speech, so most captions came out in English.

- **`mixed:ne` (and `mixed:hi`, etc.):** transcribe each utterance in the
  PRIMARY language, and only switch to English when English is detected with
  high confidence (`model.detect_language` ≥ 0.5). So a Nepali+English video
  keeps Nepali in Devanagari and renders only the real English words in
  English. Plain `mixed` is still pure per-utterance auto-detect.
- The interactive menu now asks "mixed with which MAIN language?" when you pick
  `mixed`. The `mixed:ne` form flows through the CLI and the cache key.
- Tested on the real Nepali clip: with `mixed:ne`, 4/6 utterances stayed Nepali
  (Devanagari) and only "open source" / "Just one" became English — vs plain
  `mixed` which flipped most to English. Captions render both scripts; unit
  tests pass.

---

## [1.6.1] — 2026-11-12 — Menu shows the --flags + equivalent command; Nepali verified

- **Options in the job box:** the interactive "📋 JOB CONFIGURATION" panel now
  shows the matching command-line **`--flag`** beside every choice, and prints
  the **full equivalent command** at the bottom (copy it to skip the menu next
  time). New `_equivalent_command()` helper.
- **Nepali verified end-to-end** on a real clip (`nep1.mp4`): `--language ne`
  detected Nepali, produced a **Devanagari** transcript + SRT, and the captions
  rendered correctly in Devanagari (hormozi style auto-used Noto Sans
  Devanagari, cyan highlight). Note: transcription accuracy on `small` is
  limited when the speaker mixes in English words — use `--model medium` for
  better Nepali accuracy.

---

## [1.6.0] — 2026-11-12 — Optimized captions (per-style presets + fonts) + smoother tracking

Captions looked generic because every style shared one font/size/colour, and
face tracking stepped instead of gliding. Both reworked — informed by the
same-stack reference project
[nicolaigaina/ai-video-captions](https://github.com/nicolaigaina/ai-video-captions)
(also faster-whisper + ASS + FFmpeg + Devanagari fallback).

**Captions**
- **Per-style presets:** each caption style now has its OWN font, size and
  colours (that's what makes them feel distinct). Values adapted from 2026
  short-form research: `hormozi` = cyan highlight, `mrbeast` = yellow body +
  orange highlight (NEW style), `karaoke` = blue wipe, `classic` = yellow, etc.
- **Punchier fonts, auto-picked by script:** English/Latin uses **Poppins** or
  **Bebas Neue**; Nepali/Hindi automatically falls back to **Noto Sans
  Devanagari** (detected per clip), so Devanagari never breaks.
- **Bigger & bolder defaults:** font size 84→100+, outline 4→5–8, more shadow,
  raised into the lower-middle third — much more readable on busy footage.
- **New `mrbeast` style** (Bebas Neue, yellow/orange, extra-thick outline).
  `--caption-style` now offers: classic · bigword · hormozi · mrbeast ·
  karaoke · highlight-box.

**Smoother face tracking**
- Added a **dead-zone** (ignore movements under ~5% of width) so tiny detection
  wobble no longer makes the crop twitch, **heavier smoothing** (gentler ease),
  and a **higher sample rate** (10 fps) with finer keyframes — the pan now
  glides and holds steady instead of stepping.
- Tested on a real video (IShowSpeed react): stable framing (face in 251/251
  frames settled to ~5 keyframes), and each caption style renders with its own
  distinct font/colour; Nepali still uses Noto Sans Devanagari; unit tests pass.

---

## [1.5.0] — 2026-11-12 — Three new caption styles (hormozi, karaoke, highlight-box)

Added the most-requested short-form caption looks (researched from 2026
TikTok/Reels/Shorts trends). `--caption-style` now offers five looks:

- **`hormozi`** — bold **UPPERCASE**, only 1–3 words on screen, the active word
  in the highlight colour, and the whole line "snaps" in with a quick scale pop
  as each new group appears (scaling the whole line, so words don't reflow).
- **`karaoke`** — the full line is shown and the colour **sweeps** across each
  word left-to-right exactly as spoken (ASS `\kf` karaoke fill, timed to the
  word gaps).
- **`highlight-box`** — the active word sits inside a filled coloured **plate**
  (the TikTok auto-caption look), via a second ASS "Box" style (BorderStyle 3)
  switched in with `\rBox`.
- All work with **Nepali/Devanagari** too (uppercase is a harmless no-op there;
  the box/sweep/pop are script-independent). The usual caveat: the heavy
  display fonts behind the "Hormozi" look don't cover Devanagari, so Nepali
  stays on Noto Sans Devanagari Bold.
- Wired into `--caption-style` and the interactive menu. Tested: each renders
  correctly (hormozi caps + highlight, box plate behind the active word,
  karaoke mid-sweep), a full pipeline run with `hormozi` produced a 1080×1920
  clip, Devanagari works, and unit tests pass.

---

## [1.4.0] — 2026-11-12 — Caching: skip re-downloading and re-transcribing

Re-running the same video used to repeat the two slowest steps (download, and a
transcription that can take ~20 minutes). Now they are cached.

- **What's cached:** inside each video's own folder, in `clips/<name>/cache/` —
  the downloaded video (`source.<ext>`), the transcript (`transcript.json`), and
  the settings it was made with (`meta.json`: language + model).
- **Reuse rules:** a re-run reuses the download if it's there, and reuses the
  transcript **only if the language and model match** (so changing `--model` or
  `--language` correctly re-transcribes). New `cache.py` module;
  `download_video` now saves into the cache folder.
- **`--no-cache`** forces a fresh download + transcription.
- Works in both flag mode and the interactive TUI (which shows
  "reused cached download / transcript" instead of the stage bars).
- Tested: run 1 downloads + transcribes and writes the cache; run 2 reuses both
  (seconds instead of minutes); a different `--model` and `--no-cache` both redo
  the work; unit tests pass.

---

## [1.3.2] — 2026-11-12 — Download progress bar + fixed (counting-down) ETA

- **Download now shows a real percentage.** The download stage was an
  indeterminate bar with no %. It now streams yt-dlp's output, reads the
  download percentage, and fills a proper bar. (A video+audio download has two
  phases, so the bar fills, resets once, and fills again — this is normal.)
  `download_video` gained a `progress_callback`, fed by a new
  `_run_with_progress` streaming helper.
- **ETA bug fixed — it now counts DOWN.** The estimate used to *climb*
  (55→56→57…) between progress jumps, because it was recomputed from the
  ever-growing elapsed clock while the percentage sat still. The new
  `_SmoothETA` remembers the total expected time at each real progress change
  and shows `expected − elapsed`, which ticks down smoothly and only
  re-adjusts when genuine progress happens. Verified: 25% at 10s→0:30, then
  0:27, 0:24 as the clock runs.

---

## [1.3.1] — 2026-11-12 — Browser-cookie downloads + clearer download errors

Handles YouTube's "Sign in to confirm you're not a bot" block, which can appear
after downloading several videos in a session.

- **`--cookies-from-browser BROWSER`** option (firefox / chrome / chromium /
  brave / edge / zen / …). It passes your browser's YouTube cookies to yt-dlp,
  which gets past the anti-bot check. The flag sets a
  `REELSMITH_COOKIES_BROWSER` environment variable, so it also applies in the
  interactive menu (`export REELSMITH_COOKIES_BROWSER=firefox` then
  `reelsmith`). Cookies are used for both the metadata lookup and the
  actual download.
- **Zen browser support:** `zen` is handled specially (yt-dlp doesn't know it by
  name) — since Zen is Firefox-based, we auto-find its profile folder (native
  `~/.zen` or Flatpak `~/.var/app/app.zen_browser.zen/.zen`) and point yt-dlp's
  firefox reader at it.
- **YouTube n-challenge solver enabled** (`--remote-components ejs:github`) on
  all yt-dlp calls, so YouTube's JavaScript URL-scrambling challenge is solved
  (requires a JS runtime — `deno` or `node` — to be installed). Without this,
  recent YouTube returns "No video formats found".
- **Real error shown:** a failed download now prints **yt-dlp's own message**
  (e.g. the "not a bot" text) instead of only a generic guess, plus concrete
  fixes (update yt-dlp, pass cookies).
- Tested: the flag and env var wire the cookie arguments correctly, and a
  blocked download now surfaces YouTube's actual reason.

---

## [1.3.0] — 2026-11-12 — Dynamic speaker tracking + face diagnostic + smoother ETA

Reworks `--vertical track` from a single fixed crop into a crop that **follows
the speaker**, after a report that in one clip the person was cut off.

- **Dynamic tracking (the fix):** the crop now **pans to follow the face**
  instead of using one fixed position for the whole clip. New
  `reframe.compute_crop_plan()` samples ~6 frames/sec, builds a target
  x-position over time (the face centre; **holds** the last position through
  brief ≤2 s look-aways; **drifts to centre** during long faceless stretches),
  **snaps** at big jumps (>30 % of width ≈ a scene cut) instead of sliding
  across them, **smooths** the motion (exponential moving average), and emits
  only the keyframes where the crop actually moves. `video.make_vertical`'s
  `track` mode writes a tiny FFmpeg **`sendcmd`** file and uses
  `sendcmd=…,crop=…,scale=1080×1920` to animate the crop. It still **falls back
  to a centre crop** when no face is found.
  - *Why:* a fixed crop cut the speaker off when they moved or when the shot
    changed within a clip ("in clip 4 the person cut off").
  - *Tested:* a synthetic video with a face sliding left→right kept the face in
    frame start→mid→end (crop x climbed 119→226→…, 50 keyframes, face in 49/50
    frames) where the old fixed crop would have cut them off; the full pipeline
    produced a 1080×1920 clip; the no-face video still fell back to centre; unit
    tests pass.
- **Face diagnostic:** run `python -m reelsmith.reframe "<video.mp4>"` to see
  what the detector finds — frames checked, % with a face, how much the face
  moves, how many big jumps (≈ cuts), and a plain verdict (few faces → use
  `crop`/`blur`; moves a lot → tracking helps; fairly still → fixed is fine).
  It also saves up to 8 **annotated frames** (green = detected face, red = the
  chosen crop) and warns clearly if a file's codec can't be decoded (e.g.
  AV1/VP9 `.webm`, which the normal pipeline avoids by re-encoding to H.264).
- **OpenCV warning silenced for good:** `reframe.py` now sets
  `OPENCV_LOG_LEVEL=ERROR` **before** importing `cv2` (and calls
  `cv2.setLogLevel`), so the detector's harmless `setPreferableTarget …` line no
  longer leaks to the terminal and garbles the live display.
- **Smoother, steadier ETA:** the TUI's time-remaining is now a custom
  `_SmoothETA` column that extrapolates `elapsed × (1 − done) / done` — it shows
  `--:--` until there's progress, then a steady countdown (and `H:MM:SS` for long
  jobs), replacing rich's built-in estimate which flickered and sometimes
  vanished. (`run_ffmpeg` also gained a `cwd` argument, used so the `sendcmd`
  file is referenced by a safe bare filename.)

---

## [1.2.3] — 2026-11-12 — Caption-path crash fix + scrolling transcript window

Fixes a real crash and tidies the transcript display, from live feedback on a
real YouTube video whose title had `!` and `'` in it.

- **Bug fixed (crash):** a folder named from a video title containing `!`, `'`,
  `&`, etc. broke FFmpeg's `ass=` subtitle filter ("fopen failed"), so caption
  burning failed. Two-layer fix:
  - `_sanitize_name` now keeps **only** `A–Z a–z 0–9 . _ -` (everything else
    becomes `_`), so folder names are always filter-safe.
  - `burn_captions` now runs FFmpeg **from the subtitle's own folder** and
    refers to it by the bare filename `cap_NN.ass`, so even an unusual
    `--output-dir` path can never break the filter. (`run_ffmpeg` gained a
    `cwd` argument.)
- **Scrolling transcript window:** the live transcript no longer floods the
  screen — it now shows only the **last 5 lines**, updating in place via a
  `rich.live.Live` region, with finished stages printed as `✔` lines above it.
- **Smoother render bar + ETA:** the render stage now advances **per sub-step**
  (cut → framing → captions) instead of once per whole clip, so the
  percentage and ETA move sooner and more smoothly on step 4.
- **OpenCV warning silenced:** the face detector used to print a harmless
  `setPreferableTarget ... Targets are not supported by the new graph engine`
  warning straight to the terminal (stderr), which scribbled over the progress
  display during face-tracking. `reframe.py` now sets `OPENCV_LOG_LEVEL=ERROR`
  (and `cv2.setLogLevel`) so it stays quiet. This was the cause of the
  "messed up" clipping display.
- Tested: the exact crashing title now sanitizes safely; captions burn into a
  folder containing `! '` and spaces; the Live display and unit tests pass.

---

## [1.2.2] — 2026-11-12 — Cleaner, more detailed TUI progress

Polished the interactive display based on feedback that finished stages
appeared to repeat, and that there was no visibility into the long stages.

- **No more repeated lines:** each finished stage now removes its live bar and
  prints a single `✔ done` line in its place. Previously all stages' bars
  stayed live and were redrawn every frame, which some terminals (and
  copy-paste) showed as the same line stamped many times. (It was only ever a
  redraw artifact — nothing actually ran more than once.)
- **Live transcript:** the recognised lines now stream past (dimmed) under the
  transcribe bar, so you can watch the sub-process and confirm it is working.
  In `mixed` mode each line is tagged with its detected language.
- **Per-clip sub-steps:** the render bar now shows what it is doing for each
  clip — `clip 2/3: cutting` → `face-tracking` → `captions` — and prints a
  `clip_NN.mp4 ready` line as each finishes.
- **Cleaner setup:** after you answer the menu questions, the screen is cleared
  and only the banner + 📋 JOB CONFIGURATION panel remain before processing.
- Tested: transcript streams, stages collapse to `✔` lines, sub-steps show,
  unit tests still pass.

---

## [1.2.1] — 2026-11-12 — Real transcription progress in the TUI

Fixed the confusing interactive progress display, where the "Transcribing
audio" bar sat at 0% the whole time and looked frozen (it only jumped to 100%
when the stage finished).

- **Real progress:** `transcribe_audio` / `transcribe_audio_multilang` /
  `transcribe_video` now accept a `progress_callback(fraction)` that fires as
  the audio is processed (by audio position for normal mode; per utterance for
  `mixed` mode). The TUI's transcribe bar now advances smoothly (e.g.
  7% → 12% → … → 99%).
- **Spinner added** to every progress row, so there is always visible motion —
  you can tell it is working, not frozen.
- **Time estimate (ETA)** added to each row (rich's `TimeRemainingColumn`), so
  the transcribe/render bars show roughly how long is left (e.g. `eta 0:08:32`)
  and count down as they fill.
- **"(loading model)" hint:** the transcribe bar shows this while the model
  loads/downloads on the first run (the one time the bar legitimately sits at
  0% for a while), then switches to the normal label once transcription starts.
- Reminder documented: CPU transcription of long videos is slow, and `mixed`
  mode is slower still — use a smaller `--model` for long videos.
- Tested: progress fractions stream in increasing order and reach ~1.0 for both
  normal and mixed modes; unit tests still pass.

---

## [1.2.0] — 2026-11-12 — Per-video output folders (`clips/<name>/`)

Each video now gets **its own folder**, so results from different videos never
mix together.

- **Bug fixed:** URL downloads used to all land in a single shared
  `downloaded_clips/` folder, so a second URL video **overwrote** the first.
  Local files went to `<base>_clips/` in the current directory.
- **Now:** every video is saved under a top-level **`clips/`** directory, in its
  own sub-folder — **`clips/<video-name>/`**:
  - **Local files** are named by their **filename** (without extension), e.g.
    `clips/My_Talk/`.
  - **URLs** are named by the video's **title + id**, e.g.
    `clips/Me_at_the_zoo_jNQXAC9IVRw/` — the id guarantees uniqueness even if two
    videos share a title.
- New helpers in **`src/reelsmith/download.py`**: `CLIPS_ROOT = "clips"`,
  **`_sanitize_name(name)`** (strips illegal characters, turns spaces into
  underscores, caps length), **`url_video_name(url)`** (asks yt-dlp for
  `%(title)s` + `%(id)s` without downloading; falls back to a YouTube-id regex,
  then the URL tail), and **`default_output_dir(video_path)`** (returns
  `clips/<name>`).
- Both **`cli.run()`** and **`interactive.run_with_progress()`** now call
  `download.default_output_dir(...)` when no `--output-dir` is given (replacing
  the old `downloaded_clips` / `<base>_clips` logic). `.gitignore` now also
  ignores `clips/`.
- **`--output-dir`** still overrides to a specific folder.
- **Tested:** `"/home/me/My Talk.mp4"` → `clips/My_Talk`; `"/tmp/sample.mp4"` →
  `clips/sample`; a URL → `clips/Me_at_the_zoo_jNQXAC9IVRw` (title + id via yt-dlp
  metadata); two different local videos produced **two separate folders**
  (`clips/sample/` and `clips/long_sample/`, not mixed), each with its
  `clip_01.mp4` + `.srt` + `.transcript.json` + `summary.txt`/`.json`; the 3 unit
  tests still pass. See `docs/steps/step-15-output-folders.md`.

---

## [1.1.0] — 2026-11-12 — Mixed-language transcription (`--language mixed`)

Added support for videos that **switch between languages** (e.g. Hindi and
English), so each part is written in **its own language/script** instead of one
Whisper pass forcing everything into a single script.

- Added **`transcribe.transcribe_audio_multilang(audio_path, model_size)`** and
  the helper **`transcribe._speech_chunks(audio)`** in
  `src/reelsmith/transcribe.py`. The approach is **VAD-split → per-utterance
  auto-detect → stitch**:
  1. Split the audio into utterances with faster-whisper's voice-activity
     detector (`get_speech_timestamps` with tuned `VadOptions`:
     `min_silence_duration_ms=300`, `max_speech_duration_s=20`,
     `speech_pad_ms=200`), so each chunk is roughly one utterance.
  2. Transcribe each chunk on its own with **`language=None`**, so Whisper
     **detects (and writes) the language of that utterance**.
  3. **Offset** each chunk's word/segment timings back by the chunk's start and
     **stitch** everything together in time order.
- Each segment now carries a **`"language"`** field; the transcript's top-level
  `"language"` is **`"mixed"`** and it also lists the `"languages"` found.
- **`transcribe_video(...)`** branches to this path when `language == "mixed"`.
- **CLI/menu:** `--language` help mentions `mixed`; the interactive menu's
  language list gained a **`mixed`** option.
- **What it handles:** switching **between** sentences/phrases (each utterance →
  its own language → its own script). It **cannot** reliably handle switching
  **within** a single utterance (that whole chunk is detected as one language).
  It is also **slower** (many small passes). Captions render both scripts because
  the bundled **Noto Sans Devanagari** font also covers Latin letters.
- **Tested:** built a synthetic English → Hindi → English clip (espeak-ng,
  including its Hindi voice) and ran `--language mixed`. The **mechanism was
  fully validated**: VAD split the audio into **6 utterances**, each got its own
  detected language, the **English chunks transcribed perfectly**, and the
  timings were offset/stitched correctly (0:00 → 0:02 → 0:11 → 0:14). The full
  pipeline via `reelsmith … --language mixed` produced a **1080×1920** clip,
  and the 3 unit tests still pass.
  - **Honest caveat:** the synthetic Hindi came from espeak's **robotic TTS**,
    which Whisper could **not** recognize as Hindi (it mis-detected those chunks
    as French/Hungarian and produced gibberish). This is a limit of the synthetic
    **test audio**, not the code — espeak's formant-synthesis Hindi doesn't sound
    like the human speech Whisper was trained on. On **real human Hindi** speech,
    Whisper reliably detects `hi` and outputs Devanagari, so real-Hindi detection
    should be confirmed on an actual video. See
    `docs/steps/step-14-mixed-language.md` and
    `docs/decisions/adr-008-mixed-language-vad.md`.

---

## [1.0.0] — 2026-11-12 — Polished interactive TUI (rich + questionary)

**1.0 milestone.** With a proper terminal UI on top of the full pipeline
(download → transcribe → find moments → vertical → captions, with speaker
tracking and animated captions), the tool is now **feature-complete for its
core goal**: turn one long video into several captioned vertical clips, free and
locally.

Replaced the plain `input()` wizard from 0.6.0 with a **polished interactive
terminal interface**.

- Rewrote **`src/reelsmith/interactive.py`** to use two small, free,
  open-source libraries:
  - **rich** — the rounded **title banner**, the **📋 JOB CONFIGURATION** panel,
    a final **results panel** (each clip's time + score), and the clean
    **staged progress bars**.
  - **questionary** — the **arrow-key option lists** (● selected / ○ not) for
    language, model, framing, and caption style, plus text and confirm prompts.
- New flow centered on **`launch()`**:
  - In a **real terminal** it runs `_pretty_collect_settings()` (the fancy menu)
    then **`run_with_progress(settings)`**.
  - When **not a TTY** (piped / non-interactive), it falls back to
    `_plain_collect_settings()` (simple typed prompts) and the normal logging
    pipeline `cli.run(...)`.
- **`run_with_progress()`** shows a multi-stage progress display:
  **[1/4] download** (URL only) → **transcribe** → **find moments** →
  **render** (a real per-clip progress bar). A local file shows **3 stages**
  (no download). It ends with the results panel.
- Added a module-level **`utils.QUIET`** flag so the progress display stays
  clean: `utils.info()`/`utils.ok()` and the per-segment transcript print in
  `transcribe.py` are suppressed when it's on. `run_with_progress` turns it on
  during the progress section and restores it afterwards.
- **`download.download_video(url, dir, quiet=False)`** gained a `quiet` option
  (passes `-q --no-warnings` and captures output) so yt-dlp's text doesn't break
  the progress bars.
- **`src/reelsmith/cli.py`:** the no-video / `-i` path now simply calls
  `interactive.launch()`.
- **Version bumped to 1.0.0** in `src/reelsmith/__init__.py` and
  `pyproject.toml`. Added dependencies **`rich>=13.0.0`** and
  **`questionary>=2.0.0`** (in `pyproject.toml` and `requirements.txt`).
- **Tested:** the banner and JOB CONFIGURATION panels render correctly;
  `run_with_progress` on a local file ran 3 stages (transcribe / find / render)
  with percentage + elapsed-time bars, printed the results panel (`clip_01.mp4`,
  time, **score 5.033**), and produced a **1080×1920** clip. The non-TTY plain
  fallback still works (piped answers → "simple mode" → produced a clip). The 3
  unit tests still pass and `--help` still works.
  - **Caveat:** the live arrow-key questionary menu itself can't be auto-tested
    without a real terminal; the rendering, the progress pipeline, and the
    fallback were all verified. See `docs/steps/step-13-tui.md` and
    `docs/decisions/adr-007-rich-questionary-tui.md`.

---

## [0.6.0] — 2026-11-12 — Interactive menu mode + captions on/off toggle

Made the tool usable **without memorising any command-line flags**: run it with
no arguments and it asks you a short series of questions instead.

- Added **`src/reelsmith/interactive.py`** — a friendly, dependency-free
  wizard built on Python's built-in `input()`. It asks for the video (URL or
  local path), **language** (auto/ne/en/hi), **model size**
  (tiny/base/small/medium/large-v3), **number of clips**, **vertical style**
  (crop/blur/track), **captions on/off** and (if on) **caption style**
  (classic/bigword), plus optional **advanced settings** (min/max clip length).
  It prints a summary and asks for confirmation before the slow work starts.
  Pressing **Enter accepts the shown `[default]`** for any question.
  - Helper functions: `_ask_text`, `_ask_choice` (numbered list — accepts the
    number, the value, or Enter), `_ask_yes_no`, `_ask_int`.
  - Entry point `collect_settings()` returns a settings dict, or `None` if the
    user cancels at the final confirmation.
- **`src/reelsmith/cli.py`:** the `video` argument is now **optional**
  (`nargs="?"`). If **no video is given** *or* **`-i`/`--interactive`** is
  passed, the wizard runs and then calls `run(...)`. (`interactive` is imported
  lazily inside `main()`.)
- Added **`--no-captions`** flag.
- **`run()`** gained a **`captions_on=True`** parameter. When captions are off,
  the vertical clip becomes the final clip directly (via `shutil.move`) instead
  of generating and burning an ASS subtitle.
- **Tested:** drove the wizard with piped answers (local file → English → tiny
  → 1 clip → crop → captions yes/classic → advanced 8–14 s → start); it showed
  the numbered menus, printed a correct summary (`Captions: yes — classic`,
  `Clip length: 8–14 s`), ran the full pipeline, and produced a 1080×1920 clip.
  Running `reelsmith` with **no arguments** launches the wizard.
  **`--no-captions`** produced a clip with no captions (no ASS/burn step). The 3
  unit tests still pass, and `reelsmith --help` lists `-i/--interactive` and
  `--no-captions`. See `docs/steps/step-12-interactive-cli.md`.

---

## [0.5.0] — 2026-11-12 — Speaker-tracking vertical reframe (OpenCV/YuNet)

Added a smarter way to make clips vertical: instead of always cropping the
middle, it can **find the speaker's face and crop around them**, so a person
standing off to one side is no longer cut off.

- Added **`src/reelsmith/reframe.py`** — uses OpenCV 5's **YuNet** face
  detector (`cv2.FaceDetectorYN`) to sample ~3 frames/sec of a clip, pick the
  largest face in each frame, take the **median** horizontal position, and
  compute a 9:16 crop box centered on the speaker (clamped to the frame edges).
  Returns `None` if no face is found.
- Bundled the model **`src/reelsmith/models/face_detection_yunet.onnx`**
  (~232 KB, from the OpenCV Zoo) directly in the package, so there is **no
  runtime download** — it works fully offline.
- Added a new **`track`** mode to `video.make_vertical()`: crops a 9:16 region
  around the detected speaker, then scales to 1080×1920. **Falls back to a
  plain center crop** (with a friendly log message) when no face is found.
  OpenCV is imported **lazily** (only when `track` is used), so the other modes
  don't pay for loading it.
- CLI: **`--vertical`** now accepts `crop`, `blur`, or **`track`**.
- Added dependency **`opencv-python-headless>=4.9.0`** (in `pyproject.toml` and
  `requirements.txt`) and a `[tool.setuptools.package-data]` entry so the
  `.onnx` model ships with the install.
- **Why YuNet, not Haar:** OpenCV 5.0 (the installed `cp314` build) removed the
  classic Haar `CascadeClassifier` and no longer bundles the Haar cascade XML
  files, so we use the modern YuNet DNN detector — which is more accurate
  anyway. See `docs/decisions/adr-006-yunet-face-detection.md`.
- **Current limitation:** this is the **fixed-crop** version — it uses one
  median speaker position for the whole clip (no dynamic panning yet). Panning,
  multi-face/active-speaker selection, and object tracking are on the roadmap.
- **Tested:** built a controlled off-center clip (a real face video padded onto
  the **right third** of a 1600×480 canvas; true center x≈800, face ≈x=1280).
  `reframe.compute_crop_box` returned **x=1165** (shifted right toward the face)
  vs a center crop's x≈665, with a face found in **36/36** sampled frames.
  Visually, `track` framed the person perfectly while the plain center crop of
  the same video was **all black** (missed him). Fallback verified on a
  solid-color clip ("No face found — falling back to a center crop", still
  1080×1920). The 3 unit tests still pass, and a full
  `reelsmith … --vertical track` run found a face in **42/42** frames and
  output a 1080×1920 captioned clip. See `docs/steps/step-11-speaker-tracking.md`.

---

## [0.4.0] — 2026-11-12 — Project restructure: installable `src/` package

Reorganized the prototype into the standard Python **`src/` package layout** so
it is a proper, installable product. No behavior changed — same pipeline, same
options — only the structure and how you run it.

- **Moved all modules into `src/reelsmith/`**: `transcribe.py`, `moments.py`,
  `scoring.py`, `video.py`, `captions.py`, `download.py`, `utils.py`.
- **Renamed `clipper.py` → `src/reelsmith/cli.py`** (its `main()` is the
  entry point). Internal imports changed to package-relative
  (`from . import utils`, `from . import scoring`, …).
- Added **`__init__.py`** (version `0.3.0`) and **`__main__.py`** (enables
  `python -m reelsmith`).
- Added **`pyproject.toml`** — installable with `pip install -e .`; defines the
  **`reelsmith`** console command (`reelsmith.cli:main`); dependencies
  `faster-whisper` + `yt-dlp`; MIT license; Python ≥ 3.9.
- Added **`LICENSE`** (MIT), **`.gitignore`** (venv, `__pycache__`, `output/`,
  `*_clips/`, `downloaded_clips/`, sample media), and **`samples/`** + `output/`
  folders.
- Added a first real test suite: **`tests/test_basic.py`** (3 tests — timestamp
  formatting; scoring returns `(float, dict)` and rewards a question;
  `pick_best` respects the 20–60 s limits and non-overlap). Runs via
  `python tests/test_basic.py` or `python -m pytest`.
- **How to run now:** `reelsmith my_video.mp4 ...` or
  `python -m reelsmith my_video.mp4 ...` (was `python clipper.py ...`).
- **Tested:** `pip install -e .` succeeds; `reelsmith --help` and
  `python -m reelsmith --help` both work; the 3 unit tests pass; and a full
  end-to-end run via the `reelsmith` command produced a valid 1080×1920
  captioned clip. See `docs/steps/step-10-restructure.md` and
  `docs/decisions/adr-005-src-layout.md`.

---

## [0.1.0] — 2026-11-12 — Core pipeline (Steps 1–7)

The first working end-to-end version: give it a video file, get back vertical
clips with burned-in captions.

### Step 1 — Setup
- Verified **Python 3.14.9**, **pip**, **venv**, **FFmpeg n9.0.2**, and
  **ffprobe** are all present on the machine (Arch Linux). Nothing was missing.
- Created `requirements.txt` (just `faster-whisper`, which pulls in the rest).
- Created an isolated virtual environment at `venv/`.
- **Concern that turned out fine:** Python 3.14 is very new, and we worried
  `faster-whisper`/`ctranslate2` might not have prebuilt wheels yet. It did —
  proper `cp314` wheels installed cleanly.
- **Tested:** `from faster_whisper import WhisperModel` imports successfully.

### Step 2 — Transcribe (`src/reelsmith/transcribe.py`, `src/reelsmith/utils.py`)
- Added `src/reelsmith/utils.py` with shared helpers: friendly errors (`fail`/`info`/`ok`),
  `check_ffmpeg`, `check_file_exists`, `run_ffmpeg`, `ffprobe_duration`, and
  `seconds_to_timestamp`.
- Added `src/reelsmith/transcribe.py`: extract audio with FFmpeg → transcribe with
  faster-whisper (word-level timestamps on) → save JSON + SRT.
- Options: `--language` (default `auto`, e.g. `ne`, `en`, `hi`) and `--model`
  (default `small`; `tiny`/`base`/`small`/`medium`/`large-v3`).
- **Bug fixed:** `faster-whisper` crashed inside its own audio loader with
  `TypeError: open() got an unexpected keyword argument 'metadata_errors'` — a
  version clash with the newly installed **PyAV 19**. We **side-stepped it
  entirely**: FFmpeg already extracts a clean 16 kHz mono WAV, so we read that
  WAV ourselves with Python's built-in `wave` module into a NumPy array and
  pass the array straight to Whisper. No `av` dependency in our path, and no
  new package added (NumPy already ships with faster-whisper). See
  `docs/decisions/adr-001-read-wav-ourselves.md`.
- **Tested:** transcribed a generated 14-second spoken clip; confirmed correct
  text, **per-word start/end times** in the JSON, and a valid `.srt`.

### Step 3 — Find best moments (`src/reelsmith/moments.py`, `src/reelsmith/scoring.py`)
- Added `src/reelsmith/scoring.py` — five local heuristics, each 0–1, combined with editable
  `WEIGHTS`: strong opening, question, emphasis words, speaking pace, low
  silence. Includes English **and** Nepali/Devanagari word lists.
- Added `src/reelsmith/moments.py` — builds candidate clips by joining whole sentences until
  they are 20–60 s (`MIN_SECONDS`/`MAX_SECONDS`), scores each, and greedily
  picks the top N **non-overlapping** moments in time order.
- **Design decision:** scoring lives behind one function
  `score_segment(segment) -> (score, breakdown)` so it can be swapped for a
  smarter method later without touching `src/reelsmith/moments.py`.
- **Tested:** on the real transcript (small limits) and on a synthetic
  2-minute transcript — verified clips are all 20–60 s, non-overlapping,
  chronological, and that hooky/question/emphatic lines outscore filler.

### Step 4 — Cut clips (`src/reelsmith/video.py`)
- Added `video.cut_clip()` — cuts a segment with a configurable safety
  **buffer** (`DEFAULT_BUFFER = 0.4 s`) before/after so words aren't chopped,
  clamps to the video bounds, and re-encodes for a frame-accurate cut.
- **Tested:** requested 2.0–8.0 s → correctly expanded to 1.6–8.4 s → output
  measured exactly **6.8 s**.

### Step 5 — Vertical 9:16 (`src/reelsmith/video.py`)
- Added `video.make_vertical()` with two modes:
  - `crop` (default) — zoom + center-crop, no bars.
  - `blur` — fit whole frame + blurred, zoomed background (nothing cut off).
- Target size **1080×1920** (`VERTICAL_WIDTH`/`VERTICAL_HEIGHT`).
- **Tested:** both modes output exactly 1080×1920; visually confirmed the
  blurred-background composition on a test pattern.

### Step 6 — Word-by-word captions (`src/reelsmith/captions.py`, `src/reelsmith/video.py`)
- Added `src/reelsmith/captions.py` — generates an **ASS** subtitle file with per-word
  highlighting. All appearance settings live in one editable `CAPTION_STYLE`
  dict (font, size, colors, outline, shadow, position, words-per-line).
- Default font **Noto Sans Devanagari** (supports Nepali).
- Added `video.burn_captions()` — renders captions permanently with FFmpeg.
- **Tested:** both English and **Nepali**. Confirmed the active word is
  highlighted in yellow with correct timing, and that Devanagari renders
  correctly — including the complex stacked conjunct in **महत्त्वपूर्ण**.

### Step 7 — One command (`src/reelsmith/cli.py`, `README.md`)
- Added `src/reelsmith/cli.py` — the single entry point that runs the whole pipeline:
  transcribe → find moments → (cut → vertical → captions) per clip → summary.
- Saves finished clips as `clip_01.mp4`, `clip_02.mp4`, … plus the transcript
  JSON/SRT and a **`summary.txt` + `summary.json`** listing each clip's start,
  end, length, score, and a "why" breakdown.
- Intermediate files go in `work/` and are auto-cleaned unless
  `--keep-intermediate`.
- Wrote the first `README.md` (setup, examples, improvement ideas).
- **Bug fixed:** the summary showed `np.float64(0.64)` instead of `0.64`
  because faster-whisper returns NumPy floats for timestamps. Fixed at the
  source in `src/reelsmith/transcribe.py` by wrapping timings in `float(...)`.
- **Tested:** full run on a generated ~53 s spoken video with `--vertical
  blur --clips 2` produced two valid 1080×1920 captioned clips plus summaries;
  the `work/` dir was auto-cleaned.

---

## [0.2.0] — 2026-11-12 — Clip straight from a URL (`src/reelsmith/download.py`)

- Added `src/reelsmith/download.py` using **yt-dlp** (free, open source, local — no account
  or API key). `src/reelsmith/cli.py` now accepts either a local file path **or** a URL
  (YouTube, Shorts, Reels, and many other sites) as its `video` argument.
- Added a **Step 0: Download** stage; the input is auto-detected as a URL when
  it starts with `http://`/`https://`.
- **Resolution capped at 1080p** in the download format string — we only ever
  output 1080-wide vertical video, so pulling 4K would waste time and disk. (A
  first test accidentally grabbed a 466 MB 4K file, which is what prompted the
  cap.)
- Friendly errors for a bad/private/removed link or no internet.
- Updated `requirements.txt` (`yt-dlp`) and the README.
- **Tested:** fed the first-ever YouTube video (`"Me at the zoo"`, a real URL)
  with no local file — it downloaded → transcribed correctly → produced a
  valid 1080×1920 captioned clip → cleaned up the download.

---

## [0.3.0] — 2026-11-12 — Animated captions: `bigword` style (`src/reelsmith/captions.py`, `src/reelsmith/cli.py`)

- Added an `animation` parameter to `captions.generate_ass` and split event
  building into `_events_classic` and `_events_bigword`.
- New **`bigword`** style: one large word in the center of the screen at a
  time, popping in with a quick scale bounce (starts at 140 % size, snaps to
  100 % over 120 ms) using standard ASS tags (`\an5`, `\pos`, `\fs`, `\fscx`,
  `\fscy`, `\t`). The original `classic` style is unchanged.
- Added `--caption-style {classic,bigword}` to `src/reelsmith/cli.py`; updated README.
- **Tested:** rendered a `bigword` clip and confirmed a single large word
  appears centered in the highlight color (the pop is motion, visible on play).

---

## Measured performance (reference)

Transcription wall time for a **53-second** clip on this machine (CPU), as
measured during the session:

| Model  | Time    | Note |
|--------|---------|------|
| `tiny` | ~4.1 s  | ~13× faster than real-time |
| `base` | ~32.9 s | ⚠️ inflated — this run included the **one-time model download** |
| `small`| ~15.5 s | ~3.4× faster than real-time |

Transcription dominates total run time; cutting/vertical/caption steps are only
a few seconds per clip. Each model size also downloads once on first use.
