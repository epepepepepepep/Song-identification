from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from core.backup import backup_file
from core.logger import log_change
from core.tagger import read_tags, rename_file, write_tags
from gui.styles import DARK_STYLE
from gui.worker import ScanWorker


class MainWindow(QMainWindow):
    COLUMNS = [
        "שם קובץ נוכחי",
        "שם שיר מזוהה",
        "אמן מזוהה",
        "אלבום מזוהה",
        "שנה",
        "רמת ביטחון (%)",
        "סטטוס",
        "אישור",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("זיהוי ועדכון תגיות שירים")
        self.resize(1280, 760)
        self.setStyleSheet(DARK_STYLE)

        self.folder_path = ""
        self.worker: ScanWorker | None = None
        self.row_data: list[dict[str, Any]] = []

        self._build_ui()

    def _build_ui(self) -> None:
        self._build_toolbar()
        self._build_center()
        self._build_statusbar()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("כלים")
        toolbar.setMovable(False)

        self.btn_select_folder = QPushButton("בחר תיקייה")
        self.btn_scan = QPushButton("סרוק")
        self.btn_apply = QPushButton("החל שינויים")
        self.chk_backup = QCheckBox("גיבוי לפני שמירה")
        self.chk_backup.setChecked(True)

        self.btn_select_folder.clicked.connect(self.select_folder)
        self.btn_scan.clicked.connect(self.start_scan)
        self.btn_apply.clicked.connect(self.apply_changes)

        toolbar.addWidget(self.btn_select_folder)
        toolbar.addWidget(self.btn_scan)
        toolbar.addWidget(self.btn_apply)
        toolbar.addSeparator()
        toolbar.addWidget(self.chk_backup)

        self.addToolBar(toolbar)

    def _build_center(self) -> None:
        root = QWidget()
        root_layout = QHBoxLayout(root)

        splitter = QSplitter(Qt.Horizontal)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemSelectionChanged.connect(self.update_details_panel)
        self.table.horizontalHeader().setStretchLastSection(True)

        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        details_form = QFormLayout()

        self.detail_title = QLineEdit()
        self.detail_artist = QLineEdit()
        self.detail_album = QLineEdit()
        self.detail_track = QLineEdit()
        self.detail_date = QLineEdit()
        self.detail_genre = QLineEdit()

        details_form.addRow("שם שיר:", self.detail_title)
        details_form.addRow("אמן:", self.detail_artist)
        details_form.addRow("אלבום:", self.detail_album)
        details_form.addRow("מספר רצועה:", self.detail_track)
        details_form.addRow("שנה:", self.detail_date)
        details_form.addRow("ז'אנר:", self.detail_genre)

        self.btn_manual_save = QPushButton("שמור ידנית")
        self.btn_manual_save.clicked.connect(self.save_manual_edits)

        details_layout.addWidget(QLabel("פרטי שיר נבחר"))
        details_layout.addLayout(details_form)
        details_layout.addWidget(self.btn_manual_save)
        details_layout.addStretch()

        splitter.addWidget(self.table)
        splitter.addWidget(details_widget)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 2)

        root_layout.addWidget(splitter)
        self.setCentralWidget(root)

    def _build_statusbar(self) -> None:
        status_bar = QStatusBar()
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setValue(0)

        self.status_label = QLabel("מוכן")
        self.counter_label = QLabel("0 / 0")

        status_bar.addPermanentWidget(self.progress_bar, 1)
        status_bar.addPermanentWidget(self.status_label)
        status_bar.addPermanentWidget(self.counter_label)
        self.setStatusBar(status_bar)

    def select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "בחר תיקייה לסריקה")
        if not folder:
            return
        self.folder_path = folder
        self.status_label.setText(f"נבחרה תיקייה: {folder}")

    def start_scan(self) -> None:
        if not self.folder_path:
            QMessageBox.warning(self, "שגיאה", "יש לבחור תיקייה לפני תחילת סריקה")
            return

        self.table.setRowCount(0)
        self.row_data.clear()
        self.progress_bar.setValue(0)
        self.counter_label.setText("0 / 0")

        self.worker = ScanWorker(self.folder_path)
        self.worker.file_result.connect(self.add_result_row)
        self.worker.progress.connect(self.update_progress)
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished_scan.connect(self.on_scan_finished)
        self.worker.start()

    def add_result_row(self, data: dict[str, Any]) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)

        self.row_data.append(data)
        confidence_percent = f"{data.get('confidence', 0.0) * 100:.1f}"

        values = [
            data.get("file_name", ""),
            data.get("title", ""),
            data.get("artist", ""),
            data.get("album", ""),
            data.get("date", ""),
            confidence_percent,
            data.get("status", "❌ לא זוהה"),
        ]

        for col, value in enumerate(values):
            self.table.setItem(row, col, QTableWidgetItem(str(value)))

        approve = QTableWidgetItem()
        approve.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        approve.setCheckState(Qt.Checked if data.get("approved") else Qt.Unchecked)
        self.table.setItem(row, 7, approve)

    def update_progress(self, processed: int, total: int) -> None:
        self.progress_bar.setMaximum(max(total, 1))
        self.progress_bar.setValue(processed)
        self.counter_label.setText(f"{processed} / {total}")

    def on_scan_finished(self) -> None:
        self.status_label.setText("הסריקה הסתיימה")

    def update_details_panel(self) -> None:
        row = self._selected_row()
        if row is None or row >= len(self.row_data):
            return

        data = self.row_data[row]
        self.detail_title.setText(data.get("title", ""))
        self.detail_artist.setText(data.get("artist", ""))
        self.detail_album.setText(data.get("album", ""))
        self.detail_track.setText(data.get("tracknumber", ""))
        self.detail_date.setText(data.get("date", ""))
        self.detail_genre.setText(data.get("genre", ""))

    def save_manual_edits(self) -> None:
        row = self._selected_row()
        if row is None or row >= len(self.row_data):
            QMessageBox.warning(self, "שגיאה", "יש לבחור שורה בטבלה")
            return

        data = self.row_data[row]
        data.update(
            {
                "title": self.detail_title.text().strip(),
                "artist": self.detail_artist.text().strip(),
                "album": self.detail_album.text().strip(),
                "tracknumber": self.detail_track.text().strip(),
                "date": self.detail_date.text().strip(),
                "genre": self.detail_genre.text().strip(),
            }
        )

        self.table.item(row, 1).setText(data["title"])
        self.table.item(row, 2).setText(data["artist"])
        self.table.item(row, 3).setText(data["album"])
        self.table.item(row, 4).setText(data["date"])
        self.status_label.setText("השינויים הידניים נשמרו בטבלה")

    def apply_changes(self) -> None:
        if not self.row_data:
            QMessageBox.information(self, "מידע", "אין נתונים ליישום")
            return

        applied = 0
        failures: list[str] = []
        for row, data in enumerate(self.row_data):
            approve_item = self.table.item(row, 7)
            approved = approve_item is not None and approve_item.checkState() == Qt.Checked
            if not approved:
                continue

            file_path = data.get("file_path", "")
            if not file_path:
                continue

            try:
                before = read_tags(file_path)
                if self.chk_backup.isChecked():
                    try:
                        backup_path = backup_file(file_path)
                    except Exception as exc:  # noqa: BLE001
                        raise RuntimeError(f"שגיאה ביצירת גיבוי: {exc}") from exc
                    log_change(f"נוצר גיבוי: {backup_path}")

                try:
                    write_tags(file_path, data)
                except Exception as exc:  # noqa: BLE001
                    raise RuntimeError(f"שגיאה בכתיבת תגיות: {exc}") from exc

                try:
                    renamed = rename_file(file_path, data.get("artist", ""), data.get("title", ""))
                except Exception as exc:  # noqa: BLE001
                    raise RuntimeError(f"שגיאה בשינוי שם קובץ: {exc}") from exc

                after = read_tags(renamed)

                data["file_path"] = renamed
                data["file_name"] = Path(renamed).name
                self.table.item(row, 0).setText(data["file_name"])
                log_change(
                    f"עודכן קובץ: {file_path} -> {renamed} | לפני: {before} | אחרי: {after}"
                )
                applied += 1
            except Exception as exc:  # noqa: BLE001
                log_change(f"שגיאה בעדכון הקובץ {file_path}: {exc}")
                failures.append(f"{Path(file_path).name}: {exc}")

        if failures:
            QMessageBox.warning(
                self,
                "חלק מהעדכונים נכשלו",
                "הפעולה הושלמה חלקית.\n"
                f"עודכנו {applied} קבצים.\n"
                f"נכשלו {len(failures)} קבצים:\n- " + "\n- ".join(failures[:8]),
            )
            self.status_label.setText("הפעולה הושלמה חלקית")
            return

        QMessageBox.information(self, "סיום", f"הפעולה הושלמה. עודכנו {applied} קבצים")

    def _selected_row(self) -> int | None:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        return indexes[0].row()
