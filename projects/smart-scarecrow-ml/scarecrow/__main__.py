import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
import platform
import sys

import numpy as np

from .audio import FeatureConfig
from .dataset import build_dataset, inventory_wavs
from .inference import predict_file
from .io import sha256, write_csv, write_json
from .model import load_model, train_evaluate

ROOT = Path(__file__).resolve().parent.parent


def run(args):
    from .plots import make_plots
    config = FeatureConfig()
    root = args.root.resolve()
    manifest = args.manifest or root / "data" / "manifest.csv"
    output = args.output or root / "results" / "runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "run_config.json", {"feature_config": config.to_dict(),
               "manifest": str(manifest), "manifest_sha256": sha256(manifest),
               "python": sys.version, "platform": platform.platform(), "seed": 42,
               "command": sys.argv, "created_utc": datetime.now(timezone.utc).isoformat(),
               "code_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in sorted((ROOT / "scarecrow").glob("*.py"))}})
    try:
        table, audit, summary, clips = build_dataset(root, manifest, config)
        write_json(output / "dataset_summary.json", summary)
        write_json(output / "dataset_audit.json", audit)
        write_json(output / "wav_inventory.json", inventory_wavs(root))
        write_csv(output / "features.csv", table)
        evaluation = train_evaluate(table, audit, config, output, args.demo_model, args.calibrate)
        make_plots(output / "figures", clips, table, summary, evaluation, config)
        write_json(output / "run_status.json", {"status": "complete", "evaluation_status": evaluation["status"]})
        print(f"Run saved: {output}\nFeature windows: {len(table)}\nEvaluation: {evaluation['status']}")
        if evaluation["reason"]:
            print(evaluation["reason"])
    except Exception as error:
        write_json(output / "run_status.json", {"status": "failed", "error": str(error)})
        raise


def legacy(args):
    with args.input.open(newline="") as f:
        rows = list(csv.DictReader(f))
    result = []
    for frame in sorted({int(r["frame_id"]) for r in rows}):
        subset = [r for r in rows if int(r["frame_id"]) == frame]
        indices = [int(r["sample_index"]) for r in subset]
        values = np.array([int(r["adc_value"]) for r in subset])
        if indices != list(range(len(values))) or len(values) != 256 or np.any((values < 0) | (values > 1023)):
            raise ValueError(f"Malformed legacy frame {frame}")
        result.append({"frame_id": frame, "samples": len(values), "min": int(values.min()), "max": int(values.max()),
                       "dc_adc_counts": float(values.mean()), "rms_adc_counts": float(values.std()),
                       "sample_rate_hz": None, "label": "unknown", "frequency_analysis_valid": False})
    write_json(args.output, {"frames": result, "note": "No timestamps/rate metadata. 104 us analogRead assumption is not a measured sampling period. Frames may contain transmission gaps."})
    print(f"Audited {len(result)} unlabeled hardware frames: {args.output}")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m scarecrow", description="Smart Scarecrow reproducible audio experiments")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run", help="Validate, extract features, evaluate, optionally train a demo, plot")
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--manifest", type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--demo-model", action="store_true")
    p.add_argument("--calibrate", action="store_true", help="Train folds 1-3, select low-FPR threshold on fold 4, test fold 5")
    p = sub.add_parser("predict", help="Classify complete windows of a local audio file")
    p.add_argument("--audio", type=Path, required=True)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--allow-demo", action="store_true")
    p = sub.add_parser("audit-legacy", help="Validate the original 256-sample CSV frames without assuming sample rate")
    p.add_argument("--input", type=Path, default=ROOT / "data" / "frames_test.csv")
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("capture", help="Capture continuous SCM1 firmware data (250000 baud)")
    p.add_argument("--port", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--seconds", type=float, default=5.0)
    p.add_argument("--timeout", type=float, default=30.0)
    p = sub.add_parser("capture-legacy", help="Capture existing FRAME_START/Audio/FRAME_END firmware without flashing")
    p.add_argument("--port", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--frames", type=int, default=30)
    p.add_argument("--timeout", type=float, default=60.0)
    p = sub.add_parser("live", help="Mac microphone inference; dry run unless serial actuation explicitly enabled")
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--allow-demo", action="store_true")
    p.add_argument("--seconds", type=float, default=10.0)
    p.add_argument("--sample-rate", type=int, default=48000)
    p.add_argument("--device")
    p.add_argument("--serial-port")
    p.add_argument("--enable-actuator", action="store_true")
    p = sub.add_parser("segment", help="Make a new mono 9600 Hz WAV interval without overwriting any source")
    p.add_argument("--audio", type=Path, required=True)
    p.add_argument("--start", type=float, required=True)
    p.add_argument("--end", type=float, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            run(args)
        elif args.command == "predict":
            model = load_model(args.model, args.allow_demo)
            result = predict_file(args.audio, model)
            write_json(args.output, result)
            print(f"Saved {len(result['predictions'])} predictions; model={model['status']}; {args.output}")
        elif args.command == "audit-legacy":
            legacy(args)
        elif args.command == "capture":
            from .serial_audio import capture
            capture(args.port, args.output, args.seconds, args.timeout)
        elif args.command == "capture-legacy":
            from .legacy_serial import capture_legacy
            capture_legacy(args.port, args.output, args.frames, args.timeout)
        elif args.command == "live":
            from .live import live
            live(load_model(args.model, args.allow_demo), args.output, args.seconds, args.sample_rate,
                 args.device, args.serial_port, args.enable_actuator)
        elif args.command == "segment":
            import soundfile as sf
            from .audio import load_audio
            if not np.isfinite([args.start, args.end]).all() or not 0 <= args.start < args.end:
                raise ValueError("Require finite 0 <= start < end")
            y, sr = load_audio(args.audio, 9600)
            if args.end > len(y) / sr:
                raise ValueError("Requested interval extends beyond the recording")
            chunk = y[round(args.start * sr):round(args.end * sr)]
            if not len(chunk) or np.max(np.abs(chunk)) >= 1:
                raise ValueError("Empty or overloaded audio interval; inspect gain before saving PCM16")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("xb") as f:
                sf.write(f, chunk, sr, format="WAV", subtype="PCM_16")
            print(f"Saved new interval: {args.output}; {len(chunk) / sr:.3f} s at {sr} Hz")
    except (ValueError, FileExistsError, FileNotFoundError, TimeoutError) as error:
        parser.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    main()
