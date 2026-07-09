"""Resolve paths so they work both from source and from a PyInstaller onedir build.

Config and assets live *next to the executable*, not inside it, so a booth
operator can swap a prize image without a rebuild.
"""
import sys
from pathlib import Path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


APP_DIR = app_dir()
CONFIG_PATH = APP_DIR / "config.json"
ASSETS_DIR = APP_DIR / "assets"
PRIZES_DIR = ASSETS_DIR / "prizes"
SOUNDS_DIR = ASSETS_DIR / "sounds"


def ensure_dirs() -> None:
    for d in (ASSETS_DIR, PRIZES_DIR, SOUNDS_DIR):
        d.mkdir(parents=True, exist_ok=True)
