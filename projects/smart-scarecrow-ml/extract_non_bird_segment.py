
import wave

input_path = "data/processed/non_bird/non_bird_001_9600.wav"

output_path = "data/processed/non_bird/non_bird_001_segment.wav"

start_time = 1.9
end_time = 3.3

with wave.open(input_path, "rb") as source:

    sample_rate = source.getframerate()
    channels = source.getnchannels()
    sample_width = source.getsampwidth()

    # Convert seconds to sample indices
    start_sample = int(start_time * sample_rate)
    end_sample = int(end_time * sample_rate)

    # Move to the starting position
    source.setpos(start_sample)

    # Read only the selected segment
    audio_data = source.readframes(
        end_sample - start_sample
    )

# Save the selected segment
with wave.open(output_path, "wb") as output:

    output.setnchannels(channels)
    output.setsampwidth(sample_width)
    output.setframerate(sample_rate)

    output.writeframes(audio_data)

print("Audio segment saved!")
print("Duration:", end_time - start_time, "seconds")
print("Sample count:", end_sample - start_sample)

