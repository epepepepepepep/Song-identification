import json
import os
import ssl
import urllib.request
from pathlib import Path
from typing import Any

import acoustid
import musicbrainzngs
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.json"
ACOUSTID_TIMEOUT = 25

# חפש fpcalc בתיקיית הפרויקט קודם, ואז ב-PATH
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_FPCALC_CANDIDATES = [
    _PROJECT_ROOT / "fpcalc.exe",   # Windows בתיקיית הפרויקט
    _PROJECT_ROOT / "fpcalc",       # Linux/macOS בתיקיית הפרויקט
]


def _find_fpcalc() -> str:
    """מאתר את fpcalc — קודם בתיקיית הפרויקט, אחר כך ב-PATH."""
    for candidate in _FPCALC_CANDIDATES:
        if candidate.exists():
            return str(candidate)
    return "fpcalc"


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
    fpcalc_path = _find_fpcalc()
    os.environ["FPCALC"] = fpcalc_path
    try:
        duration, fingerprint = acoustid.fingerprint_file(file_path, force_fpcalc=True)
        return duration, fingerprint
    except TypeError:
        try:
            duration, fingerprint = acoustid.fingerprint_file(file_path)
            return duration, fingerprint
        except (OSError, acoustid.FingerprintGenerationError) as exc:
            file_name = Path(file_path).name
            raise IdentifierError(f"נכשל יצירת fingerprint עבור הקובץ: {file_name}") from exc
    except (OSError, acoustid.FingerprintGenerationError) as exc:
        file_name = Path(file_path).name
        raise IdentifierError(f"נכשל יצירת fingerprint עבור הקובץ: {file_name}") from exc


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
            timeout=ACOUSTID_TIMEOUT,
            verify=False,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise IdentifierError("שגיאת רשת בעת פנייה ל-AcoustID") from exc

    if payload.get("status") != "ok":
        raise IdentifierError("AcoustID החזיר תשובה לא תקינה")

    return payload.get("results", [])


def fetch_musicbrainz_metadata(recording_id: str) -> dict[str, str]:
    # עקוף בדיקת SSL עבור MusicBrainz
    _orig_create_default_context = ssl.create_default_context

    def _no_verify_context(*args, **kwargs):
        ctx = _orig_create_default_context(*args, **kwargs)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    ssl.create_default_context = _no_verify_context
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
    except (
        musicbrainzngs.WebServiceError,
        musicbrainzngs.ResponseError,
        musicbrainzngs.NetworkError,
    ) as exc:
        raise IdentifierError("שגיאה במשיכת מטא-דאטה מ-MusicBrainz") from exc
    finally:
        ssl.create_default_context = _orig_create_default_context

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
