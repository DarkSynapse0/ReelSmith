# ADR-001: Read the WAV ourselves instead of using faster-whisper's audio loader

**Status:** Accepted
**Context step:** Step 2 (Transcribe)

## Context
When we first ran transcription, faster-whisper crashed inside its own audio
decoding code:

```
TypeError: open() got an unexpected keyword argument 'metadata_errors'
```

faster-whisper's `decode_audio` calls `av.open(..., metadata_errors="ignore")`,
but the **PyAV 19** that got installed alongside it (the only version with a
Python 3.14 wheel) changed/removed that argument. So faster-whisper and PyAV
were simply incompatible in this environment.

## Options considered
1. **Pin an older `av` version.** Risky on Python 3.14 — older PyAV may have no
   `cp314` wheel, forcing a source build against system FFmpeg libraries
   (fragile, slow, beginner-hostile).
2. **Pin an older faster-whisper.** Might reintroduce other issues and fights
   the newest models/wheels.
3. **Bypass faster-whisper's audio loader.** We already extract a clean
   16 kHz mono WAV with FFmpeg. faster-whisper's `transcribe()` accepts a NumPy
   array directly, so we can read the WAV ourselves and skip `av` entirely.

## Decision
Go with option 3. `transcribe.load_wav_as_array()` reads the FFmpeg-produced
WAV with Python's built-in `wave` module, converts 16-bit samples to float32 in
the −1..1 range (`samples / 32768`), and passes the **array** to
`model.transcribe(audio, ...)`.

## Consequences
- ✅ Avoids the crash with **no new dependency** (NumPy already ships with
  faster-whisper).
- ✅ No version pinning to maintain; robust on bleeding-edge Python.
- ✅ Simple and easy for a beginner to read.
- ⚠️ We rely on the audio being the exact WAV we created (16 kHz mono 16-bit).
  That's fine because **we** create it in `extract_audio()`.
- ⚠️ If we ever feed Whisper audio from another source, we'd route it through
  the same WAV-extraction step first.
