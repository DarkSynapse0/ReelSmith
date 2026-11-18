# ADR-004: Local and free only — no paid APIs

**Status:** Accepted
**Context:** Project-wide constraint, set at the start.

## Context
The project is a free, local alternative to commercial tools like Opus Clip. The
user lives in Nepal, wants Nepali speech to work well, and required that
**everything be free, open source, and run on their own computer — no paid
APIs**.

## Decision
Every component must be **free, open source, and run locally**. No cloud
services, no API keys, no per-use billing.

Concrete choices that follow from this:
| Need | Local/free tool chosen |
|------|------------------------|
| Speech-to-text | **faster-whisper** (runs on CPU) |
| Cut / crop / caption rendering | **FFmpeg** |
| Download from URL | **yt-dlp** |
| Moment-picking | **local heuristics** (`src/reelsmith/scoring.py`) |
| Captions font (Nepali) | **Noto Sans Devanagari** (already on system) |

## Rationale
- **Cost:** zero ongoing cost; no subscription.
- **Privacy:** footage never leaves the machine (unlike cloud tools that require
  uploading your video).
- **Offline:** after the one-time model/video download, it works without
  internet.
- **Control:** the user can edit fonts, colors, scoring, and accuracy freely.

## Consequences
- ✅ Meets the hard requirement; nothing to pay for or sign up to.
- ✅ Works for Nepali without region/language paywalls.
- ⚠️ Quality won't match big cloud AI out of the box — especially
  moment-picking and reframing. The roadmap closes these gaps with **local**
  upgrades (a local LLM via Ollama for scoring; OpenCV/MediaPipe for reframe),
  keeping the constraint intact.
- ⚠️ The only network touch is one-time downloads (Whisper model; video for URL
  inputs). That's acceptable and unavoidable.
- ℹ️ Future translation must also stay local (Whisper translate-to-English;
  Argos/NLLB for other targets) — see `ROADMAP.md`.
- ℹ️ As of v0.4.0 the "open source" part is formalized with an **MIT `LICENSE`**
  file — see `adr-005-src-layout.md`.
