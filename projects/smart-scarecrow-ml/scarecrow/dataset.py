"""Manifest validation, provenance grouping and real-data feature table creation."""
import csv
import hashlib
from collections import Counter

import numpy as np
import soundfile as sf

from .audio import load_audio, quality, windows
from .features import extract_features
from .io import project_path, sha256

LABELS = {"non_bird": 0, "bird": 1}
REQUIRED = {"clip_id", "audio_path", "label", "source_recording", "source_group",
            "original_path", "start_sec", "end_sec", "label_verified", "license_status"}


def read_manifest(root, path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not REQUIRED.issubset(reader.fieldnames or []):
            raise ValueError(f"Missing manifest columns: {sorted(REQUIRED - set(reader.fieldnames or []))}")
        rows = list(reader)
    if not rows:
        raise ValueError("Manifest is empty")
    ids = set()
    for r in rows:
        if r["clip_id"] in ids or not r["clip_id"].strip():
            raise ValueError("clip_id must be unique and nonempty")
        ids.add(r["clip_id"])
        if r["label"] not in LABELS or r["label_verified"] not in {"yes", "no"}:
            raise ValueError(f"Invalid label or verification: {r['clip_id']}")
        if any(not r[k].strip() for k in ["source_recording", "source_group", "original_path", "license_status"]):
            raise ValueError("Source provenance and license status must be explicit")
        start, end = float(r["start_sec"]), float(r["end_sec"])
        if not np.isfinite([start, end]).all() or not 0 <= start < end:
            raise ValueError("Invalid original-recording time interval")
        for key in ["audio_path", "original_path"]:
            if not project_path(root, r[key]).is_file():
                raise ValueError(f"Missing {key}: {r[key]}")
    return rows


def build_dataset(root, manifest, config):
    rows = read_manifest(root, manifest)
    # Union source/session aliases and exact duplicate originals/decoded clips.
    # This protects against renamed copies; cropped/transcoded relatives still
    # require honest source metadata (no acoustic fingerprint claim).
    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        parent[find(b)] = find(a)

    seen = {}
    decoded = []
    audit = []
    pcm_labels = {}
    for i, r in enumerate(rows):
        path = project_path(root, r["audio_path"])
        y, sr = load_audio(path, config.sample_rate)
        duration = len(y) / sr
        if abs(duration - (float(r["end_sec"]) - float(r["start_sec"]))) > max(0.02, 2 / sr):
            raise ValueError(f"{r['clip_id']}: audio_path must be the already-cropped interval")
        pcm = hashlib.sha256(np.round(y, 6).astype("<f4").tobytes()).hexdigest()
        if pcm in pcm_labels and pcm_labels[pcm] != r["label"]:
            raise ValueError("Identical decoded clips have contradictory labels")
        pcm_labels[pcm] = r["label"]
        original_hash = sha256(project_path(root, r["original_path"]))
        keys = [("source", r["source_recording"]), ("session", r["source_group"]),
                ("original", original_hash), ("pcm", pcm)]
        for k in keys:
            if k in seen:
                union(i, seen[k])
            seen[k] = i
        decoded.append(y)
        q = quality(y, sr)
        audit.append({**r, **q, "audio_sha256": sha256(path), "original_sha256": original_hash,
                      "pcm_sha256": pcm, "channels_original_clip": sf.info(str(path)).channels})
    members = {}
    for i in range(len(rows)):
        members.setdefault(find(i), []).append(rows[i]["source_group"])
    table, skipped, clip_audio = [], [], []
    used_pcm = set()
    for i, (r, y, q) in enumerate(zip(rows, decoded, audit)):
        group = " | ".join(sorted(set(members[find(i)])))
        q["effective_group"] = group
        reasons = []
        if r["label_verified"] != "yes":
            reasons.append("label_not_verified")
        if q["near_silent"]:
            reasons.append("near_silent")
        if q["clipped_fraction"] > 0.01:
            reasons.append("more_than_1_percent_clipped")
        if q["pcm_sha256"] in used_pcm:
            reasons.append("exact_duplicate_clip")
        if reasons:
            skipped.append({"clip_id": r["clip_id"], "reasons": reasons})
            continue
        used_pcm.add(q["pcm_sha256"])
        count = 0
        for start, chunk in windows(y, config):
            # Every child window keeps its original source group.
            table.append({"clip_id": r["clip_id"], "audio_path": r["audio_path"], "label": r["label"],
                          "source_recording": r["source_recording"], "source_group": group,
                          "dataset_fold": r.get("dataset_fold", ""),
                          "category": r.get("category", ""),
                          "annotation_level": r.get("annotation_level", "selected_interval"),
                          "window_start_sec": start / config.sample_rate,
                          "original_start_sec": float(r["start_sec"]) + start / config.sample_rate,
                          **extract_features(chunk, config)})
            count += 1
        q["complete_windows"] = count
        q["unused_tail_seconds"] = (len(y) % config.window_samples) / config.sample_rate
        clip_audio.append((r, y))
    group_counts = {label: len({t["source_group"] for t in table if t["label"] == label}) for label in LABELS}
    summary = {"manifest_clips": len(rows), "feature_rows": len(table),
               "windows_by_label": dict(Counter(t["label"] for t in table)),
               "independent_groups_by_label": group_counts, "skipped": skipped,
               "license_unresolved_clips": [r["clip_id"] for r in rows if r["license_status"] != "verified"],
               "label_review": "Inherited from local annotations or the named dataset; not independently listened to by the agent. Clip-level labels may be weak at window level.",
               "grouping_limit": "Exact copies and declared provenance merged; hidden cropped/transcoded relatives require manual review."}
    return table, audit, summary, clip_audio


def inventory_wavs(root):
    output = []
    for path in sorted((root / "data").rglob("*.wav")):
        try:
            y, sr = load_audio(path)
            info = sf.info(str(path))
            output.append({"path": str(path.relative_to(root)), "sha256": sha256(path),
                           "channels": info.channels, "subtype": info.subtype, **quality(y, sr)})
        except (ValueError, RuntimeError) as e:
            output.append({"path": str(path.relative_to(root)), "error": str(e)})
    return output
