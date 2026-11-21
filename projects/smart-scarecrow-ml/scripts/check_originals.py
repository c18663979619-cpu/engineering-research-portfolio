"""Verify that all 29 pre-existing files remain byte-for-byte unchanged."""
import hashlib
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
inventory = root / "backups/pre_ml_20261121/inventory.json"
if not inventory.exists():
    sys.exit("Local backup inventory not present; this check applies to the original Mac checkout only")
records = json.loads(inventory.read_text())
changed = []
for r in records:
    path = root / r["path"]
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != r["sha256"]:
        changed.append(r["path"])
print(json.dumps({"checked_original_files": len(records), "changed_or_missing": changed}, indent=2))
sys.exit(bool(changed))
