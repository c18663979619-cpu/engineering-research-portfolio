
import numpy as np
import matplotlib.pyplot as plt

# 1. Load CSV data
data = np.genfromtxt(
    "data/frames_test.csv",
    delimiter=",",
    names=True,
    dtype=int
)

# 2. Select Frame 1
frame = data[data["frame_id"] == 1]

adc_values = frame["adc_value"]

# 3. Remove DC Offset
centered_audio = adc_values - np.mean(adc_values)

# 4. Sampling frequency
fs = 1000000 / 104

# 5. Calculate FFT
window = np.hamming(len(centered_audio))

windowed_audio = centered_audio * window

fft_result = np.fft.rfft(windowed_audio)

# 6. Calculate frequency values
frequencies = np.fft.rfftfreq(
    len(centered_audio),
    d=1/fs
)

# 7. Calculate FFT magnitude
magnitude = np.abs(fft_result)
raw_fft = np.fft.rfft(centered_audio)
raw_magnitude = np.abs(raw_fft)

raw_normalized = raw_magnitude / np.max(raw_magnitude)
hamming_normalized = magnitude / np.max(magnitude)
# Find the dominant frequency (excluding DC)

peak_index = np.argmax(magnitude[1:]) + 1

peak_frequency = frequencies[peak_index]

peak_magnitude = magnitude[peak_index]

print("Dominant Frequency:", peak_frequency, "Hz")

print("Peak Magnitude:", peak_magnitude)
# 8. Plot frequency spectrum
plt.figure(figsize=(10, 4))

plt.plot(
    frequencies,
    raw_normalized,
    label="Without Window"
)

plt.plot(
    frequencies,
    hamming_normalized,
    label="Hamming Window"
)

plt.legend()

plt.xlabel("Frequency (Hz)")
plt.ylabel("Normalized FFT Magnitude")
plt.title("Sound Sensor - Frequency Spectrum")

plt.grid(True)
plt.savefig("results/fft_window_comparison.png", dpi=300, bbox_inches="tight")
plt.show()

