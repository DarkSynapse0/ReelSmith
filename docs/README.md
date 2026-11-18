# Documentation Index

All the documentation for **OpenSourceClipping** in one place. Start wherever
fits your need:

## Start here
- [../README.md](../README.md) — what the tool is, setup, and usage examples.
- [../ARCHITECTURE.md](../ARCHITECTURE.md) — the big picture: data flow and how
  the modules fit together.
- [../PROGRESS.md](../PROGRESS.md) — one-glance dashboard of what's done vs.
  planned.

## Project status & history
- [../CHANGELOG.md](../CHANGELOG.md) — everything built so far, in order, with
  what was tested.
- [../ROADMAP.md](../ROADMAP.md) — planned, deferred, and idea-stage features.

## Contributing
- [../CONTRIBUTING.md](../CONTRIBUTING.md) — set up, run, add a caption style,
  swap the scoring module, coding style.

## Build log — one page per step
| Step | Doc |
|------|-----|
| 1. Setup | [steps/step-01-setup.md](steps/step-01-setup.md) |
| 2. Transcribe | [steps/step-02-transcribe.md](steps/step-02-transcribe.md) |
| 3. Find best moments | [steps/step-03-find-moments.md](steps/step-03-find-moments.md) |
| 4. Cut clips | [steps/step-04-cut-clips.md](steps/step-04-cut-clips.md) |
| 5. Vertical 9:16 | [steps/step-05-vertical.md](steps/step-05-vertical.md) |
| 6. Captions | [steps/step-06-captions.md](steps/step-06-captions.md) |
| 7. One command | [steps/step-07-main-command.md](steps/step-07-main-command.md) |
| 8. URL download | [steps/step-08-url-download.md](steps/step-08-url-download.md) |
| 9. Animated captions | [steps/step-09-animated-captions.md](steps/step-09-animated-captions.md) |
| 10. Restructure (`src/` package) | [steps/step-10-restructure.md](steps/step-10-restructure.md) |
| 11. Speaker-tracking reframe | [steps/step-11-speaker-tracking.md](steps/step-11-speaker-tracking.md) |
| 12. Interactive menu mode | [steps/step-12-interactive-cli.md](steps/step-12-interactive-cli.md) |
| 13. Polished interactive TUI | [steps/step-13-tui.md](steps/step-13-tui.md) |
| 14. Mixed-language transcription | [steps/step-14-mixed-language.md](steps/step-14-mixed-language.md) |
| 15. Per-video output folders | [steps/step-15-output-folders.md](steps/step-15-output-folders.md) |
| 16. Dynamic speaker tracking (+ diagnostic, smooth ETA) | [steps/step-16-dynamic-tracking.md](steps/step-16-dynamic-tracking.md) |
| 17. Caching downloads & transcripts | [steps/step-17-caching.md](steps/step-17-caching.md) |

## Decision records (ADRs)
Why we made the notable technical choices:
- [decisions/adr-001-read-wav-ourselves.md](decisions/adr-001-read-wav-ourselves.md)
  — bypass faster-whisper's audio loader (PyAV clash).
- [decisions/adr-002-center-crop-vs-tracking.md](decisions/adr-002-center-crop-vs-tracking.md)
  — center crop now, speaker-tracking later.
- [decisions/adr-003-ass-for-captions.md](decisions/adr-003-ass-for-captions.md)
  — why ASS subtitles for captions.
- [decisions/adr-004-local-free-only.md](decisions/adr-004-local-free-only.md)
  — the local & free, no-paid-API constraint.
- [decisions/adr-005-src-layout.md](decisions/adr-005-src-layout.md)
  — adopt the standard `src/` package layout and pip-installable packaging.
- [decisions/adr-006-yunet-face-detection.md](decisions/adr-006-yunet-face-detection.md)
  — use OpenCV YuNet (bundled) for speaker-tracking face detection.
- [decisions/adr-007-rich-questionary-tui.md](decisions/adr-007-rich-questionary-tui.md)
  — adopt rich + questionary for the polished interactive terminal UI.
- [decisions/adr-008-mixed-language-vad.md](decisions/adr-008-mixed-language-vad.md)
  — mixed-language transcription via VAD split + per-utterance auto-detect.
- [decisions/adr-009-dynamic-tracking.md](decisions/adr-009-dynamic-tracking.md)
  — dynamic speaker tracking via an FFmpeg `sendcmd` crop path.
