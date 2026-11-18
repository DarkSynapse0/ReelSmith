"""
scoring.py
----------
Step 3 (part 1): decide how "good" a candidate clip is.

This file is deliberately SEPARATE from the rest of the code so you can
swap it out later for something smarter (for example, a machine-learning
model, or an LLM that reads the text) WITHOUT touching moments.py.

The only thing the rest of the program relies on is this contract:

    score_segment(segment) -> (total_score, breakdown_dict)

where `segment` is a dictionary like:
    {
        "start": 12.0,
        "end": 48.0,
        "text": "the full text of the clip",
        "words": [ {"word": "Hello", "start": 12.0, "end": 12.4}, ... ],
    }

`total_score` is a number (higher = more likely to be a good clip) and
`breakdown_dict` explains how we got there, which is handy for debugging
and for the summary file.

Everything here uses simple, local, free heuristics — no internet, no AI.
"""

import re


# -------------------------------------------------------------------------
# Word lists used by the heuristics.
# These are intentionally small and easy for you to edit/extend.
# Add Nepali, Hindi, or your own words freely.
# -------------------------------------------------------------------------

# Words that often signal emotion, emphasis, or a strong claim.
EMPHATIC_WORDS = {
    # English
    "amazing", "incredible", "never", "always", "best", "worst", "huge",
    "secret", "mistake", "important", "crazy", "shocking", "love", "hate",
    "must", "stop", "warning", "free", "proven", "easy", "wrong", "right",
    "biggest", "powerful", "surprising", "truth", "finally", "everyone",
    # Romanized / common Nepali emphatic words (edit as you like)
    "ramro", "naramro", "dherai", "sabai", "kahilei",
}

# Devanagari emphatic/strong words (Nepali). Matched as substrings because
# Devanagari words attach suffixes, so exact matching is less reliable.
EMPHATIC_DEVANAGARI = [
    "सबैभन्दा",   # the most / -est
    "धेरै",       # very / a lot
    "कहिल्यै",    # never / ever
    "महत्त्वपूर्ण",  # important
    "रमाइलो",     # fun / enjoyable
    "गजब",        # amazing
    "सत्य",       # truth
    "गल्ती",      # mistake
]

# Words that commonly start a question in English.
QUESTION_STARTERS = {
    "what", "why", "how", "who", "when", "where", "which", "do", "does",
    "did", "is", "are", "can", "could", "would", "should", "have",
}

# Devanagari question words (Nepali).
QUESTION_DEVANAGARI = ["के", "किन", "कसरी", "कहाँ", "कहिले", "को", "कुन"]

# Words/phrases that make a strong opening "hook".
HOOK_STARTERS = {
    "here", "this", "today", "listen", "imagine", "stop", "wait", "look",
    "the", "let", "did", "i", "you", "most", "everyone", "nobody",
}


# -------------------------------------------------------------------------
# Small helper functions, one per heuristic.
# Each returns a score roughly in the 0..1 range so they are easy to weigh.
# -------------------------------------------------------------------------

def _first_sentence(text):
    """Return the first sentence of the text (best-effort)."""
    # Split on sentence-ending punctuation, keep the first non-empty piece.
    parts = re.split(r"[.!?।]", text)  # '।' is the Devanagari full stop
    for part in parts:
        if part.strip():
            return part.strip()
    return text.strip()


def _words_list(text):
    """Lowercased list of plain word tokens from the text."""
    return re.findall(r"[^\s]+", text.lower())


def score_opening(text):
    """
    A strong opening grabs attention. We reward clips whose first word
    looks like a hook, and give a smaller bonus for a short, punchy
    first sentence.
    """
    first = _first_sentence(text)
    words = _words_list(first)
    if not words:
        return 0.0

    score = 0.0
    if words[0].strip(".,!?\"'") in HOOK_STARTERS:
        score += 0.7
    # Short, snappy openers (3–9 words) tend to work well.
    if 3 <= len(words) <= 9:
        score += 0.3
    return min(score, 1.0)


def score_question(text):
    """
    Questions pull people in ("How do you...?"). Reward a question mark
    and question-starting words in English or Nepali.
    """
    score = 0.0
    if "?" in text:
        score += 0.6
    first_words = _words_list(_first_sentence(text))
    if first_words and first_words[0].strip(".,!?\"'") in QUESTION_STARTERS:
        score += 0.4
    for q in QUESTION_DEVANAGARI:
        if q in text:
            score += 0.4
            break
    return min(score, 1.0)


def score_emphasis(text):
    """
    Count emotional / emphatic words. More emphasis (up to a point)
    suggests a more engaging moment.
    """
    words = set(w.strip(".,!?\"'()") for w in _words_list(text))
    hits = len(words & EMPHATIC_WORDS)
    for w in EMPHATIC_DEVANAGARI:
        if w in text:
            hits += 1
    # 3 or more emphatic words already counts as "very emphatic".
    return min(hits / 3.0, 1.0)


def score_pace(segment):
    """
    Reward a comfortable speaking pace. Too slow can feel boring, too fast
    can feel rushed. We measure words per second and prefer ~2.0–3.3 wps
    (a typical lively but clear pace).
    """
    duration = segment["end"] - segment["start"]
    word_count = len(segment.get("words") or _words_list(segment["text"]))
    if duration <= 0 or word_count == 0:
        return 0.0
    wps = word_count / duration
    if 2.0 <= wps <= 3.3:
        return 1.0
    # Gentle falloff outside the sweet spot instead of a hard cutoff.
    if wps < 2.0:
        return max(0.0, wps / 2.0)
    return max(0.0, 1.0 - (wps - 3.3) / 3.0)


def score_silence(segment):
    """
    Penalise clips that contain long silent gaps between words — those
    feel like dead air. We look at the biggest gap between consecutive
    words. A score of 1.0 means tight, gap-free speech.
    """
    words = segment.get("words") or []
    if len(words) < 2:
        return 0.5  # not enough info; stay neutral
    biggest_gap = 0.0
    for earlier, later in zip(words, words[1:]):
        gap = later["start"] - earlier["end"]
        biggest_gap = max(biggest_gap, gap)
    # No gap -> 1.0 ; a 2-second gap or more -> 0.0
    return max(0.0, 1.0 - biggest_gap / 2.0)


# -------------------------------------------------------------------------
# The weights decide how much each heuristic matters in the final score.
# Tweak these numbers to change the "taste" of the clip picker.
# -------------------------------------------------------------------------

WEIGHTS = {
    "opening": 2.0,
    "question": 1.5,
    "emphasis": 2.0,
    "pace": 1.0,
    "silence": 1.0,
}


def score_segment(segment):
    """
    Combine all the heuristics into one score.

    Returns:
        total     : a single number (higher is better)
        breakdown : a dict of the individual 0..1 heuristic scores,
                    useful for the summary file and for understanding
                    WHY a clip was chosen.
    """
    parts = {
        "opening": score_opening(segment["text"]),
        "question": score_question(segment["text"]),
        "emphasis": score_emphasis(segment["text"]),
        "pace": score_pace(segment),
        "silence": score_silence(segment),
    }
    total = sum(WEIGHTS[name] * value for name, value in parts.items())
    # Round for tidy display; keep enough precision to compare clips.
    breakdown = {name: round(value, 3) for name, value in parts.items()}
    return round(total, 3), breakdown
