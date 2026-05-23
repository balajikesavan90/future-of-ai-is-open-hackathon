"""Command-line helpers for launching the Streamlit app."""

import subprocess
import sys
from pathlib import Path


def main():
    app_path = Path(__file__).with_name("streamlit_app.py")
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app_path),
            *sys.argv[1:],
        ]
    )
