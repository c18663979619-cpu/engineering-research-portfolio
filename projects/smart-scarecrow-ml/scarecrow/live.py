"""Optional host-microphone inference and deliberately opt-in serial actuation."""
import time
from math import gcd

import numpy as np
from scipy.signal import resample_poly

from .audio import FeatureConfig
from .inference import TriggerGate, predict_window
from .io import write_json


def live(model, output, seconds=10.0, sample_rate=48000, device=None, serial_port=None, enable_actuator=False):
    if seconds <= 0 or sample_rate < 9600:
        raise ValueError("Positive duration and microphone sample rate >= 9600 required")
    if enable_actuator and (not serial_port or model["status"] == "demo_unvalidated"):
        raise ValueError("Actuation requires a serial port and a source-held-out model; demo models cannot actuate")
    if serial_port and not enable_actuator:
        raise ValueError("Serial output requires explicit --enable-actuator")
    if output.exists():
        raise FileExistsError(output)
    # Optional audio import may initialize PortAudio; validate all guards first.
    import sounddevice as sd
    import serial

    config = FeatureConfig(**model["feature_config"])
    blocksize = round(sample_rate * config.window_seconds)
    if abs(blocksize / sample_rate - config.window_seconds) > 1e-8:
        raise ValueError("Input rate must support exact classification block duration")
    gate, rows, link = TriggerGate(threshold=max(0.8, model.get("decision_threshold", 0.5))), [], None
    started = time.monotonic()
    status, failure = "complete", None
    try:
        if serial_port:
            link = serial.Serial(serial_port, 115200, timeout=0.2)
            time.sleep(2)
            # Full-system firmware boots disarmed; the explicit CLI actuator
            # flag authorizes arming. The LED-only sketch ignores ARM.
            link.write(b"HEARTBEAT\nARM\n")
        with sd.InputStream(device=device, samplerate=sample_rate, channels=1, dtype="float32", blocksize=blocksize) as stream:
            started = time.monotonic()
            while time.monotonic() - started < seconds:
                block, overflowed = stream.read(blocksize)
                now = time.monotonic()
                if overflowed:
                    gate.reset()
                    rows.append({"elapsed_seconds": now - started, "status": "audio_overflow_skipped"})
                    continue
                g = gcd(sample_rate, config.sample_rate)
                y = resample_poly(block[:, 0].astype(np.float64), config.sample_rate // g, sample_rate // g)
                prediction = predict_window(y, model)
                trigger = gate.update(prediction, now)
                if link:
                    link.write(b"HEARTBEAT\n")
                    if trigger:
                        link.write(b"TRIGGER\n")
                    telemetry = link.read(link.in_waiting).decode("utf-8", errors="replace") if link.in_waiting else ""
                else:
                    telemetry = ""
                row = {"elapsed_seconds": now - started, **prediction, "would_trigger": trigger,
                       "command_sent": bool(link and trigger), "controller_telemetry": telemetry}
                rows.append(row)
                print(row, flush=True)
    except BaseException as error:
        status, failure = "failed", str(error) or type(error).__name__
        raise
    finally:
        if link:
            try:
                link.write(b"STOP\n")
            finally:
                link.close()
        write_json(output, {"status": status, "error": failure, "model_status": model["status"],
                           "actuator_enabled": enable_actuator, "predictions": rows})
