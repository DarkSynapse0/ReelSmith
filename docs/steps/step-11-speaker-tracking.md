# Step 11 — Speaker-tracking vertical reframe (`--vertical track`)

## Goal
Stop cutting people off. The `crop` mode always takes the **middle** of the
frame, so a person standing off to one side gets chopped out of the vertical
clip. This step makes the crop **find the speaker's face and center on them**.

## What was built
- **`src/videoclipper/reframe.py`** — the face-tracking logic:
  - Opens the clip with OpenCV and samples **~3 frames per second** (not every
    frame — that would be slow and unnecessary).
  - On each sampled frame, runs OpenCV 5's **YuNet** face detector
    (`cv2.FaceDetectorYN`) and keeps the **largest** face (assumed to be the
    main speaker).
  - Takes the **median** horizontal position of those faces — a robust
    "typical" spot that ignores the odd stray frame.
  - Computes a **9:16 crop box** centered on that position, clamped so it never
    runs off the edge of the frame. Returns `None` if no face is found.
  - Key functions: `compute_crop_box()`, `_detect_face_centers()`.
- **Bundled model** `src/videoclipper/models/face_detection_yunet.onnx`
  (~232 KB, from the OpenCV Zoo) — committed into the package, so there is **no
  runtime download** and it works offline. `pyproject.toml` ships it via
  `[tool.setuptools.package-data]`.
- **New `track` mode in `video.make_vertical()`** — crops the 9:16 region
  reframe computed, then scales to 1080×1920. If reframe returns `None`, it
  **falls back to a plain center crop** with a friendly message. OpenCV is
  imported **lazily** (inside the `track` branch) so the `crop`/`blur` modes
  never pay to load it.
- **CLI:** `--vertical` now accepts `crop`, `blur`, or **`track`**.
- **Dependency:** added `opencv-python-headless>=4.9.0` (the "headless" build —
  no GUI libraries, which is all a command-line tool needs).

## How it was tested
1. **Controlled off-center test.** Took a real face video (YouTube "Me at the
   zoo"), shrank it, and padded it onto the **right third** of a 1600×480 black
   canvas — so the true center is x≈800 but the face sits at ≈x=1280.
   - `reframe.compute_crop_box` returned **x=1165** (shifted right, toward the
     face) versus a center crop's x≈665, with a face detected in **36/36**
     sampled frames.
   - **Before/after frames:** `track` mode framed the person perfectly; a plain
     center crop of the exact same video came out **all black** — it missed him
     entirely. A clear visual proof.
2. **Fallback.** On a solid-color clip with no face, track mode logged
   `No face found — falling back to a center crop` and still produced a valid
   1080×1920 clip.
3. **Regression + integration.** The 3 unit tests still pass. A full pipeline
   run via the installed command
   `videoclipper … --vertical track` transcribed, found a face in **42/42**
   checked frames, cropped around the speaker, burned captions, and output a
   1080×1920 clip.

## Result / what worked
Off-center speakers are now kept in frame instead of being cut off, and the
feature degrades gracefully (center crop) when there's no face. ✅

## Limitation / future
This is the **fixed-crop** version: it uses **one median position** for the
whole clip, so it does **not pan** to follow a person who moves across the
frame, and it simply picks the **largest** face when several are present. Future
upgrades (see `ROADMAP.md`): dynamic panning with smoothing, scene-cut snapping,
active-speaker selection among multiple faces, and optional object/product
tracking. Design rationale is in
`docs/decisions/adr-006-yunet-face-detection.md`.
