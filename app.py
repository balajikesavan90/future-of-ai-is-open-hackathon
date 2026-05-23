"""Compatibility entrypoint for `streamlit run app.py`."""

import sys
from pathlib import Path

src_path = Path(__file__).resolve().parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from arctic_analytics.streamlit_app import main


main()
