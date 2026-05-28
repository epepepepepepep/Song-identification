import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main() -> None:
    if sys.version_info < (3, 12):
        raise SystemExit("נדרשת Python 3.12 ומעלה")

    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
