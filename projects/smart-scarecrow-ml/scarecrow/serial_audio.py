"""SCM1 binary packets. Never concatenate missing/gapped serial frames as audio."""
import binascii
import struct
import time

import numpy as np
import serial
import soundfile as sf

from .io import write_csv, write_json

MAGIC = b"SCM1"
HEADER = struct.Struct("<4sIHHH")
COUNT = 256
PACKET_SIZE = HEADER.size + COUNT * 2 + 2


def encode_packet(sequence, samples, dropped=0):
    """Protocol fixture generator, also useful to other acquisition firmware."""
    if len(samples) != COUNT or any(not 0 <= x <= 1023 for x in samples):
        raise ValueError("Need exactly 256 unsigned 10-bit ADC samples")
    payload = HEADER.pack(MAGIC, sequence, 8000, COUNT, dropped) + struct.pack("<256H", *samples)
    return payload + struct.pack("<H", binascii.crc_hqx(payload, 0xFFFF))


class PacketParser:
    def __init__(self):
        self.buffer = bytearray()
        self.bad_packets = 0

    def feed(self, data):
        self.buffer.extend(data)
        packets = []
        while len(self.buffer) >= 4:
            position = self.buffer.find(MAGIC)
            if position < 0:
                self.buffer = self.buffer[-3:]
                break
            if position:
                del self.buffer[:position]
            if len(self.buffer) < HEADER.size:
                break
            _, seq, sr, n, dropped = HEADER.unpack_from(self.buffer)
            if sr != 8000 or n != COUNT:
                self.bad_packets += 1
                del self.buffer[0]
                continue
            if len(self.buffer) < PACKET_SIZE:
                break
            packet = bytes(self.buffer[:PACKET_SIZE])
            checksum = struct.unpack_from("<H", packet, PACKET_SIZE - 2)[0]
            if binascii.crc_hqx(packet[:-2], 0xFFFF) != checksum:
                self.bad_packets += 1
                del self.buffer[0]
                continue
            values = np.frombuffer(packet, dtype="<u2", offset=HEADER.size, count=COUNT).copy()
            if np.any(values > 1023):
                raise ValueError("Out-of-range ADC sample")
            packets.append({"sequence": seq, "sample_rate": sr, "dropped": dropped, "samples": values})
            del self.buffer[:PACKET_SIZE]
        return packets


def capture(port, output, seconds=5.0, timeout=30.0):
    if not 0 < seconds <= 600 or timeout <= seconds:
        raise ValueError("Require 0 < seconds <= 600 and timeout > seconds")
    output.mkdir(parents=True, exist_ok=False)
    parser, packets = PacketParser(), []
    needed = int(np.ceil(seconds * 8000 / COUNT))
    deadline = time.monotonic() + timeout
    try:
        with serial.Serial(port, 250000, timeout=0.25) as device:
            time.sleep(2)  # UNO reset on serial open.
            device.reset_input_buffer()
            while len(packets) < needed:
                if time.monotonic() > deadline:
                    raise TimeoutError("Timed out before a complete continuous capture")
                for packet in parser.feed(device.read(2048)):
                    if parser.bad_packets:
                        raise ValueError("CRC/header error: capture discarded, continuity not trusted")
                    if packet["dropped"]:
                        raise ValueError("Firmware ADC overrun: capture discarded")
                    if packets and packet["sequence"] != (packets[-1]["sequence"] + 1) % (2 ** 32):
                        raise ValueError("Missing packet: capture discarded")
                    packets.append(packet)
                    if len(packets) == needed:
                        break
        values = np.concatenate([p["samples"] for p in packets])
        # Keep the acquisition offset; feature extraction removes DC per window.
        audio = (values.astype(np.float64) - 512) / 512
        with (output / "capture.wav").open("xb") as f:
            sf.write(f, audio, 8000, format="WAV", subtype="PCM_16")
        write_csv(output / "packets.csv", [{k: p[k] for k in ["sequence", "sample_rate", "dropped"]} for p in packets])
        write_json(output / "capture.json", {"status": "complete", "sample_rate": 8000,
                   "actual_clock_calibrated": False, "protocol": "SCM1", "samples": len(values),
                   "duration_seconds": len(values) / 8000, "label": "unlabeled",
                   "note": "Timer-defined nominal rate; clock tolerance and sensor response need physical measurement."})
    except Exception as error:
        write_json(output / "capture_error.json", {"status": "failed", "error": str(error), "valid_packets_received": len(packets)})
        raise
