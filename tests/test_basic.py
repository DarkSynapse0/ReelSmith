"""
test_basic.py
-------------
Simple tests for the parts of the tool that don't need FFmpeg or a video:
the timestamp formatter, the scoring heuristics, and the moment selection.

You can run these two ways:

    python tests/test_basic.py        # plain, no extra tools needed
    python -m pytest                  # if you have pytest installed

Both work because each check is a function named test_... that just uses
`assert`. These give you quick confidence that a change didn't break the
core logic before you spend time running a full video through the tool.
"""

from reelsmith import utils, scoring, moments


def test_timestamp_formatting():
    """Seconds should turn into subtitle timestamps correctly."""
    assert utils.seconds_to_timestamp(0) == "00:00:00,000"
    assert utils.seconds_to_timestamp(75.5) == "00:01:15,500"
    # ASS style uses a dot separator.
    assert utils.seconds_to_timestamp(75.5, ".") == "00:01:15.500"


def test_scoring_returns_total_and_breakdown():
    """score_segment must return (number, dict) and reward a question."""
    segment = {
        "start": 0.0,
        "end": 25.0,
        "text": "Why do most people fail? This is incredibly important.",
        "words": [
            {"word": "Why", "start": 0.0, "end": 0.4},
            {"word": "fail", "start": 0.4, "end": 0.8},
        ],
    }
    total, breakdown = scoring.score_segment(segment)
    assert isinstance(total, float)
    assert isinstance(breakdown, dict)
    # It contains a question mark, so the question heuristic should fire.
    assert breakdown["question"] > 0


def test_pick_best_respects_length_and_overlap():
    """
    Chosen clips must land within the length limits and must not overlap.
    We build a simple 120-second transcript of 5-second sentences.
    """
    texts = [
        "Why do people fail at this?", "The answer is simple.",
        "This is the biggest mistake.", "It is very important.",
        "Always back up your files.", "Never skip this step.",
        "Here is a boring filler line.", "Another slow filler line.",
    ] * 3
    segments = []
    t = 0.0
    for i, txt in enumerate(texts):
        words = txt.split()
        per = 5.0 / len(words)
        wlist = [
            {"word": w, "start": round(t + k * per, 3),
             "end": round(t + (k + 1) * per, 3)}
            for k, w in enumerate(words)
        ]
        segments.append({"id": i, "start": round(t, 3), "end": round(t + 5.0, 3),
                         "text": txt, "words": wlist})
        t += 5.0

    clips = moments.pick_best(segments, num_clips=3, min_seconds=20, max_seconds=60)
    assert len(clips) == 3
    for clip in clips:
        length = clip["end"] - clip["start"]
        assert 20 <= length <= 60
    # No two chosen clips may overlap in time.
    for a, b in zip(clips, clips[1:]):
        assert a["end"] <= b["start"]


# Allow running this file directly without pytest.
if __name__ == "__main__":
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  PASS  {name}")
            passed += 1
    print(f"\n{passed} test(s) passed.")
