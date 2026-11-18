"""
reframe.py
----------
Speaker-tracking reframe: figure out WHERE the person is in a clip so the
vertical crop can be placed on them instead of blindly on the middle.

How it works (all local, free, offline):
  1. Open the clip and look at a few frames per second (not every frame —
     that would be slow and unnecessary).
  2. On each sampled frame, use OpenCV's YuNet face detector to find faces.
  3. Keep the biggest face in each frame (usually the main speaker) and
     remember its horizontal position.
  4. Take the MEDIAN of those positions — a robust "typical" location that
     ignores the odd bad frame.
  5. Work out a 9:16 crop box centered on that position (clamped so it
     never runs off the edge of the video).

If no faces are found (e.g. a slideshow, b-roll, or the person faces away
the whole time), we return None and the caller falls back to a center crop.

This module only figures out the crop box; the actual cropping is done by
FFmpeg over in video.py.
"""

import os
import statistics

# Quieten OpenCV's own C++ log output BEFORE importing cv2. The face detector
# prints a harmless warning ("setPreferableTarget ... Targets are not supported
# by the new graph engine") straight to the terminal, which would otherwise
# scribble over our clean progress display. This env var must be set first.
os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")

import cv2

# Belt-and-braces: also set it through the API in case the env var was missed.
try:
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
except Exception:
    pass

from . import utils


# The face-detection model file lives next to this code, inside the package.
_MODEL_PATH = os.path.join(os.path.dirname(__file__),
                           "models", "face_detection_yunet.onnx")

# Target aspect ratio for the vertical crop: 9 wide to 16 tall.
_ASPECT_W = 9
_ASPECT_H = 16


def _even(n):
    """Round to the nearest even number (video encoders prefer even sizes)."""
    n = int(round(n))
    return n - (n % 2)


def _detect_face_centers(video_path, sample_fps=3, score_threshold=0.7):
    """
    Walk through the video sampling a few frames per second and return:
      centers      : list of horizontal positions (pixels) of the main face
      frame_width  : width of the video in pixels
      frame_height : height of the video in pixels
      frames_seen  : how many frames we actually checked

    We pick the LARGEST detected face in each sampled frame, on the
    assumption that the closest/biggest face is the speaker.
    """
    if not os.path.isfile(_MODEL_PATH):
        utils.fail(
            "The face-detection model is missing:\n"
            f"   {_MODEL_PATH}\n"
            "   Reinstall or re-download the project files."
        )

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        utils.fail(f"Could not open the video for face detection: {video_path}")

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    # Only run the detector every `step` frames to hit roughly sample_fps.
    step = max(1, int(round(video_fps / sample_fps)))

    detector = cv2.FaceDetectorYN.create(_MODEL_PATH, "",
                                         (frame_width, frame_height),
                                         score_threshold)

    centers = []
    frames_seen = 0
    frame_index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_index % step == 0:
            frames_seen += 1
            _, faces = detector.detect(frame)
            if faces is not None and len(faces) > 0:
                # Each face row is [x, y, w, h, ...landmarks..., score].
                # Choose the one with the largest area (w * h).
                biggest = max(faces, key=lambda f: f[2] * f[3])
                x, w = biggest[0], biggest[2]
                centers.append(x + w / 2.0)  # horizontal center of the face
        frame_index += 1

    cap.release()
    return centers, frame_width, frame_height, frames_seen


