"""Shared pytest fixtures: make the app package importable without installation.

The app modules use a mix of `from app.x import y` and bare `from x import y`
imports (pre-existing inconsistency), so both the `server` directory and the
`server/app` directory need to be on `sys.path` for imports to resolve during
tests, regardless of how the app is normally launched.
"""
import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[1]
APP_DIR = SERVER_DIR / "app"

for path in (SERVER_DIR, APP_DIR):
    str_path = str(path)
    if str_path not in sys.path:
        sys.path.insert(0, str_path)
