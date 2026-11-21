
import wave
import numpy as np
import matplotlib.pyplot as plt

# 1. Load bird audio
file_path = "data/processed/bird/bird_001_9600.wav"

with wave.open(file_path, "rb") as wav:
    sample_rate = wav.getframerate()
    sample_count = wav.getnframes()
    audio_bytes = wav.readframes(sample_count)

# 2. Convert to NumPy array
audio = np.frombuffer(
    audio_bytes,
    dtype="<i2"
).astype(float)

# 3. Remove DC offset
audio = audio - np.mean(audio)

# 4. Create spectrogram
plt.figure(figsize=(12, 5))

plt.specgram(
    audio,
    NFFT=256,
    Fs=sample_rate,
    noverlap=192,
    cmap="viridis"
)

# 5. Labels
plt.xlabel("Time (seconds)")
plt.ylabel("Frequency (Hz)")
plt.title("Bird Call Spectrogram")

plt.ylim(0, 4800)
plt.xlim(1.9, 3.6)
plt.colorbar(label="Spectral Power (relative dB)")

# 6. Save image
plt.savefig(
    "results/bird_001_spectrogram_zoompng",
    dpi=300,
    bbox_inches="tight"
)

plt.show()

