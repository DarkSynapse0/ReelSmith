# Progress Dashboard

A one-glance view of what's done and what's planned. ✅ = built & tested,
⬜ = not started.

For detailed history see [CHANGELOG.md](CHANGELOG.md); for future plans see
[ROADMAP.md](ROADMAP.md).

---

## Completed features

| ✅ | Feature | Version | Details |
|----|---------|---------|---------|
| ✅ | Environment setup + venv + requirements | 0.1.0 | [step-01](docs/steps/step-01-setup.md) |
| ✅ | Transcription with word-level timestamps (JSON + SRT) | 0.1.0 | [step-02](docs/steps/step-02-transcribe.md) |
| ✅ | Language option (auto / `ne` / `en` / …) | 0.1.0 | [step-02](docs/steps/step-02-transcribe.md) |
| ✅ | Model-size option (`tiny`…`large-v3`) | 0.1.0 | [step-02](docs/steps/step-02-transcribe.md) |
| ✅ | Moment detection (20–60 s, sentence-aligned) | 0.1.0 | [step-03](docs/steps/step-03-find-moments.md) |
| ✅ | Heuristic scoring (swappable module) | 0.1.0 | [step-03](docs/steps/step-03-find-moments.md) |
| ✅ | Top-N non-overlapping selection | 0.1.0 | [step-03](docs/steps/step-03-find-moments.md) |
| ✅ | Clip cutting with safety buffer | 0.1.0 | [step-04](docs/steps/step-04-cut-clips.md) |
| ✅ | Vertical 9:16 — center crop | 0.1.0 | [step-05](docs/steps/step-05-vertical.md) |
| ✅ | Vertical 9:16 — blurred-background fit | 0.1.0 | [step-05](docs/steps/step-05-vertical.md) |
| ✅ | Word-by-word highlighted captions (ASS) | 0.1.0 | [step-06](docs/steps/step-06-captions.md) |
| ✅ | Nepali / Devanagari caption rendering | 0.1.0 | [step-06](docs/steps/step-06-captions.md) |
| ✅ | Configurable caption look (`CAPTION_STYLE`) | 0.1.0 | [step-06](docs/steps/step-06-captions.md) |
| ✅ | Single command `src/videoclipper/cli.py` | 0.1.0 | [step-07](docs/steps/step-07-main-command.md) |
| ✅ | Output folder + `summary.txt` / `summary.json` | 0.1.0 | [step-07](docs/steps/step-07-main-command.md) |
| ✅ | Clip from a URL (yt-dlp, ≤1080p) | 0.2.0 | [step-08](docs/steps/step-08-url-download.md) |
| ✅ | Animated caption style: `bigword` pop | 0.3.0 | [step-09](docs/steps/step-09-animated-captions.md) |
| ✅ | Standard `src/` package layout | 0.4.0 | [step-10](docs/steps/step-10-restructure.md) |
| ✅ | Pip-installable + `videoclipper` command / `python -m videoclipper` | 0.4.0 | [step-10](docs/steps/step-10-restructure.md) |
| ✅ | MIT `LICENSE` + `.gitignore` | 0.4.0 | [step-10](docs/steps/step-10-restructure.md) |
| ✅ | Unit test suite (`tests/test_basic.py`) | 0.4.0 | [step-10](docs/steps/step-10-restructure.md) |
| ✅ | Full product documentation (`docs/`, CHANGELOG, ROADMAP, …) | 0.4.0 | [docs/README](docs/README.md) |
| ✅ | Speaker-tracking reframe (`--vertical track`) — now **dynamic panning** | 0.5.0 → 1.3.0 | [step-11](docs/steps/step-11-speaker-tracking.md) · [step-16](docs/steps/step-16-dynamic-tracking.md) |
| ✅ | Bundled YuNet face model + OpenCV dependency | 0.5.0 | [step-11](docs/steps/step-11-speaker-tracking.md) |
| ✅ | Dynamic tracking: crop follows the speaker (sendcmd pan, smoothing, cut-snap) | 1.3.0 | [step-16](docs/steps/step-16-dynamic-tracking.md) |
| ✅ | Face diagnostic (`python -m videoclipper.reframe <video>`) | 1.3.0 | [step-16](docs/steps/step-16-dynamic-tracking.md) |
| ✅ | OpenCV detector warning suppressed | 1.3.0 | [step-16](docs/steps/step-16-dynamic-tracking.md) |
| ✅ | Interactive menu mode (no flags; run with no args or `-i`) | 0.6.0 | [step-12](docs/steps/step-12-interactive-cli.md) |
| ✅ | Captions on/off toggle (`--no-captions`) | 0.6.0 | [step-12](docs/steps/step-12-interactive-cli.md) |
| ✅ | Polished interactive TUI (rich + questionary: banner, arrow-key menus, panels) | 1.0.0 | [step-13](docs/steps/step-13-tui.md) |
| ✅ | Staged progress bars (download / transcribe / find / render) | 1.0.0 | [step-13](docs/steps/step-13-tui.md) |
| ✅ | Quiet mode (`utils.QUIET`) for clean progress output | 1.0.0 | [step-13](docs/steps/step-13-tui.md) |
| ✅ | Mixed-language transcription (`--language mixed`, between-sentence switching) | 1.1.0 | [step-14](docs/steps/step-14-mixed-language.md) |
| ✅ | Per-video output folders (`clips/<name>/`, no mixing) | 1.2.0 | [step-15](docs/steps/step-15-output-folders.md) |
| ✅ | Real transcription progress + spinner + ETA in the TUI | 1.2.1 | [CHANGELOG](CHANGELOG.md) |
| ✅ | Smooth, always-present ETA (custom extrapolating column) | 1.3.0 | [CHANGELOG](CHANGELOG.md) |
| ✅ | Cleaner TUI: ✔ collapsed stages, live transcript, per-clip sub-steps | 1.2.2 | [CHANGELOG](CHANGELOG.md) |
| ✅ | Caption-path crash fix (safe names + `cwd`) + 5-line scrolling transcript | 1.2.3 | [CHANGELOG](CHANGELOG.md) |
| ✅ | Browser-cookie downloads (`--cookies-from-browser`, incl. `zen`) + EJS solver | 1.3.1 | [CHANGELOG](CHANGELOG.md) |
| ✅ | Download progress bar (%) + fixed counting-down ETA | 1.3.2 | [CHANGELOG](CHANGELOG.md) |
| ✅ | Caching: reuse download + transcript (`--no-cache` to redo) | 1.4.0 | [CHANGELOG](CHANGELOG.md) |
| ✅ | Caption styles: `hormozi`, `karaoke`, `highlight-box` | 1.5.0 | [CHANGELOG](CHANGELOG.md) |
| ✅ | Per-style caption presets + auto font (Poppins/Bebas/Devanagari) + `mrbeast` | 1.6.0 | [CHANGELOG](CHANGELOG.md) |
| ✅ | `--model nepali` (Nepali fine-tuned) + HF/custom model support | 1.7.0 | [CHANGELOG](CHANGELOG.md) |
| ✅ | Mixed-mode primary language (`mixed:ne`) + tuning | 1.6.2–1.6.3 | [CHANGELOG](CHANGELOG.md) |
| ✅ | Smoother face tracking (dead-zone + heavier smoothing) | 1.6.0 | [CHANGELOG](CHANGELOG.md) |

