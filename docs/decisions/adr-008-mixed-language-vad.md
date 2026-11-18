# ADR-008: Mixed-language transcription via VAD split + per-utterance auto-detect

**Status:** Accepted (v1.1.0)
**Context:** Users have videos that switch between languages (e.g. Hindi and
English). A single Whisper pass writes the whole audio in one script, mangling
the other language.

## Context
Whisper (and faster-whisper) detect **one** language for a transcription run —
either what you pass via `--language`, or a single auto-detection from the start
of the audio. For a code-switching ("Hinglish") video this means:
- `--language hi` → everything in Devanagari, including English words spelled
  phonetically.
- `--language en` → Hindi mangled into Latin letters.

There is no built-in setting that keeps each part in its own script. We wanted a
**free, local** way to at least handle switching **between** sentences well.

## Decision
Add a `--language mixed` mode that **splits the audio into utterances and
detects/transcribes each one separately**, then stitches the results:
1. **VAD split** — `faster_whisper.vad.get_speech_timestamps` with tuned
   `VadOptions` (`min_silence_duration_ms=300`, `max_speech_duration_s=20`,
   `speech_pad_ms=200`) to cut the audio into roughly one-utterance chunks.
2. **Per-utterance transcription** — call `model.transcribe(chunk,
   language=None, …)` on each chunk, so Whisper detects and writes **that
   utterance's** language.
3. **Stitch** — offset each chunk's word/segment timings by the chunk start and
   concatenate in time order; tag each segment with its detected `language`.

## Rationale
- **Uses only the stable, public API** (`get_speech_timestamps` + `transcribe`),
  no private internals or extra models — stays free and local.
- **Granularity we can control.** Tuning the VAD to split on short pauses and cap
  chunk length gives roughly per-sentence units, which is the level at which
  per-language detection is reliable.
- **Simple and robust.** Each chunk is an independent, ordinary transcription;
  the only bookkeeping is adding the time offset back. Easy to reason about and
  test.
- **Captions already work** for both scripts, since the bundled Noto Sans
  Devanagari font also covers Latin — no caption changes were needed.

## Consequences
- ✅ Between-sentence code-switching is handled: Hindi sentences in Devanagari,
  English sentences in Latin, with correct timings.
- ⚠️ **Within-sentence** switching is **not** handled — an utterance that mixes
  languages is detected as one language. True word-level code-switching is a
  research-grade problem (tracked in `ROADMAP.md`).
- ⚠️ **Slower** than a single pass (many small transcriptions).
- ⚠️ Detection quality depends on the audio. In testing, the **mechanism** was
  validated on English, but a **synthetic espeak Hindi** test clip was
  mis-detected (robotic TTS doesn't resemble the human speech Whisper learned);
  real-Hindi behaviour must be confirmed on real footage.

## Alternatives considered
- **Single auto pass** — simplest, but commits to one language for the whole
  video; the exact problem we're solving.
- **Dual-pass merge** (one `hi` pass + one `en` pass, reconciled per word by
  confidence/timestamp) — could in principle handle within-sentence mixing, but
  aligning two passes at word level is fragile and error-prone. Not worth it for
  the first version; noted as a possible future approach.
- **Dedicated code-switching ASR model** — the "proper" fix for word-level
  mixing, but heavier and outside the current free/local, lightweight stack.
- **Translation** (collapse everything to one language) — a different goal
  (changes the words), still on the roadmap as a separate `--translate` feature.
