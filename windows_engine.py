from __future__ import annotations

import os
import sys
from pathlib import Path

from app import main


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        release_root = exe_dir.parent
        if (release_root / "config").exists():
            return release_root
        return exe_dir
    return Path(__file__).resolve().parent


def ensure_runtime_dirs(root: Path) -> None:
    (root / "config").mkdir(exist_ok=True)
    (root / "logs").mkdir(exist_ok=True)

    example = root / "config" / "accounts.json.example"
    accounts = root / "config" / "accounts.json"
    if example.exists() and not accounts.exists():
        accounts.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")


if __name__ == "__main__":
    root = app_root()
    os.chdir(root)
    ensure_runtime_dirs(root)
    print("Multi Account Hedger Engine starting")
    print("Press Ctrl+C to stop")
    main()
