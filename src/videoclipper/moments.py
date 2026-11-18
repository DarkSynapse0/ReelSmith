"""
moments.py
----------
Step 3 (part 2): choose the best moments to turn into clips.

The transcript from Step 2 is split into many short "segments" (roughly
one sentence each). This module:

  1. Builds CANDIDATE clips by joining consecutive sentences together
     until the clip is about 20–60 seconds long. Because we only ever
     cut at the boundary between two transcript segments, every candidate
     starts and ends on a natural sentence boundary (words are never
     cut in half).

  2. Scores every candidate using scoring.py.

  3. Picks the top N candidates, making sure the chosen clips do not
     overlap each other.

The scoring lives in scoring.py on purpose, so you can replace it later
without changing this file.
"""

from . import scoring


# Default clip-length limits (in seconds). You can override these.
MIN_SECONDS = 20
MAX_SECONDS = 60


def build_candidates(segments, min_seconds=MIN_SECONDS, max_seconds=MAX_SECONDS):
    """
    Create candidate clips from the list of transcript segments.

    We use a "sliding window" over sentences: starting at each sentence,
    we keep adding the next sentence until the clip would get too long.
    Any window whose length lands in the [min, max] range becomes a
    candidate. This produces lots of overlapping options; the selection
    step later keeps only the best, non-overlapping ones.

    Each candidate is a dictionary with start, end, text and words.
    """
    candidates = []
    n = len(segments)

    for i in range(n):
        start_time = segments[i]["start"]
        text_parts = []
        words = []

        for j in range(i, n):
            seg = segments[j]
            length = seg["end"] - start_time

            # If adding this sentence pushes us past the max length, stop
            # growing this particular window.
            if length > max_seconds:
                break

            text_parts.append(seg["text"])
            words.extend(seg.get("words") or [])
            end_time = seg["end"]

            # Once the window is long enough, record it as a candidate.
            if end_time - start_time >= min_seconds:
                candidates.append({
                    "start": round(start_time, 3),
                    "end": round(end_time, 3),
                    "text": " ".join(text_parts).strip(),
                    "words": words.copy(),
                })

    return candidates


def _overlaps(a, b):
    """True if two candidate clips share any time in common."""
    return a["start"] < b["end"] and b["start"] < a["end"]


def pick_best(segments, num_clips=5,
              min_seconds=MIN_SECONDS, max_seconds=MAX_SECONDS):
    """
    Return the top `num_clips` non-overlapping moments, best first.

    Steps:
      1. Build all candidates.
      2. Score each one with scoring.score_segment.
      3. Sort by score (highest first).
      4. Greedily take the best candidate, then the next best that does
         not overlap anything already chosen, and so on.
      5. Finally sort the chosen clips back into time order so the output
         clips are numbered from the start of the video.
    """
    candidates = build_candidates(segments, min_seconds, max_seconds)

    if not candidates:
        return []

    # Score every candidate and attach the score + breakdown to it.
    for cand in candidates:
        total, breakdown = scoring.score_segment(cand)
        cand["score"] = total
        cand["score_breakdown"] = breakdown

    # Best score first.
    candidates.sort(key=lambda c: c["score"], reverse=True)

    chosen = []
    for cand in candidates:
        if len(chosen) >= num_clips:
            break
        # Only keep it if it doesn't overlap something we already picked.
        if not any(_overlaps(cand, picked) for picked in chosen):
            chosen.append(cand)

    # Put the final clips in chronological order for nice numbering.
    chosen.sort(key=lambda c: c["start"])
    return chosen
