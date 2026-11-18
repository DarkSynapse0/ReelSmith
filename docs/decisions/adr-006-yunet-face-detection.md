# ADR-006: Use OpenCV YuNet for face detection, bundled in the package

**Status:** Accepted (v0.5.0)
**Context:** The `--vertical track` mode needs to find where the speaker is in
each clip so it can crop around them instead of the middle.

## Context
To follow a speaker we need **face detection** that is:
- **free and fully local** (no paid vision APIs — a core project rule),
- **fast enough** to process many frames of a clip on a plain laptop CPU, and
- **precise enough** to give a usable pixel position.

The obvious first choice was OpenCV's classic **Haar cascade**
(`CascadeClassifier` + the bundled `haarcascade_frontalface_default.xml`), which
for years shipped inside OpenCV with zero setup.

**Problem discovered:** the installed OpenCV is **5.0** (the version with a
Python 3.14 `cp314` wheel). OpenCV 5.0 **removed** the classic Haar
`CascadeClassifier` from the default `cv2` surface and **no longer bundles** the
Haar cascade XML files. So the "easy, zero-download" Haar path isn't available.

## Decision
Use OpenCV 5's modern **YuNet** face detector (`cv2.FaceDetectorYN`) and
**bundle its model file** inside the package.
- Model: `face_detection_yunet.onnx` (~232 KB) from the OpenCV Zoo, stored at
  `src/reelsmith/models/` and shipped via `[tool.setuptools.package-data]`.
- Detection strategy in `reframe.py`: **sample ~3 frames/sec** (not every
  frame), take the **largest face** per frame, and use the **median** horizontal
  position to drive a single **fixed crop** for the whole clip.

## Rationale
- **YuNet is better anyway.** It's a small DNN detector that's more accurate and
  more robust than Haar cascades, while still tiny and fast on CPU.
- **Bundling the model keeps us offline.** The `.onnx` is small enough to ship
  with the code, so there's no runtime download — consistent with "works for
  free, locally, after setup."
- **Sampling, not every frame.** 3 frames/sec is plenty to locate a speaker and
  keeps the step fast; analyzing every frame would be far slower for no real
  benefit at this (fixed-crop) stage.
- **Median + fixed crop as the first version.** The median position is robust to
  the occasional bad detection, and a single fixed crop already solves the main
  complaint ("I'm off to the side and get cut off") without the complexity of
  per-frame panning. Simple, reliable, testable.
- **Lazy import.** OpenCV is a heavy library, so `video.py` imports `reframe`
  only inside the `track` branch — the `crop`/`blur` modes don't load it.

## Consequences
- ✅ Free, local, offline face detection with no runtime model download.
- ✅ Accurate enough that the off-center test framed the speaker perfectly while
  a center crop missed him entirely.
- ✅ Graceful fallback to center crop when no face is found, so it never breaks.
- ⚠️ Adds `opencv-python-headless` as a dependency (a biggish wheel, ~60 MB).
  Acceptable for the capability it unlocks.
- ⚠️ **Fixed crop only** — no panning to follow a moving speaker yet, and the
  "largest face" rule isn't true active-speaker detection. Tracked as future
  work in `ROADMAP.md`.
  **Superseded in 1.3.0:** tracking moved from this single median/fixed crop to
  **dynamic panning** (a per-time crop path animated by FFmpeg `sendcmd`). The
  YuNet detection choice here still stands; only the crop strategy changed. See
  `adr-009-dynamic-tracking.md`. (The "largest face" limitation remains.)
- ℹ️ A YuNet `setPreferableTarget` warning may print on load; it's harmless.

## Alternatives considered
- **Haar cascade** — the old default; unavailable in OpenCV 5 and less accurate.
- **MediaPipe** — accurate and fast, but an extra heavyweight dependency with
  its own model assets; YuNet came "in the box" with the OpenCV we already need.
- **A vision-language model (e.g. LLaVA via Ollama)** — smarter at *identifying*
  arbitrary things, but far too slow per-frame and imprecise for pixel-accurate
  tracking on a laptop. Reserved as a possible future piece for *object/product*
  tracking, not speaker tracking.