## Planned / not yet built

| ⬜ | Feature | Status | Where |
|----|---------|--------|-------|
| ⬜ | Active-speaker selection among multiple faces | 🟡 Planned | [ROADMAP](ROADMAP.md) |
| ⬜ | Smarter moment-picking via local LLM (Ollama) | 🟡 Planned | [ROADMAP](ROADMAP.md) |
| ⬜ | More caption effects (keyword emphasis, typewriter, …) | 🟡 Planned | [ROADMAP](ROADMAP.md) |
| ⬜ | Object / product tracking (open-vocabulary) | 💡 Idea | [ROADMAP](ROADMAP.md) |
| ⬜ | Audio-first + section download (perf) | ⏸️ Deferred | [ROADMAP](ROADMAP.md) |
| ⬜ | Within-sentence (word-level) code-switching | 💡 Idea | [ROADMAP](ROADMAP.md) |
| ⬜ | Translation (→English easy; →Nepali needs add-on) | ⏸️ Deferred | [ROADMAP](ROADMAP.md) |
| ⬜ | "ClipAnything" visual search | 💡 Idea | [ROADMAP](ROADMAP.md) |
| ⬜ | Post-generation clip selection (preview & keep/delete) | 💡 Idea | [ROADMAP](ROADMAP.md) |

---

## Known limitations (today)
- Speaker tracking (`--vertical track`) now **pans dynamically** to follow a
  moving speaker (snapping at cuts). It still picks the **largest** face when
  several are present (not true active-speaker detection), and **screen-recording
  / b-roll-heavy** videos have no face to follow — use `crop`/`blur` for those
  (the `python -m videoclipper.reframe <video>` diagnostic tells you which).
- Moment-picking uses **simple heuristics** — good, not AI-smart yet.
- URL inputs download the **whole video** before processing.
- Each video is saved in its own folder under `clips/<video-name>/`, so
  different videos never mix (use `--output-dir` to override).
- **Mixed-language** mode (`--language mixed`) handles switching **between**
  sentences, but not **within** a single sentence (that utterance is detected as
  one language). It's also slower. No **translation** yet (captions stay in the
  spoken language(s)).

## Measured performance (53 s clip, this machine, CPU)
`tiny` ≈ 4 s · `small` ≈ 15.5 s · (`base` run was inflated by a one-time model
download). Transcription dominates; the FFmpeg steps are a few seconds per clip.
