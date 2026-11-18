# ADR-005: Adopt the standard `src/` package layout and pip-installable packaging

**Status:** Accepted (v0.4.0)
**Context:** The prototype grew from one script into ~8 modules, plus tests and
docs. Time to give it a real structure.

## Context
Everything started as flat scripts in the repo root (`clipper.py`,
`transcribe.py`, …), run with `python clipper.py`. That's fine for a quick
prototype, but it has problems as the project grows:
- Imports relied on all files sitting in the same folder (`import utils`), which
  is fragile and breaks the moment you run from a different directory.
- There was no clean way to install it, no real command, and no obvious home
  for tests, samples, or generated output.

## Decision
Reorganize into the **standard Python `src/` layout** and make the project
**pip-installable**:
- All code lives in a package: **`src/reelsmith/`**.
- The old `clipper.py` becomes **`cli.py`**; `main()` is the entry point.
- Internal imports are **package-relative** (`from . import utils`).
- A **`pyproject.toml`** makes it installable with `pip install -e .` and
  defines a real **`reelsmith`** console command, plus `python -m
  reelsmith` via `__main__.py`.

## Rationale
- **No `sys.path` hacks.** Package-relative imports work no matter where you run
  from.
- **A real command.** `reelsmith my_video.mp4` reads like a finished tool,
  not a loose script.
- **The `src/` convention** prevents a common packaging trap: with the code
  under `src/`, your tests run against the *installed* package, so "it works on
  my machine because the files happen to be in the current folder" bugs can't
  hide.
- **A home for everything.** `tests/`, `samples/`, `output/`, `docs/`, and
  packaging metadata all have an obvious place.
- **Industry standard.** This is the layout most modern Python projects use, so
  it's familiar to any contributor and plays nicely with tooling.

## Consequences
- ✅ Installable, with `reelsmith` and `python -m reelsmith` entry points.
- ✅ Robust imports; tests can import the package cleanly.
- ✅ Clear separation of code, tests, docs, and generated output.
- ⚠️ Slightly more setup than flat scripts: you now run `pip install -e .` once
  (instead of just `pip install -r requirements.txt`). For a beginner this is a
  single extra step, documented in the README and `CONTRIBUTING.md`.
- ℹ️ `requirements.txt` is kept for convenience, but `pip install -e .` (which
  reads `pyproject.toml`) is the recommended install.

## Alternatives considered
- **Keep it flat / minimal tidy-up** — least disruptive, but keeps the fragile
  imports and gives no real command or install path.
- **A package folder without `src/`** (`reelsmith/` at the root) — simpler,
  but loses the `src/` safety property above. We chose the full `src/` layout
  deliberately for a "proper product" structure.
