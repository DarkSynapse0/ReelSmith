"""
__main__.py
-----------
This special file is what lets you run the whole tool with:

    python -m reelsmith my_video.mp4 --language ne

When Python runs a package with `-m`, it executes this file. We simply
hand control to the real command-line entry point in cli.py.
"""

from .cli import main

if __name__ == "__main__":
    main()
