# Step 14 — Mixed-language transcription (`--language mixed`)

## Goal
Handle videos that **switch between languages** (e.g. Hindi and English). A
single Whisper pass commits to **one script** for the whole audio: force Hindi
and the English words get spelled phonetically in Devanagari; force English and
the Hindi gets mangled into Latin. This step keeps **each part in its own
language** instead.

## What was built
- **`src/reelsmith/transcribe.py`** gained a mixed-language path built on a
  **VAD-split → per-utterance auto-detect → stitch** idea:
  - **`_speech_chunks(audio)`** — splits the audio into utterances using
    faster-whisper's voice-activity detector (`get_speech_timestamps`) with tuned
    `VadOptions`: `min_silence_duration_ms=300` (split on ~0.3 s pauses),
    `max_speech_duration_s=20` (cap chunk length), `speech_pad_ms=200`. This
    makes each chunk roughly **one utterance** — small enough that its language
    can be detected on its own.
  - **`transcribe_audio_multilang(audio_path, model_size)`** — for each chunk,
    slices the audio, transcribes it with **`language=None`** (so Whisper detects
    *that chunk's* language and writes it in the right script), **offsets** the
    word/segment timings back by the chunk's start, and collects everything.
    Each segment is tagged with its **`"language"`**; the transcript's top-level
    `"language"` is **`"mixed"`** with a `"languages"` list. The per-segment print
    respects `utils.QUIET`.
- **`transcribe_video(...)`** branches to this path when `language == "mixed"`.
- **CLI/menu:** `--language` help mentions `mixed`; the interactive menu's
  language list gained a **`mixed`** option.
- Captions need no change — the bundled **Noto Sans Devanagari** font also covers
  Latin letters, so Hindi and English segments both render.

## How it was tested
1. **Synthetic mixed clip.** Built an English → Hindi → English video with
   `espeak-ng` (including its Hindi voice), separated by ~0.7 s silences so the
   VAD would split it, then ran `--language mixed` (model `small`).
2. **Mechanism validated.** The VAD split the audio into **6 utterances**; each
   got its **own detected language**; the **English chunks transcribed
   perfectly**; and the timings were **offset/stitched** correctly
   (0:00 → 0:02 → 0:11 → 0:14). Segments carried **different** language tags,
   proving the per-utterance switching works.
3. **Full pipeline + regression.** A full run via
   `reelsmith … --language mixed` produced a valid **1080×1920** clip, and the
   3 unit tests still pass.

### Honest caveat about the test
The synthetic Hindi came from **espeak's robotic TTS**, and Whisper **could not
recognize it as Hindi** — it mis-detected those chunks as French/Hungarian and
produced gibberish. This is a limitation of the **synthetic test audio**, not the
code: espeak's formant-synthesis Hindi doesn't sound like the human speech
Whisper was trained on. On **real human Hindi** speech, Whisper reliably detects
`hi` and outputs Devanagari. So the **mechanism** is proven (on English), but
**real-Hindi detection could not be auto-verified here** — it should be confirmed
on an actual Hindi/English video.

## Result / what worked
For videos that alternate languages **between** sentences, each sentence is now
transcribed and captioned in its own language/script. ✅ (Verified mechanically;
real-Hindi quality to be confirmed on real footage.)

## Limitation / future
- **Within-sentence switching** (e.g. *"यह important point है"*) is still detected
  as **one** language per utterance — true word-level code-switching is a
  research-grade problem (see `ROADMAP.md`).
- **Slower** than a normal pass, because of the many small transcriptions.
- **Translation** (writing the speech in a *different* language) is separate and
  still on the roadmap.

Design rationale is in `docs/decisions/adr-008-mixed-language-vad.md`.
