"""Download ten public CSV parts from a fixed source revision and verify hashes."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent


def main():
    manifest = json.loads((ROOT / "data/source.json").read_text())
    destination = ROOT / "data/raw"
    destination.mkdir(parents=True, exist_ok=True)
    for part in manifest["parts"]:
        path = destination / part["file"]
        if path.exists():
            payload = path.read_bytes()
        else:
            url = f'{manifest["raw_base_url"]}/{part["file"]}'
            with urlopen(url, timeout=30) as response:
                payload = response.read()
        if hashlib.sha256(payload).hexdigest() != part["sha256"]:
            raise ValueError(f"Hash mismatch: {path}; inspect/remove the local file before retrying")
        path.write_bytes(payload)
    print("Verified all ten parts (10,000 source samples).")


if __name__ == "__main__":
    main()
