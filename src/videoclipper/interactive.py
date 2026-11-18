"""
interactive.py
--------------
The polished, menu-driven interface. Instead of memorising command-line
flags, you run the command with no arguments:

    videoclipper

and answer a few questions with the arrow keys, then watch clean progress
bars as it works.

This uses two small, free, open-source libraries:
  - rich        -> the banner box, the job panel, and the progress bars
  - questionary -> the arrow-key option lists (● selected, ○ not)

If the program is not running in a real terminal (for example its input is
piped from a file or script), the fancy menu can't work, so we automatically
fall back to the simple typed prompts in `_plain_collect_settings`.
"""

import os
import shutil
import sys
from collections import deque

from rich import box
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import (BarColumn, Progress, ProgressColumn, SpinnerColumn,
                           TextColumn, TimeElapsedColumn)
from rich.table import Table
from rich.text import Text
import questionary
from questionary import Style


def _fmt_eta(seconds):
    """Format a number of seconds as M:SS or H:MM:SS."""
    seconds = int(max(0, seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


class _SmoothETA(ProgressColumn):
    """
    A steady, counting-DOWN time-remaining estimate.

    The trick: progress often moves in jumps (one transcript segment at a
    time), but the elapsed clock ticks every frame. If we recomputed the
    estimate from elapsed time on every frame, it would climb between jumps.

    Instead, each time the progress actually changes we work out the TOTAL
    expected time (elapsed / fraction, lightly smoothed) and remember it.
    Between changes we just show (total_expected − elapsed), which naturally
    ticks down as the clock runs, and only re-adjusts when real progress
    happens.
    """

    def __init__(self):
        super().__init__()
        self._state = {}  # task.id -> (last_completed, total_expected_seconds)

    def render(self, task):
        total = task.total
        completed = task.completed or 0
        elapsed = task.elapsed or 0.0
        if not total or completed <= 0 or elapsed <= 0:
            return Text("--:--", style="dim")
        fraction = completed / total
        if fraction <= 0:
            return Text("--:--", style="dim")

        last_completed, total_expected = self._state.get(task.id, (None, None))
        if last_completed != completed:
            # Progress changed: re-estimate total time, smoothed a little so
            # it doesn't lurch when the pace briefly varies.
            fresh = elapsed / fraction
            if total_expected is None:
                total_expected = fresh
            else:
                total_expected = 0.4 * fresh + 0.6 * total_expected
            self._state[task.id] = (completed, total_expected)

        remaining = max(0.0, total_expected - elapsed)
        return Text(_fmt_eta(remaining), style="cyan")

from . import __version__
from . import cache
from . import captions
from . import download
from . import moments
from . import transcribe
from . import utils
from . import video


console = Console()

# Colours/styling for the arrow-key menus so they match our banner.
_QSTYLE = Style([
    ("qmark", "fg:#00d7ff bold"),
    ("question", "bold"),
    ("pointer", "fg:#00d7ff bold"),
    ("highlighted", "fg:#00d7ff bold"),
    ("selected", "fg:#00ff87"),
    ("answer", "fg:#00ff87 bold"),
])


def _is_tty():
    """True only when we have a real interactive terminal to draw on."""
    return sys.stdin.isatty() and sys.stdout.isatty()


# -------------------------------------------------------------------------
# The pretty pieces
# -------------------------------------------------------------------------

def _banner():
    """Draw the rounded title box at the top."""
    title = (f"[bold white]🎬  VIDEOCLIPPER v{__version__}[/]  "
             f"[dim]•[/]  [cyan]AI-Powered Vertical Clip Generator[/]")
    console.print()
    console.print(Panel(title, box=box.ROUNDED, border_style="cyan",
                        padding=(0, 2)))
    console.print()


def _choice(value, description):
    """Build one labelled option for a questionary menu."""
    return questionary.Choice(title=f"{value:<9} — {description}", value=value)


def _pretty_collect_settings():
    """Ask every question with the fancy arrow-key menus."""
    _banner()

    video_path = questionary.text(
        "Paste video URL or local path:", style=_QSTYLE, qmark="?").ask()
    if not video_path:
        return None
    video_path = video_path.strip()

    language = questionary.select(
        "Speech language:",
        choices=[
            _choice("auto", "detect automatically"),
            _choice("ne", "Nepali"),
            _choice("en", "English"),
            _choice("hi", "Hindi"),
            _choice("mixed", "switches languages (e.g. Nepali + English)"),
        ], default="auto", style=_QSTYLE, qmark="?").ask()
    if language is None:
        return None

    # For mixed, ask the MAIN language so Nepali/Hindi speech isn't flipped to
    # English; only confident English utterances switch to English.
    if language == "mixed":
        primary = questionary.select(
            "Mixed with which MAIN language? (keeps it, swaps in English)",
            choices=[
                _choice("ne", "mostly Nepali + some English"),
                _choice("hi", "mostly Hindi + some English"),
                _choice("en", "mostly English + some other"),
                _choice("auto", "no main language (pure auto-detect)"),
            ], default="ne", style=_QSTYLE, qmark="?").ask()
        if primary is None:
            return None
        if primary != "auto":
            language = f"mixed:{primary}"

    # For Nepali, pre-select the Nepali fine-tuned model (much more accurate).
    model_default = "nepali" if language == "ne" else "small"
    model_size = questionary.select(
        "Whisper transcription model:",
        choices=[
            _choice("tiny", "fastest, lowest accuracy"),
            _choice("base", "fast"),
            _choice("small", "balanced (recommended)"),
            _choice("medium", "slow, accurate"),
            _choice("large-v3", "slowest, maximum accuracy"),
            _choice("nepali", "Nepali fine-tuned — best for Nepali ★"),
        ], default=model_default, style=_QSTYLE, qmark="?").ask()
    if model_size is None:
        return None

    num_clips = questionary.text(
        "Number of clips to generate:", default="5",
        validate=lambda t: t.isdigit() and int(t) > 0,
        style=_QSTYLE, qmark="?").ask()
    if num_clips is None:
        return None
    num_clips = int(num_clips)

    vertical_mode = questionary.select(
        "Vertical (9:16) framing mode:",
        choices=[
            _choice("crop", "zoom & center-crop"),
            _choice("blur", "fit frame + blurred background"),
            _choice("track", "active speaker face tracking ★"),
        ], default="crop", style=_QSTYLE, qmark="?").ask()
    if vertical_mode is None:
        return None

    captions_on = questionary.confirm(
        "Burned-in captions?", default=True, style=_QSTYLE, qmark="?").ask()
    if captions_on is None:
        return None
    caption_style = "classic"
    if captions_on:
        caption_style = questionary.select(
            "Caption style:",
            choices=[
                _choice("classic", "line of words, active word highlighted"),
                _choice("bigword", "one big word pops in at a time"),
                _choice("hormozi", "cyan bold CAPS, snappy pop"),
                _choice("mrbeast", "yellow/orange Bebas, extra bold"),
                _choice("karaoke", "full line, colour sweeps as spoken"),
                _choice("highlight-box", "active word on a coloured plate"),
            ], default="classic", style=_QSTYLE, qmark="?").ask()
        if caption_style is None:
            return None

    min_seconds, max_seconds = moments.MIN_SECONDS, moments.MAX_SECONDS
    if questionary.confirm("Change advanced settings (clip length)?",
                           default=False, style=_QSTYLE, qmark="?").ask():
        min_seconds = int(questionary.text(
            "Shortest clip length (seconds):", default=str(moments.MIN_SECONDS),
            validate=lambda t: t.isdigit() and int(t) > 0,
            style=_QSTYLE).ask() or moments.MIN_SECONDS)
        max_seconds = int(questionary.text(
            "Longest clip length (seconds):", default=str(moments.MAX_SECONDS),
            validate=lambda t: t.isdigit() and int(t) > 0,
            style=_QSTYLE).ask() or moments.MAX_SECONDS)

    settings = {
        "video_path": video_path,
        "language": language,
        "model_size": model_size,
        "num_clips": num_clips,
        "vertical_mode": vertical_mode,
        "captions_on": captions_on,
        "caption_style": caption_style,
        "min_seconds": min_seconds,
        "max_seconds": max_seconds,
        "buffer": video.DEFAULT_BUFFER,
    }

    # Wipe the question-and-answer prompts off the screen and redraw a clean
    # view: just the banner and the job-configuration summary.
    console.clear()
    _banner()
    _show_job_panel(settings)
    if not questionary.confirm("Ready to start processing?", default=True,
                               style=_QSTYLE, qmark="?").ask():
        console.print("[yellow]Cancelled. Nothing was done.[/]")
        return None
    return settings


def _equivalent_command(s):
    """
    Build the exact command-line that reproduces these menu choices — so the
    user can copy it and skip the menu next time.
    """
    parts = ["videoclipper", f'"{s["video_path"]}"',
             "--language", s["language"],
             "--model", s["model_size"],
             "--clips", str(s["num_clips"]),
             "--vertical", s["vertical_mode"]]
    if s["captions_on"]:
        parts += ["--caption-style", s["caption_style"]]
    else:
        parts += ["--no-captions"]
    if s["min_seconds"] != moments.MIN_SECONDS:
        parts += ["--min-seconds", str(s["min_seconds"])]
    if s["max_seconds"] != moments.MAX_SECONDS:
        parts += ["--max-seconds", str(s["max_seconds"])]
    return " ".join(parts)


def _show_job_panel(s):
    """Draw the '📋 JOB CONFIGURATION' box, including the --flag for each choice
    and the full equivalent command."""
    framing = {"crop": "9:16 Center-Crop", "blur": "9:16 Blurred-Fit",
               "track": "9:16 Active Face Tracking"}[s["vertical_mode"]]
    caption_text = (s["caption_style"] if s["captions_on"] else "disabled")
    caption_flag = (f"--caption-style {s['caption_style']}" if s["captions_on"]
                    else "--no-captions")

    # Three columns: label · value · the matching command-line flag.
    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("Setting", style="bold cyan", justify="right")
    table.add_column("Value")
    table.add_column("Option", style="dim")
    table.add_row("Source", s["video_path"], "(the video)")
    table.add_row("Language", s["language"], f"--language {s['language']}")
    table.add_row("Model", s["model_size"], f"--model {s['model_size']}")
    table.add_row("Clips", str(s["num_clips"]), f"--clips {s['num_clips']}")
    table.add_row("Length", f"{s['min_seconds']}–{s['max_seconds']}s",
                  f"--min-seconds {s['min_seconds']} --max-seconds {s['max_seconds']}")
    table.add_row("Framing", framing, f"--vertical {s['vertical_mode']}")
    table.add_row("Captions", caption_text, caption_flag)

    body = Group(
        table,
        Text(""),
        Text("Equivalent command (copy to skip the menu next time):",
             style="dim"),
        Text(_equivalent_command(s), style="bold green"),
    )
    console.print()
    console.print(Panel(body, title="📋 JOB CONFIGURATION", box=box.ROUNDED,
                        border_style="green", title_align="left"))
    console.print()


# -------------------------------------------------------------------------
# Running the pipeline with pretty progress bars
# -------------------------------------------------------------------------

def _stage_columns():
    """
    The look of each progress row: a spinner (always moving, so you can see
    it is alive), the label, a bar, the percentage, and elapsed time.
    """
    return [
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        BarColumn(bar_width=26, complete_style="cyan", finished_style="green"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TextColumn("[dim]•[/] eta"),
        _SmoothETA(),            # steady, always-present time estimate
    ]


def run_with_progress(settings):
    """
    Run the full pipeline, showing the clean 4-stage progress display
    (download → transcribe → find moments → render) instead of the usual
    log lines. Returns the list of chosen clips.
    """
    utils.check_ffmpeg()

    video_path = settings["video_path"]
    is_url = download.is_url(video_path)
    total_stages = 4 if is_url else 3
    step = [0]  # mutable counter so the nested helper can bump it

    def label(emoji, text):
        step[0] += 1
        return f"[{step[0]}/{total_stages}] {emoji}  {text}"

    # Decide where the results go: each video gets its own folder under
    # clips/ so different videos never mix together.
    if not is_url:
        utils.check_file_exists(video_path)
    output_dir = download.default_output_dir(video_path)
    work_dir = os.path.join(output_dir, "work")
    os.makedirs(work_dir, exist_ok=True)

    # Hide the normal chatter so only our clean display shows.
    utils.QUIET = True
    clips = []

    # The transcript streams by in a small fixed window of the last few lines
    # (deque with maxlen), so it never floods the screen.
    recent = deque(maxlen=5)
    progress = Progress(*_stage_columns(), console=console)

    def _render():
        # The live region = the recent-transcript window (if any) + the bars.
        if recent:
            body = Text("\n".join(f"   {ln}" for ln in recent),
                        style="dim italic")
            return Group(body, progress)
        return Group(progress)

    try:
        with Live(_render(), console=console, refresh_per_second=12) as live:

            def done(text):
                # Finished stages print one tidy line ABOVE the live region.
                live.console.print(f"  [green]✔[/] {text}")

            def refresh():
                live.update(_render())

            # ----- Stage: download (only for URLs; reuse cache if present) --
            if is_url:
                dl = label("⬇", "Downloading video...")
                cached_source = cache.find_source(output_dir)
                if cached_source:
                    video_path = cached_source
                    done(dl[:-3] + " — reused cached download")
                else:
                    task = progress.add_task(dl, total=100)
                    refresh()

                    def on_download(fraction, _task=task):
                        progress.update(_task, completed=min(fraction * 100, 100))
                        refresh()

                    video_path = download.download_video(
                        video_path, cache.cache_dir(output_dir), quiet=True,
                        progress_callback=on_download)
                    progress.update(task, completed=100)
                    progress.remove_task(task)
                    done(dl)

            # ----- Stage: transcribe (reuse cache, or real progress) --------
            tdesc = label("🎙",
                          f"Transcribing audio ({settings['model_size']})...")
            cached = cache.load_transcript(
                output_dir, settings["language"], settings["model_size"])
            if cached:
                transcript = cached
                done(tdesc[:-3] + " — reused cached transcript")
            else:
                # Starts at 0% showing "(loading model)" — the first run
                # downloads the model, which can take a while. Then the bar
                # advances and recognised lines scroll in the small window.
                task = progress.add_task(tdesc + "  [dim](loading model)[/]",
                                         total=100)
                refresh()
                state = {"started": False}

                def on_progress(fraction, text="", _task=task, _desc=tdesc):
                    if not state["started"]:
                        state["started"] = True
                        progress.update(_task, description=_desc)
                    progress.update(_task, completed=min(fraction * 100, 100))
                    if text:
                        recent.append(text if len(text) <= 72
                                      else text[:69] + "...")
                    refresh()

                transcript, _, _ = transcribe.transcribe_video(
                    video_path, language=settings["language"],
                    model_size=settings["model_size"], output_dir=output_dir,
                    progress_callback=on_progress)
                cache.save_transcript(output_dir, transcript,
                                      settings["language"],
                                      settings["model_size"])
                progress.remove_task(task)
                recent.clear()          # tidy away the transcript window
                refresh()
                done(tdesc)

            # ----- Stage: find best moments (quick) -----
            fdesc = label("🧠", f"Finding best moments ({settings['num_clips']})...")
            task = progress.add_task(fdesc, total=None)
            refresh()
            clips = moments.pick_best(
                transcript["segments"], num_clips=settings["num_clips"],
                min_seconds=settings["min_seconds"],
                max_seconds=settings["max_seconds"])
            progress.remove_task(task)
            if not clips:
                utils.QUIET = False
                utils.fail(
                    "No suitable moments were found. The video may be shorter "
                    f"than {settings['min_seconds']}s, or have little speech.")
            done(f"{fdesc[:-3]} — found {len(clips)}")

            # ----- Stage: render each clip. We advance the bar per SUB-STEP
            # (cut, framing, captions) so the percentage and ETA move smoothly
            # instead of jumping once per whole clip. -----
            all_words = [w for seg in transcript["segments"]
                         for w in (seg.get("words") or [])]
            source_duration = utils.ffprobe_duration(video_path)
            stage_n = total_stages   # render is always the last stage
            steps_per_clip = 3
            render = progress.add_task(
                f"[{stage_n}/{total_stages}] ✂  Rendering clips...",
                total=len(clips) * steps_per_clip)
            frame_name = {"crop": "center-crop", "blur": "blur-fit",
                          "track": "face-tracking"}[settings["vertical_mode"]]

            def step(desc):
                progress.update(render, description=desc)
                refresh()

            for i, clip in enumerate(clips, start=1):
                prefix = f"[{stage_n}/{total_stages}] ✂  clip {i}/{len(clips)}"
                raw = os.path.join(work_dir, f"raw_{i:02d}.mp4")
                vert = os.path.join(work_dir, f"vert_{i:02d}.mp4")
                ass = os.path.join(work_dir, f"cap_{i:02d}.ass")
                final = os.path.join(output_dir, f"clip_{i:02d}.mp4")

                step(f"{prefix}: cutting")
                real_start, real_end = video.cut_clip(
                    video_path, clip["start"], clip["end"], raw,
                    buffer=settings["buffer"], source_duration=source_duration)
                progress.advance(render); refresh()

                step(f"{prefix}: {frame_name}")
                video.make_vertical(raw, vert, mode=settings["vertical_mode"])
                progress.advance(render); refresh()

                if settings["captions_on"]:
                    step(f"{prefix}: captions")
                    captions.generate_ass(all_words, real_start, real_end, ass,
                                          animation=settings["caption_style"])
                    video.burn_captions(vert, ass, final)
                else:
                    shutil.move(vert, final)
                progress.advance(render); refresh()
                done(f"clip_{i:02d}.mp4 ready")

            progress.remove_task(render)
            done(f"Rendered {len(clips)} clip(s)")
    finally:
        utils.QUIET = False

    # Write the summary files (reuse the same helper the flag mode uses).
    from . import cli
    summary_txt = os.path.join(output_dir, "summary.txt")
    summary_json = os.path.join(output_dir, "summary.json")
    cli._write_summary(clips, summary_txt, summary_json,
                       os.path.basename(video_path))
    shutil.rmtree(work_dir, ignore_errors=True)

    _show_results(clips, output_dir)
    return clips


def _show_results(clips, output_dir):
    """Print a tidy results box listing the finished clips and scores."""
    table = Table(box=box.SIMPLE, show_edge=False)
    table.add_column("Clip", style="bold cyan")
    table.add_column("Time", style="white")
    table.add_column("Score", justify="right", style="green")
    for i, clip in enumerate(clips, start=1):
        start = utils.seconds_to_timestamp(clip["start"], ":")
        end = utils.seconds_to_timestamp(clip["end"], ":")
        table.add_row(f"clip_{i:02d}.mp4", f"{start} → {end}", str(clip["score"]))
    console.print()
    console.print(Panel(table, title="✅ DONE — your clips are ready",
                        subtitle=f"saved in: {output_dir}/", box=box.ROUNDED,
                        border_style="green", title_align="left"))


# -------------------------------------------------------------------------
# Plain fallback (used when there is no real terminal)
# -------------------------------------------------------------------------

def _plain_collect_settings():
    """Simple typed prompts, used when the fancy menu can't run."""
    def ask(prompt, default):
        a = input(f"{prompt} [{default}]: ").strip()
        return a or default

    print("\n=== Video Clipper (simple mode) ===")
    video_path = ""
    while not video_path:
        video_path = input("Video URL or file path: ").strip()
    language = ask("Language (auto/ne/en/hi/mixed)", "auto")
    model_default = "nepali" if language == "ne" else "small"
    settings = {
        "video_path": video_path,
        "language": language,
        "model_size": ask("Model (tiny/base/small/medium/large-v3/nepali)",
                          model_default),
        "num_clips": int(ask("Number of clips", "5")),
        "vertical_mode": ask("Vertical (crop/blur/track)", "crop"),
        "caption_style": "classic",
        "captions_on": ask("Captions? (y/n)", "y").lower().startswith("y"),
        "min_seconds": moments.MIN_SECONDS,
        "max_seconds": moments.MAX_SECONDS,
        "buffer": video.DEFAULT_BUFFER,
    }
    if settings["captions_on"]:
        settings["caption_style"] = ask("Caption style (classic/bigword)",
                                        "classic")
    return settings


# -------------------------------------------------------------------------
# Entry point used by cli.py
# -------------------------------------------------------------------------

def launch():
    """
    Run the interactive experience: fancy menu + progress bars in a real
    terminal, or simple prompts + normal logs when piped/non-interactive.
    """
    if _is_tty():
        settings = _pretty_collect_settings()
        if settings is None:
            return
        run_with_progress(settings)
    else:
        settings = _plain_collect_settings()
        if settings is None:
            return
        # Plain mode uses the normal (logging) pipeline.
        from . import cli
        cli.run(
            settings["video_path"], language=settings["language"],
            model_size=settings["model_size"], num_clips=settings["num_clips"],
            vertical_mode=settings["vertical_mode"],
            caption_style=settings["caption_style"],
            captions_on=settings["captions_on"],
            min_seconds=settings["min_seconds"],
            max_seconds=settings["max_seconds"])
