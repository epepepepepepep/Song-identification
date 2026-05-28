import json
import subprocess
from pathlib import Path
from typing import Any

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.json"
ACOUSTID_URL = "https://api.acoustid.org/v2/lookup"
MUSICBRAINZ_URL = "https://musicbrainz.org/ws/2/recording/{recording_id}"
REQUEST_TIMEOUT = 30


class IdentifierError(Exception):
    pass


def _load_acoustid_api_key() -> str:
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as fh:
            config = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise IdentifierError("קובץ config.json חסר או פגום") from exc

    api_key = str(config.get("acoustid_api_key", "")).strip()
    if not api_key:
        raise IdentifierError("לא נמצא acoustid_api_key בתוך config.json")
    return api_key


def _find_fpcalc() -> str:
    candidates = [
        PROJECT_ROOT / "fpcalc.exe",
        PROJECT_ROOT / "fpcalc",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return "fpcalc"


def create_fingerprint(file_path: str) -> tuple[int, str]:
    fpcalc_path = _find_fpcalc()
    try:
        completed = subprocess.run(
            [fpcalc_path, file_path],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise IdentifierError("נכשלה הפעלת fpcalc ליצירת fingerprint") from exc

    if completed.returncode != 0:
        error_text = completed.stderr.strip() or completed.stdout.strip() or "שגיאה לא ידועה"
        raise IdentifierError(f"fpcalc נכשל: {error_text}")

    duration = None
    fingerprint = ""
    for raw_line in completed.stdout.splitlines():
        if "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        key = key.strip().upper()
        value = value.strip()
        if key == "DURATION":
            try:
                duration = int(float(value))
            except ValueError:
                duration = None
        elif key == "FINGERPRINT":
            fingerprint = value

    if not duration or not fingerprint:
        raise IdentifierError("לא התקבל fingerprint תקין מהקובץ")

    return duration, fingerprint


def lookup_acoustid(fingerprint: str, duration: int) -> list[dict[str, Any]]:
    api_key = _load_acoustid_api_key()
    try:
        response = requests.get(
            ACOUSTID_URL,
            params={
                "client": api_key,
                "duration": duration,
                "fingerprint": fingerprint,
                "meta": "recordings",
                "format": "json",
            },
            timeout=REQUEST_TIMEOUT,
            verify=False,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise IdentifierError("שגיאת רשת בעת פנייה ל-AcoustID") from exc
    except ValueError as exc:
        raise IdentifierError("AcoustID החזיר תשובה שאינה JSON תקין") from exc

    if payload.get("status") != "ok":
        raise IdentifierError("AcoustID החזיר סטטוס שגוי")

    return payload.get("results", [])


def fetch_musicbrainz_metadata(recording_id: str) -> dict[str, str]:
    if not recording_id:
        return {}

    try:
        response = requests.get(
            MUSICBRAINZ_URL.format(recording_id=recording_id),
            params={"fmt": "json", "inc": "artists+releases+tags+media"},
            headers={
                "User-Agent": "SongIdentification/2.0 (https://github.com/epepepepepepep/Song-identification)"
            },
            timeout=REQUEST_TIMEOUT,
            verify=False,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise IdentifierError("שגיאת רשת בעת פנייה ל-MusicBrainz") from exc
    except ValueError as exc:
        raise IdentifierError("MusicBrainz החזיר תשובה שאינה JSON תקין") from exc

    recording = payload
    releases = recording.get("releases", [])
    first_release = releases[0] if releases else {}
    first_date = str(first_release.get("date") or "")

    tags = recording.get("tags", [])
    genre = tags[0].get("name", "") if tags else ""

    year = first_date[:4] if first_date else ""
    track = _extract_track_number(first_release, recording_id)

    return {
        "title": str(recording.get("title", "")),
        "artist": _join_artists(recording.get("artist-credit", [])),
        "album": str(first_release.get("title", "")),
        "year": year,
        "date": first_date,
        "genre": str(genre),
        "track": track,
        "tracknumber": track,
    }


def identify_song(file_path: str) -> dict[str, str]:
    duration, fingerprint = create_fingerprint(file_path)
    matches = lookup_acoustid(fingerprint, duration)
    if not matches:
        raise IdentifierError("לא נמצאו התאמות ב-AcoustID")

    best = max(matches, key=lambda item: float(item.get("score", 0) or 0))
    recordings = best.get("recordings", [])
    if not recordings:
        raise IdentifierError("לא נמצאה הקלטה מתאימה בתוצאת AcoustID")

    recording_id = str(recordings[0].get("id", ""))
    metadata = fetch_musicbrainz_metadata(recording_id)
    metadata["score"] = f"{float(best.get('score', 0) or 0):.2f}"
    return metadata


def _join_artists(artist_credit: list[Any]) -> str:
    parts: list[str] = []
    for item in artist_credit:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("artist", {}).get("name") or "")
        join_phrase = str(item.get("joinphrase") or "")
        if name:
            parts.append(name + join_phrase)
    return "".join(parts).strip()


def _extract_track_number(release: dict[str, Any], recording_id: str) -> str:
    media = release.get("media", [])
    for medium in media:
        for track in medium.get("tracks", []):
            rec = track.get("recording", {})
            if str(rec.get("id", "")) == recording_id:
                number = track.get("number") or track.get("position")
                if number:
                    return str(number)
    return ""
