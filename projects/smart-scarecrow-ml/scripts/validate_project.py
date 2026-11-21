"""Record local checks and UNO compile evidence without flashing any device."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    checks = [
        ("pytest", [sys.executable, "-m", "pytest", "-q"]),
        ("pip_check", [sys.executable, "-m", "pip", "check"]),
        ("original_integrity", [sys.executable, "scripts/check_originals.py"]),
    ]
    cli = shutil.which("arduino-cli")
    bundled = Path("/Applications/Arduino IDE.app/Contents/Resources/app/lib/backend/resources/arduino-cli")
    if not cli and bundled.exists():
        cli = str(bundled)
    if cli:
        for sketch in ["uno_audio_capture", "uno_controller", "scarecrow_host_ml", "legacy_master_fixed"]:
            libraries = []
            if sketch in ["scarecrow_host_ml", "legacy_master_fixed"]:
                servo = Path.home() / "Library/Arduino15/libraries/Servo"
                if servo.exists():
                    libraries += ["--library", str(servo)]
            if sketch == "legacy_master_fixed":
                fft = Path.home() / "Documents/Arduino/libraries/arduinoFFT"
                if fft.exists():
                    libraries += ["--library", str(fft)]
            checks.append((sketch, [cli, "compile", "--fqbn", "arduino:avr:uno", "--warnings", "all", *libraries,
                          "--build-path", str(args.output.resolve() / ("build_" + sketch)),
                          "firmware/" + sketch]))
    summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "checks": [],
               "hardware_connected_tested": False, "flashed": False}
    for name, command in checks:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=180)
        log = result.stdout + result.stderr
        with (args.output / (name + ".log")).open("x") as f:
            f.write(log)
        summary["checks"].append({"name": name, "returncode": result.returncode, "command": command})
        print(f"{name}: {'PASS' if result.returncode == 0 else 'FAIL'}", flush=True)
        if name.startswith("uno_"):
            print(result.stdout, flush=True)
    if not cli:
        summary["firmware_compile"] = "not run: arduino-cli unavailable"
    with (args.output / "validation.json").open("x") as f:
        json.dump(summary, f, indent=2); f.write("\n")
    return int(any(c["returncode"] for c in summary["checks"]))


if __name__ == "__main__":
    sys.exit(main())
