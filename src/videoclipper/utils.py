"""
utils.py
--------
Small helper functions shared by all the other scripts.

Keeping these in one place means the rest of the code stays short and
readable, and every script gives the same friendly error messages.
"""

import os
import shutil
import subprocess
import sys


# ----- Friendly messages -------------------------------------------------

def fail(message):
    """
    Print an error in plain language and stop the program.

    We use this instead of letting Python crash with a confusing
    traceback, which is hard for a beginner to read.
    """
    print(f"\n❌ {message}\n")
    sys.exit(1)


# When True, the normal progress/success chatter is hidden. The fancy
# interactive interface turns this on so its clean progress bars are not
# buried under log lines. Errors (fail) are always shown.
QUIET = False


def info(message):
    """Print a normal progress message (unless QUIET is on)."""
    if not QUIET:
        print(f"• {message}")


def ok(message):
    """Print a success message (unless QUIET is on)."""
    if not QUIET:
        print(f"✅ {message}")


# ----- Environment checks ------------------------------------------------

def check_ffmpeg():
    """
    Make sure the `ffmpeg` and `ffprobe` commands are available.

    `shutil.which` looks for a program on your system PATH, the same way
    your terminal does. If it is missing we explain how to install it.
    """
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            fail(
                f"'{tool}' was not found on your system.\n"
                "   FFmpeg is required for extracting audio and making clips.\n"
                "   Install it with one of these, depending on your OS:\n"
                "     Arch Linux : sudo pacman -S ffmpeg\n"
                "     Ubuntu/Deb : sudo apt install ffmpeg\n"
                "     macOS      : brew install ffmpeg\n"
                "     Windows    : winget install Gyan.FFmpeg"
            )


def check_file_exists(path):
    """Stop with a friendly message if an input file is missing."""
    if not os.path.isfile(path):
        fail(
            f"The file '{path}' does not exist.\n"
            "   Please check the path and the spelling of the file name."
        )


# ----- Running FFmpeg ----------------------------------------------------

def run_ffmpeg(args, description="running FFmpeg", cwd=None):
    """
    Run an FFmpeg command.

    `args` is a list like ["ffmpeg", "-i", "in.mp4", ...].
    `cwd` optionally runs FFmpeg from a given folder (used so subtitle
    filter paths can be a safe bare filename regardless of the folder name).
    We hide FFmpeg's very chatty output unless something goes wrong,
    in which case we show it so the problem can be understood.
    """
    result = subprocess.run(args, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        # Show the last part of FFmpeg's output, which usually holds the error.
        tail = result.stderr.strip().splitlines()[-15:]
        fail(
            f"FFmpeg failed while {description}.\n"
            "   Here is what FFmpeg reported:\n\n   "
            + "\n   ".join(tail)
        )
    return result


def ffprobe_duration(path):
    """
    Return the length of a media file in seconds (as a float).

    Uses `ffprobe`, which ships with FFmpeg and reads media metadata.
    """
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        fail(f"Could not read the duration of '{path}'. Is it a valid video?")


# ----- Time formatting ---------------------------------------------------

def seconds_to_timestamp(seconds, separator=","):
    """
    Turn a number of seconds into a subtitle timestamp.

    Example: 75.5  ->  "00:01:15,500"
    SRT files use a comma before milliseconds; ASS files use a dot,
    so the separator is adjustable.
    """
    if seconds < 0:
        seconds = 0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    whole_seconds = int(seconds % 60)
    milliseconds = int(round((seconds - int(seconds)) * 1000))
    # Rounding can push milliseconds to 1000; carry it over cleanly.
    if milliseconds == 1000:
        milliseconds = 0
        whole_seconds += 1
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}{separator}{milliseconds:03d}"
