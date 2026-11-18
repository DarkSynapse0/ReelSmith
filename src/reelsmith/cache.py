"""
cache.py
--------
Remember the expensive results for each video so re-running it is fast.

The two slow steps are downloading the video and transcribing it (which can
take many minutes). Both results are saved inside the video's own folder, in
a `cache/` sub-folder:

    clips/<video-name>/cache/
        source.<ext>       the downloaded video
        transcript.json    the transcription
        meta.json          which language + model the transcript was made with

On a re-run we reuse the download if it is there, and reuse the transcript if
it was made with the SAME language and model. Pass --no-cache to ignore all of
this and start fresh.
"""

import glob
import json
import os


_VIDEO_EXTS = ("mp4", "mkv", "webm", "mov", "m4v")


def cache_dir(output_dir):
    """The cache folder for a given video's output folder."""
    return os.path.join(output_dir, "cache")


def source_template(output_dir):
    """Where a downloaded video should be saved so it can be reused later."""
    d = cache_dir(output_dir)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "source.%(ext)s")


def find_source(output_dir):
    """Return the path to a previously-downloaded video, or None."""
    matches = glob.glob(os.path.join(cache_dir(output_dir), "source.*"))
    videos = [m for m in matches
              if m.rsplit(".", 1)[-1].lower() in _VIDEO_EXTS]
    return videos[0] if videos else None


def _meta_path(output_dir):
    return os.path.join(cache_dir(output_dir), "meta.json")


def _transcript_path(output_dir):
    return os.path.join(cache_dir(output_dir), "transcript.json")


def load_transcript(output_dir, language, model):
    """
    Return a cached transcript ONLY if it was made with the same language and
    model; otherwise None (so we don't reuse the wrong transcription).
    """
    meta_file = _meta_path(output_dir)
    transcript_file = _transcript_path(output_dir)
    if not (os.path.isfile(meta_file) and os.path.isfile(transcript_file)):
        return None
    try:
        with open(meta_file, encoding="utf-8") as f:
            meta = json.load(f)
        if meta.get("language") != language or meta.get("model") != model:
            return None
        with open(transcript_file, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None  # a broken cache file should never crash the run


def save_transcript(output_dir, transcript, language, model):
    """Store a transcript plus the settings it was made with."""
    os.makedirs(cache_dir(output_dir), exist_ok=True)
    with open(_transcript_path(output_dir), "w", encoding="utf-8") as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)
    with open(_meta_path(output_dir), "w", encoding="utf-8") as f:
        json.dump({"language": language, "model": model}, f, indent=2)
