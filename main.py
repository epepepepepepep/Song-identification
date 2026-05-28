import json
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox

from gui.main_window import MainWindow


CONFIG_PATH = Path(__file__).resolve().parent / "config.json"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(config: dict) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as fh:
        json.dump(config, fh, ensure_ascii=False, indent=2)


def ensure_acoustid_key() -> dict:
    config = load_config()
    if config.get("acoustid_api_key"):
        return config

    key, ok = QInputDialog.getText(
        None,
        "מפתח AcoustID",
        "לא נמצא קובץ הגדרות. הזן מפתח API של AcoustID:",
    )
    if not ok or not key.strip():
        QMessageBox.critical(None, "שגיאה", "לא הוזן מפתח API. התוכנה תיסגר.")
        raise SystemExit(1)

    config["acoustid_api_key"] = key.strip()
    save_config(config)
    QMessageBox.information(None, "נשמר בהצלחה", "המפתח נשמר בקובץ config.json")
    return config


def main() -> None:
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    app.setFont(QFont("Segoe UI", 10))

    ensure_acoustid_key()

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
