"""Inspect discontinuous ADC frames without inventing audio timing or labels."""
import argparse
import csv
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scarecrow.io import sha256, write_json
from scarecrow.plots import plt, save


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    metadata = json.loads((args.capture / "capture.json").read_text())
    rows = list(csv.DictReader((args.capture / "frames.csv").open()))
    quality = list(csv.DictReader((args.capture / "frame_quality.csv").open()))
    ids = sorted({int(r["frame_id"]) for r in rows})
    values = []
    for frame in ids:
        selected = [r for r in rows if int(r["frame_id"]) == frame]
        if [int(r["sample_index"]) for r in selected] != list(range(256)):
            raise ValueError("Incomplete or unordered ADC frame")
        x = np.array([int(r["adc_value"]) for r in selected])
        if np.any((x < 0) | (x > 1023)):
            raise ValueError("ADC sample outside 10-bit code range")
        values.append(x)
    values = np.array(values)
    receipt = np.array([float(r["host_received_seconds"]) for r in quality])
    stats = {"frames": len(ids), "samples": int(values.size), "adc_min": int(values.min()),
             "adc_max": int(values.max()), "dc_mean_adc": float(values.mean()),
             "frame_rms_min_adc": float(values.std(axis=1).min()),
             "frame_rms_median_adc": float(np.median(values.std(axis=1))),
             "frame_rms_max_adc": float(values.std(axis=1).max()),
             "rail_fraction": float(np.mean((values <= 1) | (values >= 1022))),
             "host_frame_receipt_interval_median_seconds": float(np.median(np.diff(receipt))) if len(receipt) > 1 else None,
             "frames_csv_sha256": sha256(args.capture / "frames.csv"),
             "label": "unlabeled", "actual_sample_rate_measured": False,
             "capture_metadata": metadata,
             "conclusion": "Structurally valid independent frames; no continuous WAV or Bird/Non-bird claim. Host receipt timing is not the intra-frame sample clock."}
    write_json(args.output / "hardware_capture_analysis.json", stats)
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), layout="constrained")
    for x, frame in zip(values[:4], ids[:4]):
        axes[0, 0].plot(np.arange(256), x - x.mean(), lw=0.8, label=f"Frame {frame}")
    axes[0, 0].set(title="First four separate frames, DC removed", xlabel="Sample index (not continuous time)", ylabel="ADC counts")
    axes[0, 0].legend()
    axes[0, 1].plot(ids, values.std(axis=1), "o-", color="#158570")
    axes[0, 1].set(title="Per-frame RMS", xlabel="Frame ID", ylabel="ADC counts")
    axes[1, 0].plot(ids, values.mean(axis=1), "o-", color="#dc7845")
    axes[1, 0].set(title="DC offset", xlabel="Frame ID", ylabel="ADC counts")
    axes[1, 1].plot(ids[1:], np.diff(receipt), "o-")
    axes[1, 1].set(title="Host receipt intervals (includes serial and firmware gaps)", xlabel="Frame ID", ylabel="Seconds")
    fig.suptitle("Kona328 / Waveshare A1 — real capture, unlabeled, discontinuous")
    save(fig, args.output / "hardware_capture_quality.png")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
