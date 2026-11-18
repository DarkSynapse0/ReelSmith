"""
download.py
-----------
Download a video from a URL (YouTube, YouTube Shorts, Reels, and many
other sites) so the rest of the tool can clip it.

We use yt-dlp, a free and open-source downloader that runs locally. No
account, no API key. It is already installed in the virtual environment.

The main function, `download_video`, takes a URL and returns the path to
the downloaded video file on your computer.
"""

import glob
import os
import re
import subprocess
import sys

from . import utils


# Every run's results go under this top-level folder, one sub-folder per
# video, so different videos never mix together.
CLIPS_ROOT = "clips"


# YouTube now scrambles video URLs with a JavaScript "n-challenge". These
# arguments let yt-dlp fetch and run the official solver script, which needs a
# JavaScript runtime (deno or node) installed. Without this, YouTube returns
# "No video formats found".
_EJS_ARGS = ["--remote-components", "ejs:github"]


def _resolve_browser(browser):
    """
    Turn a browser name into what yt-dlp's --cookies-from-browser expects.

    Most names (firefox, chrome, brave, ...) pass straight through. The
    special name "zen" is handled for the Zen browser, which yt-dlp doesn't
    know by name: Zen is Firefox-based, so we find its profile folder (native
    or Flatpak install) and point yt-dlp's firefox reader at it directly.
    """
    if browser.lower() != "zen":
        return browser  # e.g. "firefox", "chrome", or an explicit "firefox:/path"

    roots = [
        os.path.expanduser("~/.zen"),
        os.path.expanduser("~/.var/app/app.zen_browser.zen/.zen"),  # Flatpak
    ]
    for root in roots:
        candidates = glob.glob(os.path.join(root, "*", "cookies.sqlite"))
        # Prefer the "Default" profile if there are several.
        candidates.sort(key=lambda p: ("default" not in p.lower(), p))
        if candidates:
            return f"firefox:{os.path.dirname(candidates[0])}"
    return "firefox"  # give up gracefully and let yt-dlp try the default


def _cookie_args():
    """
    If the user has told us which browser to borrow YouTube cookies from
    (via the VIDEOCLIPPER_COOKIES_BROWSER environment variable, set by the
    --cookies-from-browser option), return the yt-dlp arguments for it.

    This is what gets past YouTube's "Sign in to confirm you're not a bot"
    block, which can appear after downloading several videos.
    """
    browser = os.environ.get("VIDEOCLIPPER_COOKIES_BROWSER", "").strip()
    return ["--cookies-from-browser", _resolve_browser(browser)] if browser else []


def is_url(text):
    """
    Decide whether the thing the user typed is a web link or a local file.

    A simple, good-enough check: does it start with http:// or https://?
    """
    return text.strip().lower().startswith(("http://", "https://"))


def _sanitize_name(name):
    """
    Turn any title/filename into something safe to use as a folder name.

    We keep ONLY plain letters, numbers, dot, dash and underscore. Anything
    else (spaces, and tricky characters like ! ' " : & that can break file
    paths or FFmpeg filter strings) becomes an underscore. Then we tidy up
    and cap the length.

    Example: "Claude Code is FREE Now! Here's How" -> "Claude_Code_is_FREE_Now_Here_s_How"
    """
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())  # keep safe chars only
    name = re.sub(r"_+", "_", name)                        # collapse repeats
    name = name.strip("._-")
    return name[:60] or "video"


