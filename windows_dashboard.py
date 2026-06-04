from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

from streamlit.web import cli as streamlit_cli


APP_NAME = "Multi Account Hedger Dashboard"
DEFAULT_PORT = int(os.getenv("HEDGER_DASHBOARD_PORT", "8502"))


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        release_root = exe_dir.parent
        if (release_root / "config").exists():
            return release_root
        return exe_dir
    return Path(__file__).resolve().parent


def resource_path(relative_path: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", app_root()))
    return base / relative_path


def ensure_runtime_dirs(root: Path) -> None:
    (root / "config").mkdir(exist_ok=True)
    (root / "logs").mkdir(exist_ok=True)

    example = root / "config" / "accounts.json.example"
    accounts = root / "config" / "accounts.json"
    if example.exists() and not accounts.exists():
        accounts.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")


def open_browser_later(port: int) -> None:
    time.sleep(2.5)
    webbrowser.open(f"http://localhost:{port}")


def main() -> None:
    root = app_root()
    os.chdir(root)
    ensure_runtime_dirs(root)

    dashboard_script = resource_path("dashboard.py")
    if not dashboard_script.exists():
        raise FileNotFoundError(f"missing dashboard.py: {dashboard_script}")

    os.environ["STREAMLIT_SERVER_ADDRESS"] = "0.0.0.0"
    os.environ["STREAMLIT_SERVER_PORT"] = str(DEFAULT_PORT)
    os.environ["STREAMLIT_BROWSER_SERVER_ADDRESS"] = "localhost"
    os.environ["STREAMLIT_BROWSER_SERVER_PORT"] = str(DEFAULT_PORT)
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"

    threading.Thread(target=open_browser_later, args=(DEFAULT_PORT,), daemon=True).start()
    sys.argv = [
        "streamlit",
        "run",
        str(dashboard_script),
        "--server.address=0.0.0.0",
        f"--server.port={DEFAULT_PORT}",
        "--browser.serverAddress=localhost",
        f"--browser.serverPort={DEFAULT_PORT}",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false",
    ]
    streamlit_cli.main()


if __name__ == "__main__":
    print(f"{APP_NAME} starting on http://localhost:{DEFAULT_PORT}")
    main()
