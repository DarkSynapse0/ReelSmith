"""
transcribe.py
-------------
Step 2 of the clipping tool: turn a video's speech into text.

What it does, in order:
  1. Extracts the audio track from a video using FFmpeg
     (16 kHz mono WAV, which is what Whisper expects).
  2. Transcribes that audio with faster-whisper, asking for
     word-level timestamps (we need to know when each word is spoken
     so later steps can highlight captions word-by-word).
  3. Saves two files:
       - a JSON file with every segment and every word + its timing
       - an SRT subtitle file (standard captions you can open anywhere)

You can run it on its own:
    python transcribe.py my_video.mp4 --language ne --model small

But normally it is called for you by clipper.py (Step 7).
"""

import argparse
import json
import os
import tempfile
import wave

import numpy as np
from faster_whisper import WhisperModel

from . import utils


# Friendly aliases for special models. faster-whisper's WhisperModel accepts a
# plain size ("small"), a Hugging Face model id, or a local path — so we can
# point an easy name at a community fine-tune. "nepali" is a Whisper large-v3
# fine-tuned for Nepali+English, which is far more accurate on Nepali than the
# stock models.
_MODEL_ALIASES = {
    "nepali": "DontHash/neptrans-v4-ct2",
}


def _resolve_model(name):
    """Turn a friendly model name into what faster-whisper should load."""
    return _MODEL_ALIASES.get(name, name)


# -------------------------------------------------------------------------
# 1. Extract the audio
# -------------------------------------------------------------------------

def extract_audio(video_path, audio_path):
    """
    Pull the audio out of the video and save it as a WAV file.

    Why these settings?
      -ac 1       : one channel (mono) — speech models don't need stereo
      -ar 16000   : 16,000 samples per second — Whisper's expected rate
      -vn         : drop the video, we only want sound
    """
    utils.info("Extracting audio from the video...")
    utils.run_ffmpeg(
        [
            "ffmpeg", "-y",            # -y = overwrite the output if it exists
            "-i", video_path,
            "-ac", "1",
            "-ar", "16000",
            "-vn",
            audio_path,
        ],
        description="extracting the audio track",
    )


def load_wav_as_array(wav_path):
    """
    Read our 16 kHz mono WAV file into a NumPy array of floats.

    Why do this ourselves instead of letting faster-whisper open the file?
    Some versions of the underlying 'av' library are not compatible with
    faster-whisper's built-in audio loader. By reading the simple WAV we
    created with FFmpeg (16-bit samples) and converting it to the float
    format Whisper wants, we avoid that problem completely.

    16-bit audio samples range from -32768 to 32767, so dividing by 32768
    scales them into the -1.0 .. 1.0 range that Whisper expects.
    """
    with wave.open(wav_path, "rb") as wav:
        frames = wav.readframes(wav.getnframes())
    samples = np.frombuffer(frames, dtype=np.int16)
    return samples.astype(np.float32) / 32768.0


# -------------------------------------------------------------------------
# 2. Transcribe with faster-whisper
# -------------------------------------------------------------------------

def transcribe_audio(audio_path, language, model_size, progress_callback=None):
    """
    Run speech-to-text and return a clean Python dictionary.

    `progress_callback`: optional function called with a fraction 0.0–1.0 as
                   transcription advances, so a caller (like the fancy
                   interface) can show a real progress bar.

    `language`   : None for auto-detect, or a code like "ne" (Nepali),
                   "en" (English), "hi" (Hindi), etc.
    `model_size` : "tiny", "base", "small", "medium", "large-v3".
                   Bigger = more accurate but slower and more memory.
                   "small" is a good starting point for a normal laptop.
    """
    utils.info(f"Loading the '{model_size}' Whisper model "
               "(the first run downloads it, which can take a while)...")

    # compute_type="int8" keeps memory low and runs well on a plain CPU.
    model = WhisperModel(_resolve_model(model_size), device="cpu", compute_type="int8")

    utils.info("Transcribing... this is the slow part, please be patient.")

    # Load the audio into a NumPy array ourselves (see load_wav_as_array
    # above for why) and pass that to Whisper.
    audio = load_wav_as_array(audio_path)
    # Total length in seconds, used to turn "seconds done" into a percentage.
    total_duration = max(len(audio) / 16000.0, 0.001)

    # word_timestamps=True is the key setting: it gives us the start and
    # end time of every single word, which the caption step depends on.
    segments, detected = model.transcribe(
        audio,
        language=language,          # None => auto-detect
        word_timestamps=True,
        vad_filter=True,            # skip long silences for cleaner timing
    )

    # faster-whisper returns a lazy generator; looping over it does the work.
    result_segments = []
    full_text_parts = []
    for seg in segments:
        # Report progress: how far through the audio we are, 0.0–1.0, plus
        # the latest line of text (so a caller can show it streaming by).
        if progress_callback:
            progress_callback(float(min(seg.end / total_duration, 1.0)),
                              seg.text.strip())
        words = []
        if seg.words:  # can be None if a segment had no clear words
            for w in seg.words:
                words.append({
                    "word": w.word,
                    # float() converts any NumPy number into a plain Python
                    # float so it prints and saves cleanly everywhere.
                    "start": round(float(w.start), 3),
                    "end": round(float(w.end), 3),
                })
        result_segments.append({
            "id": seg.id,
            "start": round(float(seg.start), 3),
            "end": round(float(seg.end), 3),
            "text": seg.text.strip(),
            "words": words,
        })
        full_text_parts.append(seg.text.strip())
        # Print as we go so you can see it working (hidden in quiet mode,
        # e.g. when the fancy interface is showing its own progress bar).
        if not utils.QUIET:
            print(f"    [{utils.seconds_to_timestamp(seg.start)}] {seg.text.strip()}")

    language_used = language or detected.language
    utils.ok(f"Transcription done. Language: {language_used}, "
             f"{len(result_segments)} segments.")

    return {
        "language": language_used,
        "text": " ".join(full_text_parts).strip(),
        "segments": result_segments,
    }


