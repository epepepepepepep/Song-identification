# -*- coding: utf-8 -*-
import os
import sys
import json
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

FPCALC = str(Path(__file__).parent / "fpcalc.exe")
os.environ["FPCALC"] = FPCALC
print(f"[1] fpcalc: {FPCALC}")
print(f"    exists: {Path(FPCALC).exists()}")

if len(sys.argv) > 1:
    TEST_FILE = sys.argv[1]
else:
    music_dir = Path.home() / "Music"
    mp3_files = list(music_dir.rglob("*.mp3"))
    if not mp3_files:
        print("[!] No MP3 found - run: py test.py path\\to\\song.mp3")
        sys.exit(1)
    TEST_FILE = str(mp3_files[0])

print(f"\n[2] Test file: {TEST_FILE}")
print(f"    exists: {Path(TEST_FILE).exists()}")

print("\n[3] Creating fingerprint...")
try:
    import acoustid
    duration, fingerprint = acoustid.fingerprint_file(TEST_FILE)
    print(f"    OK! Duration={duration}")
    print(f"    Fingerprint={str(fingerprint)[:40]}...")
except Exception as e:
    print(f"    ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[4] Sending to AcoustID...")
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
    print(f"    Results count: {len(results)}")
    if results:
        best = max(results, key=lambda x: x.get("score", 0))
        print(f"    Best score: {best.get('score')}")
        recordings = best.get("recordings", [])
        if recordings:
            print(f"    Title: {recordings[0].get('title', 'unknown')}")
        else:
            print("    WARNING: no recordings in result")
    else:
        print("    ERROR: no results found")
        print(f"    Full response: {data}")
except Exception as e:
    print(f"    ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nDone!")
