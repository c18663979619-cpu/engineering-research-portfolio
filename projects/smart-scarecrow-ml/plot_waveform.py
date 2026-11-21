
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
frame1 = data[data["frame_id"] == 1]

# 3. Extract sample indices and ADC values
sample_index = frame1["sample_index"]
adc_values = frame1["adc_value"]

# 4. Calculate approximate sampling time (ms)
time_ms = sample_index * 104 / 1000

# 5. Plot waveform
plt.figure(figsize=(10, 4))

plt.plot(time_ms, adc_values)

plt.xlabel("Time (ms)")
plt.ylabel("ADC Value")
plt.title("Sound Sensor Waveform - Frame 1")

plt.grid(True)

# 6. Display plot
plt.show()