# -------------------------------------------------------------------------
# 2b. Mixed-language ("mixed") transcription
# -------------------------------------------------------------------------
#
# For videos that switch between languages (e.g. Hindi and English), a single
# Whisper pass writes everything in ONE script. To keep each part in its own
# language, we:
#   1. Split the audio into short utterances using voice-activity detection.
#   2. Transcribe each utterance on its own with auto-detect, so Whisper
#      picks (and writes) the language of THAT utterance.
#   3. Stitch the pieces back together with corrected timings.
#
# This handles switching BETWEEN sentences/phrases well. It cannot perfectly
# handle switching WITHIN a single phrase (that whole utterance is detected
# as one language). It is also slower, because of the many small passes.

def _speech_chunks(audio, sampling_rate=16000):
    """
    Return a list of (start_sample, end_sample) speech regions.

    We tune the voice-activity detector to split on fairly short pauses and
    to cap how long one chunk can be, so each chunk is roughly one utterance
    — small enough that its language can be detected on its own.
    """
    from faster_whisper.vad import VadOptions, get_speech_timestamps
    options = VadOptions(
        min_silence_duration_ms=200,   # split on short pauses (finer utterances
                                       # → more chance to catch an English word)
        max_speech_duration_s=15,      # never let one chunk exceed 15s
        speech_pad_ms=150,             # keep a little audio around each chunk
    )
    stamps = get_speech_timestamps(audio, options, sampling_rate=sampling_rate)
    return [(s["start"], s["end"]) for s in stamps]


def transcribe_audio_multilang(audio_path, model_size, primary=None,
                               progress_callback=None):
    """
    Transcribe utterance-by-utterance, detecting the language of each one.

    `primary`: the main language of the video (e.g. "ne"). When set, each
               utterance is transcribed in THAT language unless English is
               detected with high confidence. This stops a mostly-Nepali
               video from being flipped to English, while still catching the
               English words/phrases. When None, every utterance is pure
               auto-detect (can mis-detect short clips).

    Returns the same transcript shape as transcribe_audio, but each segment
    also carries a "language" field, and the top-level "language" is "mixed".

    `progress_callback`: optional function called with a fraction 0.0–1.0 as
                   each utterance is finished.
    """
    utils.info(f"Loading the '{model_size}' Whisper model...")
    model = WhisperModel(_resolve_model(model_size), device="cpu", compute_type="int8")

    audio = load_wav_as_array(audio_path)
    sampling_rate = 16000
    chunks = _speech_chunks(audio, sampling_rate)
    if not chunks:
        # No speech detected; fall back to a normal single-language pass.
        return transcribe_audio(audio_path, primary, model_size)

    mode = f"primary '{primary}' + English" if primary else "auto-detect"
    utils.info(f"Transcribing {len(chunks)} utterance(s) ({mode}); "
               "mixed mode is slower...")
    # How sure we must be that a chunk is English before switching to it.
    # Lower = catches more English words, but risks flipping a Nepali chunk.
    english_threshold = 0.35

    result_segments = []
    full_text_parts = []
    languages_seen = set()

    for chunk_index, (start_sample, end_sample) in enumerate(chunks):
        clip_audio = audio[start_sample:end_sample]
        offset = start_sample / sampling_rate  # seconds to add back on
        chunk_texts = []  # this utterance's text, for the progress callback

        # Decide which language to transcribe this utterance in.
        if primary:
            # Keep the primary language unless this chunk is clearly English.
            detected, prob, _ = model.detect_language(clip_audio)
            if detected == "en" and prob >= english_threshold:
                use_language = "en"
            else:
                use_language = primary
        else:
            use_language = None   # pure auto-detect for this utterance

        segments, info = model.transcribe(
            clip_audio, language=use_language, word_timestamps=True,
            vad_filter=False,
        )
        chunk_language = info.language
        languages_seen.add(chunk_language)

        for seg in segments:
            words = []
            if seg.words:
                for w in seg.words:
                    words.append({
                        "word": w.word,
                        "start": round(float(w.start) + offset, 3),
                        "end": round(float(w.end) + offset, 3),
                    })
            text = seg.text.strip()
            result_segments.append({
                "id": len(result_segments),
                "start": round(float(seg.start) + offset, 3),
                "end": round(float(seg.end) + offset, 3),
                "text": text,
                "language": chunk_language,   # which language this piece is in
                "words": words,
            })
            full_text_parts.append(text)
            chunk_texts.append(text)
            if not utils.QUIET:
                stamp = utils.seconds_to_timestamp(seg.start + offset)
                print(f"    [{stamp}] ({chunk_language}) {text}")

        # Report progress once per finished utterance, with its text and the
        # detected language (so a caller can show it streaming by).
        if progress_callback:
            label = f"({chunk_language}) {' '.join(chunk_texts)}".strip()
            progress_callback((chunk_index + 1) / len(chunks), label)

    # Utterances were processed in order, but sort by time just to be safe.
    result_segments.sort(key=lambda s: s["start"])
    utils.ok(f"Transcription done (mixed). Languages found: "
             f"{', '.join(sorted(languages_seen))}; "
             f"{len(result_segments)} segments.")

    return {
        "language": "mixed",
        "languages": sorted(languages_seen),
        "text": " ".join(full_text_parts).strip(),
        "segments": result_segments,
    }


