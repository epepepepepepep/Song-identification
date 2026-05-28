"""
סקריפט בדיקה — מריץ כל שלב בנפרד ומדפיס את התוצאה
הרץ: py test.py
"""
import os
import sys
import json
from pathlib import Path

# ── 1. נתיב fpcalc ──────────────────────────────────────────────────────────
FPCALC = str(Path(__file__).parent / "fpcalc.exe")
os.environ["FPCALC"] = FPCALC
print(f"[1] נתיב fpcalc: {FPCALC}")
print(f"    קיים: {Path(FPCALC).exists()}")

# ── 2. בחר קובץ MP3 לבדיקה ─────────────────────────────────────────────────
if len(sys.argv) > 1:
    TEST_FILE = sys.argv[1]
else:
    # חפש קובץ mp3 ראשון בתיקיית המוזיקה
    music_dir = Path.home() / "Music"
    mp3_files = list(music_dir.rglob("*.mp3"))
    if not mp3_files:
        print("[!] לא נמצא קובץ MP3 — הרץ: py test.py 'נתיב\\לשיר.mp3'")
        sys.exit(1)
    TEST_FILE = str(mp3_files[0])

print(f"\n[2] קובץ בדיקה: {TEST_FILE}")
print(f"    קיים: {Path(TEST_FILE).exists()}")

# ── 3. יצירת fingerprint ────────────────────────────────────────────────────
print("\n[3] יוצר fingerprint...")
try:
    import acoustid
    duration, fingerprint = acoustid.fingerprint_file(TEST_FILE)
    print(f"    ✅ הצלחה! Duration={duration}, Fingerprint={fingerprint[:40]}...")
except Exception as e:
    print(f"    ❌ שגיאה: {e}")
    sys.exit(1)

# ── 4. שליחה ל-AcoustID ─────────────────────────────────────────────────────
print("\n[4] שולח ל-AcoustID...")
try:
    import requests
    config = json.loads((Path(__file__).parent / "config.json").read_text(encoding="utf-8"))
    api_key = config.get("acoustid_api_key", "")
    print(f"    API Key: {api_key[:4]}****")

    res = requests.get(
        "https://api.acoustid.org/v2/lookup",
        params={
            "client": api_key,
            "duration": duration,
            "fingerprint": fingerprint,
            "meta": "recordings",
            "format": "json",
        },
        timeout=30,
    )
    data = res.json()
    print(f"    Status: {data.get('status')}")
    results = data.get("results", [])
    print(f"    תוצאות: {len(results)}")
    if results:
        best = max(results, key=lambda x: x.get("score", 0))
        print(f"    ✅ התאמה הכי טובה: score={best.get('score')}")
        recordings = best.get("recordings", [])
        if recordings:
            print(f"    שם שיר: {recordings[0].get('title', 'לא ידוע')}")
        else:
            print("    ⚠️ אין recordings בתוצאה")
    else:
        print("    ❌ לא נמצאו תוצאות")
except Exception as e:
    print(f"    ❌ שגיאה: {e}")
    sys.exit(1)

print("\n✅ הבדיקה הסתיימה!")
