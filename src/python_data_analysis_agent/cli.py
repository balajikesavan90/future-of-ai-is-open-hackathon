"""Command-line helpers for launching the Streamlit app."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def launch_streamlit(args: list[str] | None = None) -> int:
    app_path = Path(__file__).with_name("streamlit_app.py")
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app_path),
            *(args or []),
        ]
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "app":
        argv = argv[1:]
    return launch_streamlit(argv)


if __name__ == "__main__":
    raise SystemExit(main())
