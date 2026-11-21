"""Bounded capture of the user's existing 115200-baud text-frame firmware."""
import time

import numpy as np
import serial

from .io import write_csv, write_json


class LegacyFrameParser:
    def __init__(self):
        self.frame_id = None
        self.samples = []
        self.rejected = 0

    def reset(self):
        self.frame_id = None
        self.samples = []

    def feed(self, line):
        try:
            if line.startswith("FRAME_START,"):
                if self.frame_id is not None:
                    self.rejected += 1
                self.reset()
                _, frame_id, count = line.split(",")
                if int(count) != 256 or not 0 <= int(frame_id) <= 0xFFFFFFFF:
                    raise ValueError("Invalid frame header")
                self.frame_id = int(frame_id)
            elif line.startswith("Audio:") and self.frame_id is not None:
                value = int(line.split(":", 1)[1])
                if not 0 <= value <= 1023 or len(self.samples) >= 256:
                    raise ValueError("Invalid ADC sample")
                self.samples.append(value)
            elif line.startswith("FRAME_END,"):
                end_id = int(line.split(",")[1])
                if self.frame_id == end_id and len(self.samples) == 256:
                    result = {"frame_id": self.frame_id, "samples": list(self.samples)}
                    self.reset()
                    return result
                raise ValueError("Incomplete or mismatched frame")
        except (ValueError, IndexError):
            self.rejected += 1
            self.reset()
        return None


def capture_legacy(port, output, frames=30, timeout=60.0):
    if not 1 <= frames <= 10000 or timeout <= 2:
        raise ValueError("Require 1..10000 frames and timeout >2 seconds")
    output.mkdir(parents=True, exist_ok=False)
    parser, accepted, seen = LegacyFrameParser(), [], set()
    started = time.monotonic()
    try:
        with serial.Serial(port, 115200, timeout=0.25) as device:
            time.sleep(2)
            device.reset_input_buffer()
            with (output / "serial_raw.txt").open("x") as log:
                while len(accepted) < frames:
                    if time.monotonic() - started > timeout:
                        raise TimeoutError("Not enough complete frames before timeout; inspect saved raw log")
                    # Limit line size so unexpected binary firmware cannot grow a line unboundedly.
                    raw = device.read_until(b"\n", size=128)
                    if not raw:
                        continue
                    line = raw.decode("ascii", errors="replace").strip()
                    log.write(line + "\n")
                    packet = parser.feed(line)
                    if packet:
                        if packet["frame_id"] in seen:
                            raise ValueError("Repeated frame ID, board may have reset during recording")
                        seen.add(packet["frame_id"])
                        packet["host_received_seconds"] = time.monotonic() - started
                        accepted.append(packet)
                        print(f"Frame {packet['frame_id']}: 256 samples ({len(accepted)}/{frames})", flush=True)
        rows, quality = [], []
        for packet in accepted:
            values = np.array(packet["samples"])
            rows.extend({"frame_id": packet["frame_id"], "sample_index": i, "adc_value": int(v)} for i, v in enumerate(values))
            quality.append({"frame_id": packet["frame_id"], "host_received_seconds": packet["host_received_seconds"],
                            "min_adc": int(values.min()), "max_adc": int(values.max()),
                            "dc_adc": float(values.mean()), "rms_adc": float(values.std())})
        write_csv(output / "frames.csv", rows)
        write_csv(output / "frame_quality.csv", quality)
        write_json(output / "capture.json", {"status": "complete", "protocol": "legacy_text_frames", "baud": 115200,
                   "frames": len(accepted), "samples_per_frame": 256, "label": "unlabeled",
                   "rejected_frames": parser.rejected, "continuous_audio": False,
                   "source_code_nominal_rate_hz": 1000000 / 104, "measured_sample_rate_hz": None,
                   "note": "Existing firmware sends a frame then delays 300 ms. Never concatenate as continuous WAV or feed these short frames directly to the 0.25-second model."})
    except Exception as error:
        write_json(output / "capture_error.json", {"status": "failed", "error": str(error), "complete_frames_received": len(accepted)})
        raise
