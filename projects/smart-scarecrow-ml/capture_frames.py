
import serial
import csv
import time

# 1. Serial configuration
PORT = "/dev/cu.usbmodem11101"
BAUD_RATE = 115200

# 2. Data collection settings
TOTAL_FRAMES = 3
SAMPLES_PER_FRAME = 256

# 3. Connect to Arduino
arduino = serial.Serial(
    PORT,
    BAUD_RATE,
    timeout=2
)

time.sleep(2)
arduino.reset_input_buffer()

# 4. Create CSV file
file = open("data/frames_test.csv", "w", newline="")
writer = csv.writer(file)

writer.writerow([
    "frame_id",
    "sample_index",
    "adc_value"
])

# 5. Initialise variables
saved_frames = 0
current_frame_id = None
samples = []

print("Starting frame collection...")

# 6. Read serial data
while saved_frames < TOTAL_FRAMES:

    line = arduino.readline().decode(
        "utf-8", errors="ignore"
    ).strip()

    if line.startswith("FRAME_START,"):

        parts = line.split(",")

        try:
            frame_id = int(parts[1])
            sample_count = int(parts[2])
        except (ValueError, IndexError):
            continue

        current_frame_id = None
        samples = []

        if sample_count == SAMPLES_PER_FRAME:
            current_frame_id = frame_id

    elif line.startswith("Audio:"):

        if current_frame_id is not None:

            try:
                value = int(line.split(":")[1])
            except (ValueError, IndexError):
                continue

            if 0 <= value <= 1023:
                samples.append(value)

    elif line.startswith("FRAME_END,"):

        try:
            end_id = int(line.split(",")[1])
        except (ValueError, IndexError):
            continue

        if (
            current_frame_id == end_id
            and len(samples) == SAMPLES_PER_FRAME
        ):

            for i, value in enumerate(samples):
                writer.writerow([
                    current_frame_id,
                    i,
                    value
                ])

            saved_frames += 1

            print(
                f"Frame {current_frame_id} saved: "
                f"{len(samples)} samples"
            )

        current_frame_id = None
        samples = []

# 7. Close connections
file.close()
arduino.close()

print("Collection completed!")
print("Total frames:", saved_frames)
print("Total samples:", saved_frames * SAMPLES_PER_FRAME)

