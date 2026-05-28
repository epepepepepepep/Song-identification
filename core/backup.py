import shutil
from pathlib import Path


def backup_file(file_path: str) -> str:
    source = Path(file_path)
    backup_dir = source.parent / ".backup"
    backup_dir.mkdir(exist_ok=True)

    target = backup_dir / source.name
    i = 1
    while target.exists():
        target = backup_dir / f"{source.stem}_{i}{source.suffix}"
        i += 1

    shutil.copy2(source, target)
    return str(target)
