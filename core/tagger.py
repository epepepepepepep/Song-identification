import re
from pathlib import Path
from typing import Any

from mutagen import File


def read_tags(file_path: str) -> dict[str, str]:
    audio = File(file_path, easy=True)
    if audio is None or audio.tags is None:
        return {}

    def _first(key: str) -> str:
        value = audio.tags.get(key, [""])
        if isinstance(value, list):
            return str(value[0]) if value else ""
        return str(value)

    return {
        "title": _first("title"),
        "artist": _first("artist"),
        "album": _first("album"),
        "tracknumber": _first("tracknumber"),
        "date": _first("date"),
        "genre": _first("genre"),
    }


def write_tags(file_path: str, metadata: dict[str, Any]) -> None:
    audio = File(file_path, easy=True)
    if audio is None:
        raise ValueError("סוג הקובץ אינו נתמך")

    if audio.tags is None:
        audio.add_tags()

    for key in ("title", "artist", "album", "tracknumber", "date", "genre"):
        value = str(metadata.get(key, "")).strip()
        if value:
            audio.tags[key] = [value]

    audio.save()


def rename_file(file_path: str, artist: str, title: str) -> str:
    source = Path(file_path)
    clean_artist = _safe_name(artist or "אמן לא ידוע")
    clean_title = _safe_name(title or "שם לא ידוע")
    target = source.with_name(f"{clean_artist} - {clean_title}{source.suffix}")

    if source.resolve() == target.resolve():
        return str(source)

    i = 1
    while target.exists():
        target = source.with_name(f"{clean_artist} - {clean_title} ({i}){source.suffix}")
        i += 1

    source.rename(target)
    return str(target)


def _safe_name(text: str) -> str:
    return re.sub(r"[\\/:*?\"<>|]", "_", text).strip() or "לא_ידוע"