# -------------------------------------------------------------------------
# 3. Save the results
# -------------------------------------------------------------------------

def save_json(transcript, json_path):
    """Save the full transcript (with word timings) as readable JSON."""
    with open(json_path, "w", encoding="utf-8") as f:
        # ensure_ascii=False keeps Nepali/Devanagari characters intact
        # instead of turning them into \uXXXX escape codes.
        json.dump(transcript, f, ensure_ascii=False, indent=2)
    utils.ok(f"Saved transcript JSON: {json_path}")


def save_srt(transcript, srt_path):
    """
    Save a standard .srt subtitle file (one entry per segment).

    SRT format looks like:
        1
        00:00:00,000 --> 00:00:03,500
        Hello and welcome
        <blank line>
    """
    lines = []
    for index, seg in enumerate(transcript["segments"], start=1):
        start = utils.seconds_to_timestamp(seg["start"], separator=",")
        end = utils.seconds_to_timestamp(seg["end"], separator=",")
        lines.append(str(index))
        lines.append(f"{start} --> {end}")
        lines.append(seg["text"])
        lines.append("")  # blank line separates entries
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    utils.ok(f"Saved subtitles: {srt_path}")


# -------------------------------------------------------------------------
# The main routine that ties the three steps together
# -------------------------------------------------------------------------

def transcribe_video(video_path, language="auto", model_size="small",
                     output_dir=".", progress_callback=None):
    """
    High-level function used by clipper.py.

    Returns the transcript dictionary and also writes the JSON + SRT files.

    `progress_callback`: optional function called with a fraction 0.0–1.0 as
    transcription advances (used by the fancy interface's progress bar).
    """
    utils.check_ffmpeg()
    utils.check_file_exists(video_path)

    # "auto" is friendlier to type than "None" on the command line,
    # so we translate it here into what faster-whisper actually wants.
    # "mixed" is special: it means "the speech switches languages". It may
    # carry a primary language after a colon, e.g. "mixed:ne" = mostly Nepali.
    lang = None if language in (None, "auto") else language
    primary = None
    is_mixed = language is not None and language.startswith("mixed")
    if is_mixed and ":" in language:
        primary = language.split(":", 1)[1] or None

    os.makedirs(output_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(video_path))[0]
    json_path = os.path.join(output_dir, f"{base}.transcript.json")
    srt_path = os.path.join(output_dir, f"{base}.srt")

    # Extract audio into a temporary WAV file that we clean up afterwards.
    tmp_dir = tempfile.mkdtemp(prefix="clipper_")
    audio_path = os.path.join(tmp_dir, "audio.wav")
    try:
        extract_audio(video_path, audio_path)
        if is_mixed:
            transcript = transcribe_audio_multilang(
                audio_path, model_size, primary=primary,
                progress_callback=progress_callback)
        else:
            transcript = transcribe_audio(
                audio_path, lang, model_size,
                progress_callback=progress_callback)
    finally:
        # Best-effort cleanup of the temp audio.
        if os.path.isfile(audio_path):
            os.remove(audio_path)
        if os.path.isdir(tmp_dir):
            os.rmdir(tmp_dir)

    save_json(transcript, json_path)
    save_srt(transcript, srt_path)
    return transcript, json_path, srt_path


# -------------------------------------------------------------------------
# Command-line interface (so you can run this file directly)
# -------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Transcribe a video to word-level JSON and an SRT file."
    )
    parser.add_argument("video", help="path to the video file")
    parser.add_argument(
        "--language", default="auto",
        help="language code (default: auto-detect). "
             "Examples: ne (Nepali), en (English), hi (Hindi).",
    )
    parser.add_argument(
        "--model", default="small", dest="model_size",
        help="Whisper model size: tiny, base, small (default), medium, large-v3.",
    )
    parser.add_argument(
        "--output-dir", default=".",
        help="where to save the JSON and SRT (default: current folder).",
    )
    args = parser.parse_args()

    transcribe_video(
        args.video,
        language=args.language,
        model_size=args.model_size,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
