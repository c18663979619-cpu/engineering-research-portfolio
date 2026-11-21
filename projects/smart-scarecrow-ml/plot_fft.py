
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
fft_result = np.fft.rfft(centered_audio)

# 6. Calculate frequency values
frequencies = np.fft.rfftfreq(
    len(centered_audio),
    d=1/fs
)

# 7. Calculate FFT magnitude
magnitude = np.abs(fft_result)
# Find the dominant frequency (excluding DC)

peak_index = np.argmax(magnitude[1:]) + 1

peak_frequency = frequencies[peak_index]

peak_magnitude = magnitude[peak_index]

print("Dominant Frequency:", peak_frequency, "Hz")

print("Peak Magnitude:", peak_magnitude)
# 8. Plot frequency spectrum
plt.figure(figsize=(10, 4))

plt.plot(frequencies, magnitude)

plt.xlabel("Frequency (Hz)")
plt.ylabel("FFT Magnitude")
plt.title("Sound Sensor - Frequency Spectrum")

plt.grid(True)

plt.show()

