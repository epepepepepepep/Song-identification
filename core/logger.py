from datetime import datetime
from pathlib import Path


LOG_FILE = Path(__file__).resolve().parents[1] / "changes.log"


def log_change(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(f"[{timestamp}] {message}\n")
