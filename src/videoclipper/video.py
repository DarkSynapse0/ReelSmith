"""
video.py
--------
All the FFmpeg video operations live here:

  Step 4: cut a chosen segment out of the source video (with a buffer).
  Step 5: turn a clip into a 9:16 vertical video (center-crop or blurred fit).
  Step 6: burn word-by-word captions onto a clip.

Keeping every FFmpeg call in one file makes the pipeline (clipper.py) easy
to read, and means there is a single place to tweak video quality settings.
"""

import os

from . import utils


# A small buffer (in seconds) added before and after each clip so that the
# first and last words are not clipped off. Adjustable from clipper.py.
DEFAULT_BUFFER = 0.4


# -------------------------------------------------------------------------
# Step 4: Cut a segment out of the source video
# -------------------------------------------------------------------------

def cut_clip(source_path, start, end, output_path,
             buffer=DEFAULT_BUFFER, source_duration=None):
    """
    Cut the part of `source_path` between `start` and `end` seconds.

    A `buffer` is subtracted from the start and added to the end so that
    speech is not chopped mid-word. We clamp the times so we never ask
    for a negative start or go past the end of the video.

    We re-encode (rather than copy) the stream so the cut is accurate to
    the exact second — stream copying can only cut on keyframes, which
    would make clips start a little early or late.

    Returns the (buffered) start and end actually used, so later steps
    (captions) know the true time range of the clip.
    """
    if source_duration is None:
        source_duration = utils.ffprobe_duration(source_path)

    safe_start = max(0.0, start - buffer)
    safe_end = min(source_duration, end + buffer)
    duration = safe_end - safe_start

    utils.info(f"Cutting clip {safe_start:.1f}s → {safe_end:.1f}s "
               f"({duration:.1f}s long)...")

    utils.run_ffmpeg(
        [
            "ffmpeg", "-y",
            "-ss", f"{safe_start:.3f}",   # seek to start (fast seek)
            "-i", source_path,
            "-t", f"{duration:.3f}",       # keep this many seconds
            "-c:v", "libx264",             # re-encode video for an exact cut
            "-c:a", "aac",                 # re-encode audio
            "-pix_fmt", "yuv420p",         # widely compatible pixel format
            output_path,
        ],
        description="cutting a clip",
    )
    utils.ok(f"Saved raw clip: {os.path.basename(output_path)}")
    return safe_start, safe_end


# -------------------------------------------------------------------------
# Step 5: Make a clip vertical (9:16)
# -------------------------------------------------------------------------

# Target size for vertical video: 1080 wide, 1920 tall (9:16).
VERTICAL_WIDTH = 1080
VERTICAL_HEIGHT = 1920


