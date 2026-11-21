
import numpy as np
import matplotlib.pyplot as plt

# 1. Read CSV data
data = np.genfromtxt(
    "data/frames_test.csv",
    delimiter=",",
    names=True,
    dtype=int
)

# 2. Select Frame 1
frame1 = data[data["frame_id"] == 3]

# 3. Extract sample indices and ADC values
sample_index = frame1["sample_index"]
adc_values = frame1["adc_value"]

# 4. Calculate approximate sampling time (ms)
time_ms = sample_index * 104 / 1000

# 5. Plot waveform

# Calculate the average ADC value
dc_offset = np.mean(adc_values)
plt.figure(figsize=(10, 4))
# Remove DC offset
centered_audio = adc_values - dc_offset
rms = np.sqrt(np.mean(centered_audio ** 2))

print("RMS:", rms)
# Print results
print("DC Offset:", dc_offset)
print("Centered Mean:", np.mean(centered_audio))

# Plot centered waveform
plt.plot(time_ms, centered_audio)

plt.xlabel("Time (ms)")
plt.ylabel("Centered ADC Value")
plt.title("Sound Waveform - DC Offset Removed")

plt.grid(True)

# 6. Display plot
plt.show()

