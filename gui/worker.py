from pathlib import Path

from PySide6.QtCore import QThread, Signal

from core.identifier import (
    IdentifierError,
    create_fingerprint,
    fetch_musicbrainz_metadata,
    lookup_acoustid,
)
from core.scanner import scan_folder


class ScanWorker(QThread):
    file_result = Signal(dict)
    progress = Signal(int, int)
    status = Signal(str)
    finished_scan = Signal()

    def __init__(self, folder_path: str):
        super().__init__()
        self.folder_path = folder_path

    def run(self) -> None:
        files = scan_folder(self.folder_path)
        total = len(files)
        if total == 0:
            self.status.emit("לא נמצאו קבצי אודיו בתיקייה")
            self.finished_scan.emit()
            return

        for index, file_path in enumerate(files, start=1):
            self.status.emit(f"מעבד: {Path(file_path).name}")
            self.file_result.emit(self._identify_file(file_path))
            self.progress.emit(index, total)

        self.status.emit("הסריקה הסתיימה")
        self.finished_scan.emit()

    def _identify_file(self, file_path: str) -> dict:
        result = {
            "file_path": file_path,
            "file_name": Path(file_path).name,
            "title": "",
            "artist": "",
            "album": "",
            "date": "",
            "tracknumber": "",
            "genre": "",
            "confidence": 0.0,
            "status": "❌ לא זוהה",
            "approved": False,
            "error": "",
        }

        try:
            duration, fingerprint = create_fingerprint(file_path)
        except IdentifierError as exc:
            result["error"] = f"שגיאה בשלב יצירת fingerprint: {exc}"
            return result

        try:
            matches = lookup_acoustid(fingerprint, duration)
        except IdentifierError as exc:
            result["error"] = f"שגיאה בשלב חיפוש ב-AcoustID: {exc}"
            return result

        if not matches:
            result["error"] = "לא נמצאו התאמות"
            return result

        best = max(matches, key=lambda item: item.get("score", 0))
        score = float(best.get("score", 0.0))
        recordings = best.get("recordings", [])
        if not recordings:
            result["error"] = "אין הקלטה מתאימה"
            return result

        recording = recordings[0]
        recording_id = recording.get("id", "")
        try:
            metadata = fetch_musicbrainz_metadata(recording_id) if recording_id else {}
        except IdentifierError as exc:
            result["error"] = f"שגיאה בשלב משיכת נתונים מ-MusicBrainz: {exc}"
            return result

        result.update(
            {
                "title": metadata.get("title") or recording.get("title", ""),
                "artist": metadata.get("artist", ""),
                "album": metadata.get("album", ""),
                "date": metadata.get("date", ""),
                "tracknumber": metadata.get("tracknumber", ""),
                "genre": metadata.get("genre", ""),
                "confidence": score,
                "status": self._status_from_score(score),
                "approved": score >= 0.85,
            }
        )

        return result

    @staticmethod
    def _status_from_score(score: float) -> str:
        if score >= 0.85:
            return "✅ אושר"
        if score >= 0.5:
            return "⚠️ דורש בדיקה"
        return "❌ לא זוהה"
