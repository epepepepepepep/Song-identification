from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.identifier import IdentifierError, identify_song
from core.metadata_writer import MetadataWriteError, build_metadata_preview, write_mp3_metadata
from ui.result_widget import ResultWidget


class IdentifyWorker(QThread):
    progress = Signal(int, int)
    song_ready = Signal(str, dict)
    song_error = Signal(str, str)

    def __init__(self, files: list[str]):
        super().__init__()
        self.files = files

    def run(self) -> None:
        total = len(self.files)
        for index, file_path in enumerate(self.files, start=1):
            try:
                metadata = identify_song(file_path)
                self.song_ready.emit(file_path, metadata)
            except IdentifierError as exc:
                self.song_error.emit(file_path, str(exc))
            self.progress.emit(index, total)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("זיהוי והוספת מטא-דאטה לשירים")
        self.resize(1200, 760)
        self.setLayoutDirection(Qt.RightToLeft)

        self.selected_files: list[str] = []
        self.result_widgets: dict[str, ResultWidget] = {}
        self.worker: IdentifyWorker | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)

        controls = QHBoxLayout()
        self.select_button = QPushButton("בחר קבצים")
        self.identify_button = QPushButton("זהה והוסף מטא-דאטה")
        self.save_all_button = QPushButton("שמור הכל")
        self.select_button.clicked.connect(self.select_files)
        self.identify_button.clicked.connect(self.identify_selected)
        self.save_all_button.clicked.connect(self.save_all)
        controls.addWidget(self.select_button)
        controls.addWidget(self.identify_button)
        controls.addWidget(self.save_all_button)
        controls.addStretch()

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.status_label = QLabel("בחר קבצים כדי להתחיל")

        splitter = QSplitter(Qt.Horizontal)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["קובץ", "סטטוס"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)

        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setWidget(self.results_container)

        splitter.addWidget(self.table)
        splitter.addWidget(self.results_scroll)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        root_layout.addLayout(controls)
        root_layout.addWidget(self.progress)
        root_layout.addWidget(self.status_label)
        root_layout.addWidget(splitter)
        self.setCentralWidget(root)

    def select_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "בחר קבצי אודיו",
            "",
            "Audio Files (*.mp3 *.flac *.wav *.ogg *.m4a);;All Files (*)",
        )
        if not files:
            return

        self.selected_files = files
        self.table.setRowCount(0)
        self._clear_results_widgets()

        for file_path in files:
            row = self.table.rowCount()
            self.table.insertRow(row)
            file_item = QTableWidgetItem(Path(file_path).name)
            file_item.setData(Qt.ItemDataRole.UserRole, file_path)
            self.table.setItem(row, 0, file_item)
            self.table.setItem(row, 1, QTableWidgetItem("ממתין לזיהוי"))

        self.progress.setMaximum(len(files))
        self.progress.setValue(0)
        self.status_label.setText(f"נבחרו {len(files)} קבצים")

    def identify_selected(self) -> None:
        if not self.selected_files:
            QMessageBox.warning(self, "שגיאה", "יש לבחור קבצים לפני זיהוי")
            return

        self.progress.setMaximum(len(self.selected_files))
        self.progress.setValue(0)
        self.identify_button.setEnabled(False)
        self.status_label.setText("מזהה שירים, נא להמתין...")

        self.worker = IdentifyWorker(self.selected_files)
        self.worker.song_ready.connect(self._on_song_ready)
        self.worker.song_error.connect(self._on_song_error)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_identify_finished)
        self.worker.start()

    def _on_song_ready(self, file_path: str, metadata: dict) -> None:
        row = self._row_for_file(file_path)
        if row is not None:
            self.table.item(row, 1).setText("זוהה בהצלחה")

        widget = ResultWidget(file_path, metadata)
        widget.save_requested.connect(self.save_one)
        self.result_widgets[file_path] = widget
        self.results_layout.addWidget(widget)

    def _on_song_error(self, file_path: str, error_text: str) -> None:
        row = self._row_for_file(file_path)
        if row is not None:
            self.table.item(row, 1).setText(f"שגיאה: {error_text}")

    def _on_progress(self, current: int, total: int) -> None:
        self.progress.setMaximum(max(total, 1))
        self.progress.setValue(current)

    def _on_identify_finished(self) -> None:
        self.identify_button.setEnabled(True)
        self.status_label.setText("הזיהוי הסתיים")

    def save_one(self, file_path: str, metadata: dict) -> None:
        preview = build_metadata_preview(file_path, metadata)
        answer = QMessageBox.question(
            self,
            "תצוגה מקדימה לפני שמירה",
            f"האם לשמור את המטא-דאטה הבא?\n\n{preview}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            write_mp3_metadata(file_path, metadata)
            self._set_widget_status(file_path, "נשמר בהצלחה")
            row = self._row_for_file(file_path)
            if row is not None:
                self.table.item(row, 1).setText("נשמר")
        except MetadataWriteError as exc:
            self._set_widget_status(file_path, f"שגיאה: {exc}")
            QMessageBox.warning(self, "שגיאה בשמירה", str(exc))

    def save_all(self) -> None:
        if not self.result_widgets:
            QMessageBox.information(self, "מידע", "אין תוצאות לשמירה")
            return

        preview_text = "\n\n".join(
            build_metadata_preview(file_path, widget.metadata())
            for file_path, widget in self.result_widgets.items()
        )
        answer = QMessageBox.question(
            self,
            "תצוגה מקדימה לפני שמירה",
            f"האם לשמור את כל המטא-דאטה?\n\n{preview_text}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        saved = 0
        failed = []
        for file_path, widget in self.result_widgets.items():
            try:
                write_mp3_metadata(file_path, widget.metadata())
                widget.set_status("נשמר בהצלחה")
                saved += 1
                row = self._row_for_file(file_path)
                if row is not None:
                    self.table.item(row, 1).setText("נשמר")
            except MetadataWriteError as exc:
                widget.set_status(f"שגיאה: {exc}")
                failed.append(f"{Path(file_path).name}: {exc}")
                row = self._row_for_file(file_path)
                if row is not None:
                    self.table.item(row, 1).setText("נכשל בשמירה")

        if failed:
            QMessageBox.warning(
                self,
                "שמירה חלקית",
                f"נשמרו {saved} קבצים.\nנכשלו {len(failed)} קבצים:\n- " + "\n- ".join(failed),
            )
        else:
            QMessageBox.information(self, "הצלחה", f"נשמרו {saved} קבצים בהצלחה")

    def _row_for_file(self, file_path: str) -> int | None:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == file_path:
                return row
        return None

    def _clear_results_widgets(self) -> None:
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.result_widgets.clear()

    def _set_widget_status(self, file_path: str, status: str) -> None:
        widget = self.result_widgets.get(file_path)
        if widget:
            widget.set_status(status)
