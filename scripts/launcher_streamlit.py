#!/usr/bin/env python3
"""
Launcher for the Streamlit interface (explicit; does not replace start_web.py).

Usage:
  python3 scripts/launcher_streamlit.py
"""

import subprocess
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    app = root / 'src' / 'gui' / 'streamlit_interface.py'
    if not app.exists():
        print('[ERROR] Streamlit app not found:', app)
        raise SystemExit(1)
    cmd = [
        sys.executable, '-m', 'streamlit', 'run', str(app),
        '--server.address=localhost',
        '--browser.gatherUsageStats=false'
    ]
    subprocess.call(cmd, cwd=root)


if __name__ == '__main__':
    main()

