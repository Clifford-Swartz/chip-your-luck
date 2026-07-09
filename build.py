"""Build a distributable Windows folder: python build.py

Produces dist/ChipYourLuck/ containing ChipYourLuck.exe alongside an
editable config.json and assets/ folder. Zip that folder and hand it to
whoever runs the booth.

Deliberately --onedir, not --onefile: onefile unpacks to a temp directory on
every launch (slow) and buries config.json where nobody can edit it.
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAME = "ChipYourLuck"
DIST = ROOT / "dist" / NAME


def main() -> int:
    for stale in (ROOT / "build", ROOT / "dist", ROOT / f"{NAME}.spec"):
        if stale.is_dir():
            shutil.rmtree(stale)
        elif stale.exists():
            stale.unlink()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onedir", "--windowed",
        "--name", NAME,
        "--hidden-import", "tkinter",
        str(ROOT / "main.py"),
    ]
    print(" ".join(cmd))
    if subprocess.call(cmd) != 0:
        return 1

    # Ship config + assets *beside* the exe so they stay editable.
    shutil.copy2(ROOT / "config.json", DIST / "config.json")
    for sub in ("assets/prizes", "assets/sounds"):
        (DIST / sub).mkdir(parents=True, exist_ok=True)
    src_assets = ROOT / "assets"
    if src_assets.is_dir():
        shutil.copytree(src_assets, DIST / "assets", dirs_exist_ok=True)

    print(f"\nBuilt: {DIST}\nRun:   {DIST / (NAME + '.exe')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
