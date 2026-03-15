
import zipfile
import time
from pathlib import Path

def archive_project(state):
    base = Path.cwd().name
    ts = int(time.time())

    archive_dir = Path("archives")
    archive_dir.mkdir(exist_ok=True)

    zip_path = archive_dir / f"{base}_{ts}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in Path(".").rglob("*"):
            if "__pycache__" in str(f):
                continue
            if "archives" in str(f):
                continue
            if f.is_file():
                z.write(f)

    return str(zip_path)
