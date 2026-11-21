
import csv
import wave
import numpy as np

# 1. Read labels.csv
with open("data/labels.csv", "r") as file:
    reader = csv.DictReader(file)
    samples = list(reader)

# 2. Process each audio file
for sample in samples:

    path = sample["audio_path"]
    label = sample["label"]

    # Read WAV
    with wave.open(path, "rb") as wav:
        audio_bytes = wav.readframes(wav.getnframes())

    # Convert PCM to NumPy
    audio = np.frombuffer(
        audio_bytes, dtype="<i2"
    ).astype(float)

    # Normalize 16-bit PCM and remove DC offset
    audio = audio / 32768.0
    audio = audio - np.mean(audio)

    # Calculate RMS
    rms = np.sqrt(np.mean(audio ** 2))

    print(f"{label} RMS: {rms:.6f}")

