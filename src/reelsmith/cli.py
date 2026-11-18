"""
clipper.py
----------
Step 7: the one command that does everything.

Run it like this:

    python clipper.py my_video.mp4 --language ne --clips 5

What happens, start to finish:
    1. Transcribe the video           (transcribe.py  -> JSON + SRT)
    2. Find the best moments          (moments.py + scoring.py)
    3. For each chosen moment:
         a. cut it out                (video.cut_clip)
         b. make it vertical 9:16     (video.make_vertical)
         c. build word captions       (captions.generate_ass)
         d. burn the captions in      (video.burn_captions)
    4. Save the finished clips in an output folder
    5. Write a summary file listing each clip's start, end and score.

This file mostly just connects the other modules together, so it stays
short and easy to follow.
"""

import argparse
import json
import os
import shutil

from . import cache
from . import captions
from . import download
from . import moments
from . import transcribe
from . import utils
from . import video


def _flatten_words(transcript):
    """Collect every word (with absolute timings) into one flat list."""
    words = []
    for seg in transcript["segments"]:
        words.extend(seg.get("words") or [])
    return words


def _write_summary(clips, summary_txt_path, summary_json_path, video_name):
    """
    Write two summary files:
      - a human-friendly .txt you can read in any editor
      - a .json version in case you want to process it with another program
    """
    # Plain-text summary
    lines = [
        f"Clip summary for: {video_name}",
        f"Total clips: {len(clips)}",
        "=" * 50,
        "",
    ]
    for i, clip in enumerate(clips, start=1):
        length = clip["end"] - clip["start"]
        start_ts = utils.seconds_to_timestamp(clip["start"], ":")
        end_ts = utils.seconds_to_timestamp(clip["end"], ":")
        lines.append(f"Clip {i:02d}  ->  clip_{i:02d}.mp4")
        lines.append(f"  Start : {start_ts}  ({clip['start']:.1f}s)")
        lines.append(f"  End   : {end_ts}  ({clip['end']:.1f}s)")
        lines.append(f"  Length: {length:.1f}s")
        lines.append(f"  Score : {clip['score']}")
        lines.append(f"  Why   : {clip['score_breakdown']}")
        lines.append(f"  Text  : {clip['text'][:200]}")
        lines.append("")
    with open(summary_txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # JSON summary (strip the bulky per-word list to keep it readable)
    compact = []
    for i, clip in enumerate(clips, start=1):
        compact.append({
            "clip": i,
            "file": f"clip_{i:02d}.mp4",
            "start": clip["start"],
            "end": clip["end"],
            "length": round(clip["end"] - clip["start"], 2),
            "score": clip["score"],
            "score_breakdown": clip["score_breakdown"],
            "text": clip["text"],
        })
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(compact, f, ensure_ascii=False, indent=2)


def run(video_path, language="auto", model_size="small", num_clips=5,
        vertical_mode="crop", caption_style="classic", captions_on=True,
        buffer=video.DEFAULT_BUFFER,
        min_seconds=moments.MIN_SECONDS, max_seconds=moments.MAX_SECONDS,
        output_dir=None, keep_intermediate=False, use_cache=True):
    """The full pipeline. Returns the list of chosen clips."""

    # --- Checks up front, with friendly errors ---
    utils.check_ffmpeg()

    # Each video gets its own folder (clips/<video-name>/) so results from
    # different videos never mix together. The user can override with
    # --output-dir.
    is_url = download.is_url(video_path)
    if output_dir is None:
        output_dir = download.default_output_dir(video_path)
    work_dir = os.path.join(output_dir, "work")   # intermediate files
    os.makedirs(work_dir, exist_ok=True)

    # The input can be either a local file OR a web link. If it is a link,
    # download it — but reuse a previous download from the cache if we have it.
    if is_url:
        print("\n========== STEP 0: DOWNLOAD ==========")
        cached_source = cache.find_source(output_dir) if use_cache else None
        if cached_source:
            utils.ok(f"Using cached download: {os.path.basename(cached_source)}")
            video_path = cached_source
        else:
            video_path = download.download_video(
                video_path, cache.cache_dir(output_dir))
    else:
        utils.check_file_exists(video_path)

    base = os.path.splitext(os.path.basename(video_path))[0]

    print("\n========== STEP 1-2: TRANSCRIBE ==========")
    # Reuse the transcript if we already made one with the same language+model.
    transcript = cache.load_transcript(output_dir, language, model_size) \
        if use_cache else None
    if transcript:
        utils.ok("Using cached transcript (same language & model).")
    else:
        transcript, _, _ = transcribe.transcribe_video(
            video_path, language=language, model_size=model_size,
            output_dir=output_dir,
        )
        cache.save_transcript(output_dir, transcript, language, model_size)

    print("\n========== STEP 3: FIND BEST MOMENTS ==========")
    clips = moments.pick_best(
        transcript["segments"], num_clips=num_clips,
        min_seconds=min_seconds, max_seconds=max_seconds,
    )
    if not clips:
        utils.fail(
            "No suitable moments were found.\n"
            f"   The video may be shorter than the minimum clip length "
            f"({min_seconds}s), or it may have very little speech.\n"
            "   Try a longer video, or lower --min-seconds."
        )
    utils.ok(f"Selected {len(clips)} moment(s).")

    all_words = _flatten_words(transcript)
    source_duration = utils.ffprobe_duration(video_path)

    print("\n========== STEP 4-6: BUILD EACH CLIP ==========")
    for i, clip in enumerate(clips, start=1):
        print(f"\n--- Clip {i} of {len(clips)} ---")
        raw_path = os.path.join(work_dir, f"raw_{i:02d}.mp4")
        vert_path = os.path.join(work_dir, f"vert_{i:02d}.mp4")
        ass_path = os.path.join(work_dir, f"cap_{i:02d}.ass")
        final_path = os.path.join(output_dir, f"clip_{i:02d}.mp4")

        # 4) Cut (the real start/end include the safety buffer).
        real_start, real_end = video.cut_clip(
            video_path, clip["start"], clip["end"], raw_path,
            buffer=buffer, source_duration=source_duration,
        )
        # 5) Vertical.
        video.make_vertical(raw_path, vert_path, mode=vertical_mode)
        # 6) Captions (optional) aligned to the buffered clip range.
        if captions_on:
            captions.generate_ass(all_words, real_start, real_end, ass_path,
                                  animation=caption_style)
            video.burn_captions(vert_path, ass_path, final_path)
        else:
            # No captions wanted: the vertical clip IS the final clip.
            shutil.move(vert_path, final_path)
        utils.ok(f"Finished clip_{i:02d}.mp4")

    print("\n========== STEP 7: SUMMARY ==========")
    summary_txt = os.path.join(output_dir, "summary.txt")
    summary_json = os.path.join(output_dir, "summary.json")
    _write_summary(clips, summary_txt, summary_json, os.path.basename(video_path))
    utils.ok(f"Wrote summary: {summary_txt}")

    # Clean up intermediate files unless asked to keep them.
    if not keep_intermediate:
        shutil.rmtree(work_dir, ignore_errors=True)
    else:
        utils.info(f"Kept intermediate files in: {work_dir}")

    print("\n🎉 All done!")
    print(f"   Your clips and summary are in: {output_dir}/")
    return clips


def main():
    parser = argparse.ArgumentParser(
        description="Turn one long video into several short vertical clips "
                    "with burned-in word captions.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "video",
        nargs="?",            # optional: if omitted, we launch interactive mode
        default=None,
        help="a local video file path OR a video URL "
             "(YouTube, Shorts, Reels, etc.). "
             "Leave this out to use the interactive menu.",
    )
    parser.add_argument("-i", "--interactive", action="store_true",
                        help="use the step-by-step menu instead of typing flags")
    parser.add_argument("--no-captions", dest="captions_on",
                        action="store_false",
                        help="do not burn in captions")
    parser.add_argument("--cookies-from-browser", dest="cookies_browser",
                        default=None,
                        help="use this browser's cookies for downloads "
                             "(firefox, chrome, chromium, brave, edge, zen, ...)."
                             " Fixes YouTube's 'sign in to confirm you're not "
                             "a bot' error.")
    parser.add_argument("--language", default="auto",
                        help="language code: auto, ne (Nepali), en, hi, ...; "
                             "'mixed' for videos that switch languages; or "
                             "'mixed:ne' = mostly Nepali, keep English words "
                             "as English (recommended for Nepali+English)")
    parser.add_argument("--model", dest="model_size", default=None,
                        help="Whisper model: tiny, base, small, medium, "
                             "large-v3; 'nepali' (a Nepali-fine-tuned model); "
                             "or any Hugging Face model id. Default: small — "
                             "but 'nepali' automatically when --language ne.")
    parser.add_argument("--clips", dest="num_clips", type=int, default=5,
                        help="how many clips to make")
    parser.add_argument("--vertical", dest="vertical_mode", default="crop",
                        choices=["crop", "blur", "track"],
                        help="'crop' = zoom & center-crop; 'blur' = blurred fit; "
                             "'track' = follow the speaker's face")
    parser.add_argument("--caption-style", dest="caption_style",
                        default="classic",
                        choices=["classic", "bigword", "hormozi", "mrbeast",
                                 "karaoke", "highlight-box"],
                        help="caption look: classic, bigword, hormozi "
                             "(cyan bold caps), mrbeast (yellow/orange Bebas), "
                             "karaoke (colour sweep), highlight-box (plate)")
    parser.add_argument("--buffer", type=float, default=video.DEFAULT_BUFFER,
                        help="seconds of padding before/after each clip")
    parser.add_argument("--min-seconds", dest="min_seconds", type=int,
                        default=moments.MIN_SECONDS,
                        help="shortest allowed clip length")
    parser.add_argument("--max-seconds", dest="max_seconds", type=int,
                        default=moments.MAX_SECONDS,
                        help="longest allowed clip length")
    parser.add_argument("--output-dir", dest="output_dir", default=None,
                        help="where to save clips (default: <video>_clips)")
    parser.add_argument("--keep-intermediate", action="store_true",
                        help="keep the raw/vertical/ass working files")
    parser.add_argument("--no-cache", dest="use_cache", action="store_false",
                        help="ignore any cached download/transcript and redo "
                             "them from scratch")
    args = parser.parse_args()

    # If the user chose a browser for cookies, stash it where the downloader
    # looks (an env var), so it applies in both flag mode and the menu.
    if args.cookies_browser:
        os.environ["REELSMITH_COOKIES_BROWSER"] = args.cookies_browser

    # No video given, or --interactive asked for → run the friendly menu
    # (fancy arrow-key UI in a real terminal; simple prompts if piped).
    if args.interactive or args.video is None:
        from . import interactive
        interactive.launch()
        return

    # Pick the default model: 'nepali' (the Nepali fine-tune) automatically for
    # --language ne, otherwise 'small'. An explicit --model always wins.
    model_size = args.model_size
    if model_size is None:
        model_size = "nepali" if args.language == "ne" else "small"

    # Otherwise run directly from the command-line flags.
    run(
        args.video,
        language=args.language,
        model_size=model_size,
        num_clips=args.num_clips,
        vertical_mode=args.vertical_mode,
        caption_style=args.caption_style,
        captions_on=args.captions_on,
        buffer=args.buffer,
        min_seconds=args.min_seconds,
        max_seconds=args.max_seconds,
        output_dir=args.output_dir,
        keep_intermediate=args.keep_intermediate,
        use_cache=args.use_cache,
    )


if __name__ == "__main__":
    main()
