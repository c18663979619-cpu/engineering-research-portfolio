
import serial
import csv

# 1. Arduino serial port configuration
PORT = "/dev/cu.usbmodem11101"
BAUD_RATE = 115200

# 2. Connect to Arduino
arduino = serial.Serial(PORT, BAUD_RATE, timeout=2)

# 3. Create a CSV file
file = open("data/audio_test.csv", "w", newline="")
writer = csv.writer(file)

# Write the column name
writer.writerow(["adc_value"])

# 4. Collect 20 samples
count = 0

while count < 20:

    line = arduino.readline().decode(
        "utf-8", errors="ignore"
    ).strip()

    if line.startswith("Audio:"):

        try:
            value = int(line.split(":")[1])
        except ValueError:
            continue

        writer.writerow([value])
        print(value)

        count += 1

# 5. Close the connections
file.close()
arduino.close()

print("Successfully saved 20 samples!")

