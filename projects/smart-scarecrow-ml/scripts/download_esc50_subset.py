"""Download a fixed, attributable real-audio benchmark; never invent samples.

Run from the project root with .venv/bin/python scripts/download_esc50_subset.py.
Only downloaded dataset audio is written; original experiments are untouched.
"""
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import io
import json
from pathlib import Path
import random
import re
import ssl
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scarecrow.io import write_csv, write_json

COMMIT = "33c8ce9eb2cf0b1c2f8bcf322eb349b6be34dbb6"
BASE = f"https://raw.githubusercontent.com/karolpiczak/ESC-50/{COMMIT}/"
NEGATIVES = ["rain", "wind", "crickets", "engine", "vacuum_cleaner", "footsteps", "clapping", "helicopter"]
BIRDS = ["chirping_birds", "crow"]


def fetch(url):
    # Use the Mac/system CA store when the python.org Python has no CA symlink.
    context = ssl.create_default_context(cafile="/etc/ssl/cert.pem" if Path("/etc/ssl/cert.pem").exists() else None)
    with urllib.request.urlopen(url, timeout=60, context=context) as response:
        return response.read()


def main():
    destination = ROOT / "data/external/esc50_subset"
    manifest = ROOT / "data/manifest_esc50.csv"
    existing_manifest = list(csv.DictReader(manifest.open())) if manifest.exists() else None
    destination.mkdir(parents=True, exist_ok=True)
    attribution_dir = ROOT / "docs/third_party/esc50"
    attribution_dir.mkdir(parents=True, exist_ok=True)
    metadata = fetch(BASE + "meta/esc50.csv")
    license_bytes = fetch(BASE + "LICENSE")
    licenses = license_bytes.decode("utf-8")
    if "Attribution-NonCommercial" not in licenses:
        raise ValueError("Unexpected upstream license; manual review needed")
    for name, content in [("LICENSE.upstream.txt", license_bytes), ("metadata.upstream.csv", metadata)]:
        p = attribution_dir / name
        if p.exists():
            if p.read_bytes() != content:
                raise ValueError("Upstream snapshot mismatch")
        else:
            with p.open("xb") as f:
                f.write(content)
    all_rows = list(csv.DictReader(io.StringIO(metadata.decode("utf-8"))))
    for r in all_rows:
        key = "-".join(r["filename"].split("-")[:3]) + ".ogg"
        lines = [line for line in licenses.splitlines() if line.startswith(f"- [{key}]")]
        r["attribution"] = lines[0] if len(lines) == 1 else ""
    rng = random.Random(42)
    selected = [r for r in all_rows if r["category"] in BIRDS]
    for category in NEGATIVES:
        for fold in range(1, 6):
            candidates = sorted([r for r in all_rows if r["category"] == category and r["fold"] == str(fold)
                                 and not re.search(r"bird|crow|rooster", r["attribution"], flags=re.I)], key=lambda r: r["filename"])
            if len(candidates) < 2:
                raise ValueError(f"Not enough title-screened negatives: {category} fold {fold}")
            selected.extend(rng.sample(candidates, 2))
    selected.sort(key=lambda r: r["filename"])
    if len(selected) != 160 or any(not r["attribution"] for r in selected):
        raise ValueError("Selection or per-file attribution is incomplete")

    def download(row):
        path = destination / row["filename"]
        if path.exists():
            data = path.read_bytes()
        else:
            data = fetch(BASE + "audio/" + row["filename"])
            if not data.startswith(b"RIFF") or data[8:12] != b"WAVE":
                raise ValueError("Download is not a WAV")
            with path.open("xb") as f:
                f.write(data)
        return row["filename"], hashlib.sha256(data).hexdigest(), len(data)

    downloads = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(download, row) for row in selected]
        for i, future in enumerate(as_completed(futures), 1):
            filename, checksum, size = future.result()
            downloads[filename] = {"sha256": checksum, "bytes": size}
            if i % 20 == 0:
                print(f"Downloaded/verified {i}/{len(selected)} real WAV files", flush=True)
    rows = []
    record_path = attribution_dir / "subset_download.json"
    if record_path.exists():
        expected = json.loads(record_path.read_text())
        if expected["commit"] != COMMIT or expected["files"] != downloads:
            raise ValueError("Audio hashes differ from the saved pinned subset; no records overwritten")
    for r in selected:
        match = re.search(r"\((https?://[^)]+)\) by (.*) \[([^]]+)\]", r["attribution"])
        if not match:
            raise ValueError(f"Cannot parse attribution: {r['filename']}")
        url, creator, source_license = match.groups()
        relative = str((destination / r["filename"]).relative_to(ROOT))
        rows.append({"clip_id": "esc50_" + Path(r["filename"]).stem, "audio_path": relative,
                     "label": "bird" if r["category"] in BIRDS else "non_bird",
                     "source_recording": "FREESOUND_" + r["src_file"], "source_group": "FREESOUND_" + r["src_file"],
                     "original_path": relative, "start_sec": 0, "end_sec": 5,
                     "label_verified": "yes", "license_status": "verified", "source_url": url,
                     "creator": creator, "license_url": "https://creativecommons.org/licenses/by-nc/3.0/",
                     "redistribution_allowed": "not_automatically_published", "dataset_fold": r["fold"],
                     "category": r["category"], "annotation_level": "weak_clip_label",
                     "source_license_tag": source_license,
                     "notes": "ESC-50 published clip label; absence of background birds not independently verified; time offsets relative to ESC clip, original Freesound offset unavailable"})
    if existing_manifest is None:
        write_csv(manifest, rows)
    elif existing_manifest != [{k: str(v) for k, v in row.items()} for row in rows]:
        raise ValueError("Existing manifest differs from the reproducible selection; no overwrite")
    record = {"repository": "https://github.com/karolpiczak/ESC-50",
               "commit": COMMIT, "selection_seed": 42, "clips": len(rows),
               "selection": "All chirping_birds and crow (80); 2 per negative category per fold (80); obvious bird mentions excluded from negative source descriptions",
               "negative_categories": NEGATIVES, "files": downloads,
               "audio_uploaded": False, "license": "Dataset CC BY-NC 3.0; retain individual credits in upstream license"}
    if not record_path.exists():
        write_json(record_path, record)
    credits = ("ESC-50 subset. Karol J. Piczak; original creators below. Dataset: CC BY-NC 3.0.\n"
               "https://github.com/karolpiczak/ESC-50\n\n" + "\n".join(r["attribution"] for r in selected) + "\n")
    credit_path = attribution_dir / "SELECTED_ATTRIBUTIONS.txt"
    if credit_path.exists():
        if credit_path.read_text() != credits:
            raise ValueError("Existing credits differ; no overwrite")
    else:
        with credit_path.open("x") as f:
            f.write(credits)
    print(f"Saved {manifest}; {sum(v['bytes'] for v in downloads.values()):,} audio bytes")


if __name__ == "__main__":
    main()
