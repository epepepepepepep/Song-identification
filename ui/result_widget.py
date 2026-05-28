from pathlib import Path

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class ResultWidget(QGroupBox):
    save_requested = Signal(str, dict)

    def __init__(self, file_path: str, metadata: dict[str, str]):
        super().__init__(Path(file_path).name)
        self.file_path = file_path
        self.setLayoutDirection(Qt.RightToLeft)

        root = QVBoxLayout(self)
        form = QFormLayout()

        self.title_edit = QLineEdit(metadata.get("title", ""))
        self.artist_edit = QLineEdit(metadata.get("artist", ""))
        self.album_edit = QLineEdit(metadata.get("album", ""))
        self.year_edit = QLineEdit(metadata.get("year", ""))
        self.genre_edit = QLineEdit(metadata.get("genre", ""))
        self.track_edit = QLineEdit(metadata.get("track", ""))
        self.score_label = QLabel(metadata.get("score", "0.00"))
        self.youtube_title_edit = QLineEdit(metadata.get("youtube_title", ""))
        self.youtube_url_edit = QLineEdit(metadata.get("youtube_url", ""))
        self.youtube_title_edit.setReadOnly(True)
        self.youtube_url_edit.setReadOnly(True)

        form.addRow("שם שיר:", self.title_edit)
        form.addRow("אמן:", self.artist_edit)
        form.addRow("אלבום:", self.album_edit)
        form.addRow("שנה:", self.year_edit)
        form.addRow("ז'אנר:", self.genre_edit)
        form.addRow("מספר רצועה:", self.track_edit)
        form.addRow("ציון התאמה:", self.score_label)
        form.addRow("שם סרטון ביוטיוב:", self.youtube_title_edit)
        form.addRow("קישור יוטיוב:", self.youtube_url_edit)

        actions = QHBoxLayout()
        self.status_label = QLabel("מוכן לשמירה")
        self.save_button = QPushButton("שמור מטא-דאטה")
        self.open_youtube_button = QPushButton("פתח ביוטיוב")
        self.save_button.clicked.connect(self._emit_save)
        self.open_youtube_button.clicked.connect(self._open_youtube)
        self.open_youtube_button.setEnabled(bool(self.youtube_url_edit.text().strip()))
        actions.addWidget(self.status_label)
        actions.addStretch()
        actions.addWidget(self.open_youtube_button)
        actions.addWidget(self.save_button)

        root.addLayout(form)
        root.addLayout(actions)

    def metadata(self) -> dict[str, str]:
        return {
            "title": self.title_edit.text().strip(),
            "artist": self.artist_edit.text().strip(),
            "album": self.album_edit.text().strip(),
            "year": self.year_edit.text().strip(),
            "genre": self.genre_edit.text().strip(),
            "track": self.track_edit.text().strip(),
            "score": self.score_label.text().strip(),
            "youtube_title": self.youtube_title_edit.text().strip(),
            "youtube_url": self.youtube_url_edit.text().strip(),
        }

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def _emit_save(self) -> None:
        self.save_requested.emit(self.file_path, self.metadata())

    def _open_youtube(self) -> None:
        url = self.youtube_url_edit.text().strip()
        if not url:
            return
        QDesktopServices.openUrl(QUrl(url))