def compute_crop_box(video_path, sample_fps=3):
    """
    Decide the 9:16 crop box that keeps the speaker in frame.

    Returns a dict:
        {"w", "h", "x", "y", "frames_with_face", "frames_seen"}
    or None if no faces were found (caller should fall back to center crop).

    The box is expressed in the ORIGINAL video's pixels, so FFmpeg can crop
    it directly and then scale the result to 1080x1920.
    """
    centers, vw, vh, frames_seen = _detect_face_centers(video_path, sample_fps)

    if not centers:
        return None  # no faces -> let the caller center-crop instead

    # The "typical" horizontal position of the speaker. Median shrugs off
    # the occasional stray detection far from the rest.
    target_cx = statistics.median(centers)

    # Size of a 9:16 rectangle that fits inside the original frame.
    crop_w = _even(vh * _ASPECT_W / _ASPECT_H)
    crop_h = vh
    if crop_w > vw:
        # The source is already narrower than 9:16 (e.g. a square video):
        # use the full width and shrink the height to keep 9:16.
        crop_w = _even(vw)
        crop_h = _even(vw * _ASPECT_H / _ASPECT_W)

    # Place the crop so its center sits on the speaker, then clamp it so it
    # stays fully inside the frame.
    x = int(round(target_cx - crop_w / 2.0))
    x = max(0, min(x, vw - crop_w))
    y = max(0, (vh - crop_h) // 2)

    return {
        "w": crop_w,
        "h": crop_h,
        "x": x,
        "y": y,
        "frames_with_face": len(centers),
        "frames_seen": frames_seen,
    }


# -------------------------------------------------------------------------
# Dynamic tracking: a crop that FOLLOWS the speaker over time
# -------------------------------------------------------------------------

def compute_crop_plan(video_path, sample_fps=10):
    """
    Build a time-varying crop that follows the speaker, instead of one fixed
    position. Returns:

        {"w", "h", "y", "keyframes": [(time_seconds, crop_x), ...],
         "frames_with_face", "frames_seen"}

    or None if no face is ever found (caller should center-crop).

    The steps:
      1. Sample several frames per second and find the main face in each.
      2. Decide a target horizontal position per sample:
           - a face       -> the face's centre
           - a brief gap  -> hold the last face position (short look-aways)
           - a long gap   -> drift back to the centre (e.g. screen recording)
      3. Detect big jumps (scene cuts / the speaker leaping across) and SNAP
         rather than slide across them.
      4. Smooth everything so the pan glides instead of jittering.
      5. Emit keyframes (only when the position actually changes) that FFmpeg
         can animate with its `sendcmd` + `crop` filters.
    """
    if not os.path.isfile(_MODEL_PATH):
        utils.fail(f"Face model missing: {_MODEL_PATH}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        utils.fail(f"Could not open video for tracking: {video_path}")

    vw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    vh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, int(round(fps / sample_fps)))
    detector = cv2.FaceDetectorYN.create(_MODEL_PATH, "", (vw, vh), 0.7)

    crop_w = _even(vh * _ASPECT_W / _ASPECT_H)
    crop_h = vh
    if crop_w > vw:
        crop_w = _even(vw)
        crop_h = _even(vw * _ASPECT_H / _ASPECT_W)
    y = max(0, (vh - crop_h) // 2)

    # 1. Sample the face centre over time.
    samples = []  # (time, raw_center_x or None)
    frame_index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_index % step == 0:
            _, faces = detector.detect(frame)
            rx = None
            if faces is not None and len(faces) > 0:
                biggest = max(faces, key=lambda f: f[2] * f[3])
                rx = biggest[0] + biggest[2] / 2.0
            samples.append((frame_index / fps, rx))
        frame_index += 1
    cap.release()

    face_count = sum(1 for _, rx in samples if rx is not None)
    if face_count == 0:
        return None

    # 2-4. Turn raw detections into a smooth, snapping crop path.
    center = vw / 2.0
    hold_seconds = 2.0          # keep last face position through short gaps
    jump_fraction = 0.30        # jump bigger than this = a cut (snap)
    alpha = 0.14                # smoothing strength (lower = gentler, smoother)
    dead_zone = 0.05 * vw       # ignore movements smaller than this (anti-jitter)
    per_sample = 1.0 / sample_fps

    keyframes = []
    last_face_x = None
    gap_samples = 0
    prev_face_x = None
    smoothed = None
    last_emitted_x = None

    for t, rx in samples:
        snap = False
        if rx is not None:
            if prev_face_x is not None and abs(rx - prev_face_x) > jump_fraction * vw:
                snap = True
            target = rx
            last_face_x = rx
            prev_face_x = rx
            gap_samples = 0
        else:
            gap_samples += 1
            if last_face_x is not None and gap_samples * per_sample <= hold_seconds:
                target = last_face_x
            else:
                target = center

        if smoothed is None or snap:
            smoothed = target            # snap: start fresh at a cut
        elif abs(target - smoothed) > dead_zone:
            # Only drift toward the face once it moves beyond the dead zone,
            # so tiny detection wobble doesn't make the crop twitch. The low
            # alpha then eases there gradually, so the pan glides.
            smoothed = alpha * target + (1 - alpha) * smoothed
        # else: within the dead zone — hold still (stable framing).

        crop_x = int(round(smoothed - crop_w / 2.0))
        crop_x = max(0, min(crop_x, vw - crop_w))

        # Record a keyframe whenever the crop moves even slightly (so the pan
        # is finely stepped and looks continuous), or at a cut.
        if last_emitted_x is None or abs(crop_x - last_emitted_x) >= 2 or snap:
            keyframes.append((round(t, 3), crop_x))
            last_emitted_x = crop_x

    # Make sure the very first keyframe is at time 0.
    if keyframes and keyframes[0][0] > 0.0:
        keyframes.insert(0, (0.0, keyframes[0][1]))

    return {
        "w": crop_w, "h": crop_h, "y": y, "keyframes": keyframes,
        "frames_with_face": face_count, "frames_seen": len(samples),
    }


# -------------------------------------------------------------------------
# Diagnostic: see what the face detector actually finds in a video
# -------------------------------------------------------------------------

def diagnose(video_path, out_dir="debug_faces", sample_fps=3):
    """
    Run face detection over a video and PRINT what it found, plus save a few
    annotated frames (green = detected face, red = the crop that the current
    fixed-crop tracker would use). This tells us whether a weak result is a
    detection problem (few faces) or a framing problem (faces move / many
    shots), so we can fix the right thing.

    Run it with:  python -m videoclipper.reframe <video>
    """
    if not os.path.isfile(_MODEL_PATH):
        utils.fail(f"Face model missing: {_MODEL_PATH}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        utils.fail(f"Could not open video: {video_path}")

    vw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    vh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, int(round(fps / sample_fps)))
    detector = cv2.FaceDetectorYN.create(_MODEL_PATH, "", (vw, vh), 0.7)

    crop_w = _even(vh * _ASPECT_W / _ASPECT_H)
    crop_w = min(crop_w, _even(vw))

    os.makedirs(out_dir, exist_ok=True)
    records = []          # (time, center_x or None, face_box or None)
    saved = 0
    frame_index = 0
    print(f"\nAnalysing '{os.path.basename(video_path)}' "
          f"({vw}x{vh}) ...\n")

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_index % step == 0:
            t = frame_index / fps
            _, faces = detector.detect(frame)
            box = None
            cx = None
            if faces is not None and len(faces) > 0:
                biggest = max(faces, key=lambda f: f[2] * f[3])
                box = [int(biggest[k]) for k in range(4)]
                cx = box[0] + box[2] / 2.0
            records.append((t, cx, box))

            # Save up to ~8 annotated frames, spread across the video.
            if saved < 8 and len(records) % max(1, int(sample_fps * 3)) == 1:
                shot = frame.copy()
                if box:
                    cv2.rectangle(shot, (box[0], box[1]),
                                  (box[0] + box[2], box[1] + box[3]),
                                  (0, 255, 0), 3)
                    cxi = int(max(0, min(cx - crop_w / 2, vw - crop_w)))
                else:
                    cxi = int((vw - crop_w) // 2)
                cv2.rectangle(shot, (cxi, 0), (cxi + crop_w, vh), (0, 0, 255), 3)
                cv2.imwrite(os.path.join(out_dir, f"frame_{saved:02d}.png"), shot)
                saved += 1
        frame_index += 1
    cap.release()

    # ----- Summarise -----
    total = len(records)
    if total == 0:
        print("  Could not read any frames from this video.")
        print("   This usually means the codec (often AV1/VP9 in .webm files)\n"
              "   can't be decoded by OpenCV directly. Inside the normal\n"
              "   pipeline this is not a problem, because each clip is first\n"
              "   re-encoded to H.264 before face detection. To diagnose, try\n"
              "   an .mp4 version of the video.\n")
        return
    with_face = [r for r in records if r[1] is not None]
    pct = 100.0 * len(with_face) / total if total else 0.0
    print(f"  Frames checked        : {total}")
    print(f"  Frames with a face    : {len(with_face)}  ({pct:.0f}%)")

    if with_face:
        xs = [r[1] for r in with_face]
        xs_pct = [100.0 * x / vw for x in xs]
        xmin, xmax = min(xs_pct), max(xs_pct)
        med = statistics.median(xs_pct)
        spread = xmax - xmin
        print(f"  Face x position       : min {xmin:.0f}%  median {med:.0f}%  "
              f"max {xmax:.0f}%  (of frame width)")
        print(f"  Horizontal spread     : {spread:.0f}% of the width")

        # Count big jumps between consecutive face detections (≈ scene cuts
        # or the speaker moving a lot).
        jumps = 0
        prev = None
        for _, x, _ in with_face:
            if prev is not None and abs(x - prev) > 0.25 * vw:
                jumps += 1
            prev = x
        print(f"  Big position jumps    : {jumps}  (≈ cuts / large moves)")

        print("\n  Verdict:")
        if pct < 30:
            print("   • A face is visible in only a small part of the video "
                  "(screen-\n     recording / b-roll heavy). Face tracking can't "
                  "help much here —\n     'blur' or 'crop' will usually look "
                  "better for this video.")
        elif spread > 30 or jumps > 3:
            print("   • The face moves around a lot / there are several shots, "
                  "so a single\n     fixed crop is wrong for much of the clip. "
                  "This needs DYNAMIC\n     tracking (follow + snap at cuts) — "
                  "which is the upgrade to build.")
        else:
            print("   • The face stays fairly still — the current fixed crop "
                  "should work.\n     If it still looks off, check the saved "
                  "frames below.")
    else:
        print("\n  Verdict:")
        print("   • No faces were detected at all. The speaker may be small, "
              "turned away,\n     or it's not talking-head footage. Use 'crop' "
              "or 'blur' for this video.")

    print(f"\n  Saved {saved} annotated frame(s) to: {out_dir}/")
    print("   (green box = detected face, red box = where it would crop)\n")


def _main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Diagnose face detection / tracking on a video.")
    parser.add_argument("video", help="path to a video file")
    parser.add_argument("--out-dir", default="debug_faces",
                        help="where to save annotated frames")
    args = parser.parse_args()
    diagnose(args.video, out_dir=args.out_dir)


if __name__ == "__main__":
    _main()