def url_video_name(url):
    """
    Work out a friendly, unique folder name for a video URL.

    We ask yt-dlp (without downloading) for the video's title and id, and
    combine them (the id guarantees uniqueness even if two videos share a
    title). If that lookup fails, we fall back to the id in the URL, or the
    last part of the URL.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "yt_dlp", "--no-playlist", "--skip-download",
             *_cookie_args(), *_EJS_ARGS,
             "--print", "%(title)s", "--print", "%(id)s", url],
            capture_output=True, text=True, timeout=120,
        )
        lines = [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
        if len(lines) >= 2:
            return _sanitize_name(f"{lines[0]}_{lines[-1]}")
        if lines:
            return _sanitize_name(lines[0])
    except Exception:
        pass  # fall through to the URL-based fallbacks below

    # Fallbacks that need no network: pull an id out of common URL shapes.
    match = re.search(r"(?:v=|/shorts/|youtu\.be/)([A-Za-z0-9_-]{6,})", url)
    if match:
        return _sanitize_name(match.group(1))
    return _sanitize_name(url.rstrip("/").split("/")[-1] or "video")


def default_output_dir(video_path):
    """
    Decide where a video's clips should be saved, giving each video its own
    folder under `clips/` so results never mix together:

        clips/<video-name>/

    For a URL we use the video's title + id; for a local file we use its
    file name (without the extension).
    """
    if is_url(video_path):
        name = url_video_name(video_path)
    else:
        name = _sanitize_name(os.path.splitext(os.path.basename(video_path))[0])
    return os.path.join(CLIPS_ROOT, name)


_PERCENT_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")


def _run_with_progress(args, progress_callback):
    """
    Run yt-dlp, stream its output, and report the download percentage.

    yt-dlp prints lines like "[download]  42.0% of 10.00MiB at ...". We watch
    for that percentage and pass it to `progress_callback` as a 0.0–1.0
    fraction. A video + audio download has two phases (each counts 0→100%),
    so the bar may reset once in the middle — that is normal. Returns
    (returncode, captured_output) for error reporting.
    """
    proc = subprocess.Popen(args, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    captured = []
    for line in proc.stdout:
        captured.append(line)
        match = _PERCENT_RE.search(line)
        if match and "%" in line and "download" in line.lower():
            try:
                progress_callback(min(float(match.group(1)) / 100.0, 1.0))
            except Exception:
                pass  # a display hiccup must never break the download
    proc.wait()
    return proc.returncode, "".join(captured[-20:])


def download_video(url, output_dir, quiet=False, progress_callback=None):
    """
    Download the video at `url` into `output_dir` and return its file path.

    We ask yt-dlp for the best MP4 video + audio and let it merge them
    (merging uses FFmpeg, which we already have). The downloaded file is
    always named 'source.<ext>' so it is easy to find afterwards.

    We run yt-dlp as `python -m yt_dlp` so it always uses the exact same
    environment as this program.

    `quiet`: when True we hide yt-dlp's chatty output (used by the fancy
    interactive interface, which shows its own clean progress bar instead).
    `progress_callback`: optional function called with a fraction 0.0–1.0 as
    the download advances (so the interface can show a real download bar).
    """
    os.makedirs(output_dir, exist_ok=True)
    output_template = os.path.join(output_dir, "source.%(ext)s")

    utils.info(f"Downloading video from: {url}")
    utils.info("(This uses yt-dlp and may take a moment depending on size.)")

    yt_args = [
        sys.executable, "-m", "yt_dlp",
        # Prefer an MP4 video + M4A audio, capped at 1080p height.
        # We only ever output 1080-wide vertical video, so downloading a
        # giant 4K source would just waste time and disk for no benefit.
        "-f", "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/"
              "best[ext=mp4][height<=1080]/best[height<=1080]/best",
        "--merge-output-format", "mp4",
        "-o", output_template,
        "--no-playlist",   # if the link is part of a playlist, take one video
        *_cookie_args(),   # use browser cookies if configured (anti-bot)
        *_EJS_ARGS,        # solve YouTube's JS n-challenge (needs deno/node)
    ]

    if progress_callback is not None:
        # Stream yt-dlp's output line by line and read the download percentage
        # out of it, so the interface can show a real progress bar.
        returncode, captured = _run_with_progress(yt_args + ["--newline", url],
                                                   progress_callback)
    else:
        if quiet:
            yt_args += ["-q", "--no-warnings"]
        yt_args.append(url)
        result = subprocess.run(yt_args, capture_output=quiet, text=True)
        returncode = result.returncode
        captured = result.stderr if quiet else ""

    if returncode != 0:
        # Surface yt-dlp's own error so the real cause is visible — it is
        # usually far more specific than a guess.
        detail = ""
        if captured:
            tail = "\n   ".join(captured.strip().splitlines()[-6:])
            detail = f"\n   yt-dlp reported:\n   {tail}\n"
        utils.fail(
            "Could not download that video.\n"
            f"{detail}"
            "   Common reasons & fixes:\n"
            "     - YouTube changed something -> update yt-dlp:\n"
            "         pip install -U yt-dlp\n"
            "     - 'Sign in to confirm you're not a bot' / too many downloads ->\n"
            "       pass your browser cookies, e.g. run yt-dlp once with\n"
            "         yt-dlp --cookies-from-browser firefox <url>\n"
            "     - the link is wrong, private, age-restricted, or removed\n"
            "     - no internet connection"
        )

    # Find the file we just downloaded (its extension may vary).
    matches = sorted(glob.glob(os.path.join(output_dir, "source.*")))
    # Ignore any leftover subtitle/description files, keep real video files.
    video_files = [m for m in matches
                   if m.rsplit(".", 1)[-1].lower()
                   in ("mp4", "mkv", "webm", "mov", "m4v")]
    if not video_files:
        utils.fail("The download finished but no video file was found.")

    path = video_files[0]
    utils.ok(f"Downloaded: {os.path.basename(path)}")
    return path
