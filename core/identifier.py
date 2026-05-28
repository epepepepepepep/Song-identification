import json
from pathlib import Path
from typing import Any

import acoustid
import musicbrainzngs
import requests


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.json"


class IdentifierError(Exception):
    pass


def _load_acoustid_key() -> str:
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise IdentifierError("קובץ config.json חסר או פגום") from exc

    key = data.get("acoustid_api_key", "").strip()
    if not key:
        raise IdentifierError("לא הוגדר מפתח AcoustID")
    return key


def create_fingerprint(file_path: str) -> tuple[int, str]:
    try:
        duration, fingerprint = acoustid.fingerprint_file(file_path)
        return duration, fingerprint
    except Exception as exc:  # noqa: BLE001
        raise IdentifierError(f"נכשל יצירת fingerprint עבור הקובץ: {file_path}") from exc


def lookup_acoustid(fingerprint: str, duration: int) -> list[dict[str, Any]]:
    api_key = _load_acoustid_key()
    try:
        response = requests.get(
            "https://api.acoustid.org/v2/lookup",
            params={
                "client": api_key,
                "duration": duration,
                "fingerprint": fingerprint,
                "meta": "recordings",
                "format": "json",
            },
            timeout=25,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise IdentifierError("שגיאת רשת בעת פנייה ל-AcoustID") from exc

    if payload.get("status") != "ok":
        raise IdentifierError("AcoustID החזיר תשובה לא תקינה")

    return payload.get("results", [])


def fetch_musicbrainz_metadata(recording_id: str) -> dict[str, str]:
    try:
        musicbrainzngs.set_useragent(
            "song-identification",
            "1.0.0",
            "https://github.com/epepepepepepep/Song-identification",
        )
        data = musicbrainzngs.get_recording_by_id(
            recording_id,
            includes=["artists", "releases", "tags"],
        )
    except Exception as exc:  # noqa: BLE001
        raise IdentifierError("שגיאה במשיכת מטא-דאטה מ-MusicBrainz") from exc

    recording = data.get("recording", {})
    artists = recording.get("artist-credit", [])
    artist_names = [
        part.get("artist", {}).get("name", "")
        for part in artists
        if isinstance(part, dict) and part.get("artist")
    ]

    releases = recording.get("release-list", [])
    first_release = releases[0] if releases else {}

    tags = recording.get("tag-list", [])
    genre = tags[0].get("name", "") if tags else ""

    return {
        "title": recording.get("title", ""),
        "artist": ", ".join(filter(None, artist_names)),
        "album": first_release.get("title", ""),
        "tracknumber": "",
        "date": first_release.get("date", ""),
        "genre": genre,
    }
