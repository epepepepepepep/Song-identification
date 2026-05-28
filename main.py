import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from ui.main_window import MainWindow


def main() -> None:
    if sys.version_info < (3, 12):
        raise SystemExit("נדרשת Python 3.12 ומעלה")

    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)

    try:
        window = MainWindow()
    except Exception as exc:  # noqa: BLE001
        QMessageBox.critical(None, "שגיאה", f"נכשלה פתיחת האפליקציה: {exc}")
        raise SystemExit(1) from exc

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
