
import wave
import numpy as np

# 1. Audio file path
file_path = "data/processed/bird/bird_001_9600.wav"

# 2. Open WAV file
with wave.open(file_path, "rb") as wav_file:

    sample_rate = wav_file.getframerate()

    channels = wav_file.getnchannels()

    sample_count = wav_file.getnframes()

    audio_bytes = wav_file.readframes(sample_count)

# 3. Convert bytes into NumPy array
audio = np.frombuffer(audio_bytes, dtype="<i2")

# 4. Calculate audio duration
duration = sample_count / sample_rate

# 5. Print information
print("Sample Rate:", sample_rate)
print("Channels:", channels)
print("Total Samples:", sample_count)
print("Duration:", duration, "seconds")

print("Array Shape:", audio.shape)
print("Minimum Value:", np.min(audio))
print("Maximum Value:", np.max(audio))

