"""Download a small, provenance-tracked CWRU subset from the official host."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parent
FILES = {
    97: ("healthy", 0), 98: ("healthy", 1), 99: ("healthy", 2),
    105: ("inner", 0), 106: ("inner", 1), 107: ("inner", 2),
    130: ("outer", 0), 131: ("outer", 1), 132: ("outer", 2),
    118: ("ball", 0), 119: ("ball", 1), 120: ("ball", 2),
}


def download(item):
    number, (label, load) = item
    path = ROOT / "data" / f"{number}.mat"
    url = f"https://engineering.case.edu/sites/default/files/{number}.mat"
    if not path.exists():
        with urllib.request.urlopen(url, timeout=60) as response:
            content = response.read()
        if not content.startswith(b"MATLAB"):
            raise ValueError(f"Not a MATLAB file: {url}")
        path.write_bytes(content)
    content = path.read_bytes()
    return {
        "id": number, "label": label, "load_hp": load,
        "split": ["anchor_train", "development", "locked_test"][load],
        "url": url, "file": str(path), "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "permission": "public download; redistribution/commercial license not established",
        "independence": "different load recordings; NOT confirmed independent bearings",
        "fault_diameter_in": None if label == "healthy" else 0.007,
    }


if __name__ == "__main__":
    (ROOT / "data").mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        manifest = sorted(pool.map(download, FILES.items()), key=lambda x: x["id"])
    (ROOT / "data_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    for entry in manifest:
        print(entry["id"], entry["label"], entry["split"], entry["bytes"], entry["sha256"][:12])