def make_vertical(input_path, output_path, mode="crop"):
    """
    Convert a (usually wide) clip into a 1080x1920 vertical video.

    Three styles, chosen with `mode`:

      "crop" (default):
          Zoom in and center-crop. The video fills the whole 9:16 frame
          with no bars, but the left and right edges are cut off. Best
          when the important action is in the middle.

      "blur":
          Fit the whole original frame inside 9:16 without cutting
          anything, and fill the empty space above/below with a blurred,
          zoomed copy of the same video. Nothing is lost; you get the
          familiar "blurred background" look.

      "track":
          Detect the speaker's face and crop around THEM instead of the
          middle, so a person standing off to one side is not cut off.
          Falls back to a center crop if no face can be found.

    These are built with FFmpeg video filters:
      scale=...:force_original_aspect_ratio=increase  -> cover the frame
      scale=...:force_original_aspect_ratio=decrease  -> fit inside frame
      crop=W:H                                         -> cut to exact size
      boxblur                                          -> blur the background
      overlay=(W-w)/2:(H-h)/2                          -> center one over other
    """
    w, h = VERTICAL_WIDTH, VERTICAL_HEIGHT
    run_cwd = None   # set for 'track' so FFmpeg finds the sendcmd file safely

    if mode == "crop":
        utils.info("Making vertical (center-crop)...")
        video_filter = (
            f"scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h}"
        )
        args = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", video_filter,
            "-c:v", "libx264", "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            output_path,
        ]

    elif mode == "blur":
        utils.info("Making vertical (blurred background)...")
        # filter_complex lets us build two versions of the video and
        # combine them: a blurred background + the sharp, fitted foreground.
        filter_complex = (
            "[0:v]split=2[bg][fg];"
            f"[bg]scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},boxblur=20:3[bgblur];"
            f"[fg]scale={w}:{h}:force_original_aspect_ratio=decrease[fgfit];"
            "[bgblur][fgfit]overlay=(W-w)/2:(H-h)/2"
        )
        args = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-filter_complex", filter_complex,
            "-c:v", "libx264", "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            output_path,
        ]

    elif mode == "track":
        utils.info("Making vertical (speaker-tracking)...")
        # Import here so OpenCV is only loaded when tracking is actually used
        # (it is a heavy library and the other modes don't need it).
        from . import reframe
        plan = reframe.compute_crop_plan(input_path)
        if plan is None:
            utils.info("  No face found — falling back to a center crop.")
            video_filter = (
                f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                f"crop={w}:{h}"
            )
            args = [
                "ffmpeg", "-y",
                "-i", input_path,
                "-vf", video_filter,
                "-c:v", "libx264", "-c:a", "aac",
                "-pix_fmt", "yuv420p",
                output_path,
            ]
        else:
            utils.info(
                f"  Following the speaker across {len(plan['keyframes'])} "
                f"keyframe(s) "
                f"(face in {plan['frames_with_face']}/{plan['frames_seen']} "
                f"frames)."
            )
            # Write a tiny "sendcmd" script telling FFmpeg where the crop's
            # left edge should be at each moment. We run FFmpeg FROM that
            # folder and reference the file by bare name, so an unusual folder
            # name can never break the filter string.
            out_dir = os.path.dirname(os.path.abspath(output_path))
            cmds_name = os.path.splitext(os.path.basename(output_path))[0] + ".cmds"
            with open(os.path.join(out_dir, cmds_name), "w") as f:
                for t, x in plan["keyframes"]:
                    f.write(f"{t:.3f} crop x {x};\n")
            x0 = plan["keyframes"][0][1]
            video_filter = (
                f"sendcmd=f={cmds_name},"
                f"crop={plan['w']}:{plan['h']}:{x0}:{plan['y']},"
                f"scale={w}:{h}"
            )
            run_cwd = out_dir
            args = [
                "ffmpeg", "-y",
                "-i", os.path.abspath(input_path),
                "-vf", video_filter,
                "-c:v", "libx264", "-c:a", "aac",
                "-pix_fmt", "yuv420p",
                os.path.abspath(output_path),
            ]

    else:
        utils.fail(
            f"Unknown vertical mode '{mode}'. Use 'crop', 'blur', or 'track'."
        )

    utils.run_ffmpeg(args, description="making the clip vertical", cwd=run_cwd)
    utils.ok(f"Saved vertical clip: {os.path.basename(output_path)}")


# -------------------------------------------------------------------------
# Step 6: Burn captions onto a clip
# -------------------------------------------------------------------------

def burn_captions(input_path, ass_path, output_path):
    """
    Burn the captions from an .ass file permanently into the video.

    The `ass` filter renders the subtitle file (with all its fonts and
    colours) directly onto each frame. "Burned in" means the captions are
    now part of the picture and will show on any player.

    Putting a file path INSIDE an FFmpeg filter is fragile: characters like
    ' ! : & in a folder name break the filter string. To sidestep that
    completely, we run FFmpeg FROM the subtitle's own folder and refer to it
    by its bare filename (always "cap_NN.ass", which has no tricky
    characters). The video in/out paths are made absolute so they still
    resolve from that folder.
    """
    utils.info("Burning in captions...")
    ass_dir = os.path.dirname(os.path.abspath(ass_path))
    ass_name = os.path.basename(ass_path)
    utils.run_ffmpeg(
        [
            "ffmpeg", "-y",
            "-i", os.path.abspath(input_path),
            "-vf", f"ass={ass_name}",
            "-c:v", "libx264", "-c:a", "copy",  # keep the audio untouched
            "-pix_fmt", "yuv420p",
            os.path.abspath(output_path),
        ],
        description="burning in captions",
        cwd=ass_dir,
    )
    utils.ok(f"Saved captioned clip: {os.path.basename(output_path)}")
