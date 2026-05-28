from pathlib import Path


SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".m4a", ".ogg", ".wav"}


def scan_folder(folder_path: str) -> list[str]:
    root = Path(folder_path)
    if not root.exists() or not root.is_dir():
        return []

    files: list[str] = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(str(path))
    return sorted(files)
