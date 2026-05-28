from pathlib import Path
from typing import Any

from mutagen.id3 import TALB, TCON, TDRC, TIT2, TPE1, TRCK, ID3, ID3NoHeaderError


class MetadataWriteError(Exception):
    pass


def normalize_metadata(metadata: dict[str, Any]) -> dict[str, str]:
    return {
        "title": str(metadata.get("title", "")).strip(),
        "artist": str(metadata.get("artist", "")).strip(),
        "album": str(metadata.get("album", "")).strip(),
        "year": str(metadata.get("year", "")).strip(),
        "genre": str(metadata.get("genre", "")).strip(),
        "track": str(metadata.get("track", "")).strip(),
    }


def build_metadata_preview(file_path: str, metadata: dict[str, Any]) -> str:
    clean = normalize_metadata(metadata)
    return "\n".join(
        [
            f"קובץ: {Path(file_path).name}",
            f"שם שיר (TIT2): {clean['title']}",
            f"אמן (TPE1): {clean['artist']}",
            f"אלבום (TALB): {clean['album']}",
            f"שנה (TDRC): {clean['year']}",
            f"ז'אנר (TCON): {clean['genre']}",
            f"מספר רצועה (TRCK): {clean['track']}",
        ]
    )


def write_mp3_metadata(file_path: str, metadata: dict[str, Any]) -> None:
    path = Path(file_path)
    if path.suffix.lower() != ".mp3":
        raise MetadataWriteError("ניתן לשמור מטא-דאטה רק לקבצי MP3")

    clean = normalize_metadata(metadata)

    try:
        try:
            tags = ID3(file_path)
        except ID3NoHeaderError:
            tags = ID3()

        tags.delall("TIT2")
        tags.delall("TPE1")
        tags.delall("TALB")
        tags.delall("TDRC")
        tags.delall("TCON")
        tags.delall("TRCK")

        if clean["title"]:
            tags.add(TIT2(encoding=3, text=clean["title"]))
        if clean["artist"]:
            tags.add(TPE1(encoding=3, text=clean["artist"]))
        if clean["album"]:
            tags.add(TALB(encoding=3, text=clean["album"]))
        if clean["year"]:
            tags.add(TDRC(encoding=3, text=clean["year"]))
        if clean["genre"]:
            tags.add(TCON(encoding=3, text=clean["genre"]))
        if clean["track"]:
            tags.add(TRCK(encoding=3, text=clean["track"]))

        tags.save(file_path, v2_version=3)
    except Exception as exc:  # noqa: BLE001
        raise MetadataWriteError(f"נכשלה כתיבת מטא-דאטה: {exc}") from exc
