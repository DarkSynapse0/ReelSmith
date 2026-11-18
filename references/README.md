# references/

Drop videos (or notes) here that you want to use as **references** for the
clips you're making — e.g. a short you like the look of, a creator whose
caption style you want to copy, or raw footage you plan to clip later.

Suggested layout (make sub-folders however you like):

```
references/
├── styles/        ← example shorts whose caption/look you want to match
├── to-clip/       ← long videos you plan to turn into clips
└── notes.md       ← your own notes: "like the cyan hormozi captions here", etc.
```

## How to use a reference with the tool

- To **clip** a reference video, just point the tool at it:
  ```bash
  reelsmith references/to-clip/my_video.mp4 --language ne --caption-style hormozi
  ```
- To **match a caption style** you see in a reference, tell me which one it is
  (or describe it) and I can map it to a `--caption-style` or tune the look in
  `src/reelsmith/captions.py`.

## Notes
- **Video files in this folder are ignored by git** (see `.gitignore`), so large
  references won't be committed. Only `README.md` and `notes.md` are tracked.
- This folder is just for *your* reference material — the tool never writes here;
  finished clips go to `clips/<video-name>/`.
