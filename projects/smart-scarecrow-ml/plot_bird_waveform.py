import argparse
from pathlib import Path
import wave

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_AUDIO = PROJECT_DIR / "data" / "processed" / "bird" / "bird_001_9600.wav"
DEFAULT_OUTPUT = PROJECT_DIR / "results" / "bird_001_9600_waveform.png"


def main():
    parser = argparse.ArgumentParser(description="Plot a mono 16-bit PCM WAV waveform.")
    parser.add_argument("--input", type=Path, default=DEFAULT_AUDIO)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    with wave.open(str(args.input), "rb") as wav_file:
        if wav_file.getnchannels() != 1 or wav_file.getsampwidth() != 2:
            raise ValueError("Expected a mono 16-bit PCM WAV file.")
        sample_rate = wav_file.getframerate()
        audio_bytes = wav_file.readframes(wav_file.getnframes())

    samples = np.frombuffer(audio_bytes, dtype="<i2")
    time_seconds = np.arange(samples.size) / sample_rate

    fig, ax = plt.subplots(figsize=(10, 4), layout="constrained")
    ax.plot(time_seconds, samples, color="#185a91", linewidth=0.65)
    ax.set(
        title=f"Bird Call Waveform · {args.input.stem}",
        xlabel="Time (s)",
        ylabel="Amplitude (16-bit PCM counts)",
    )
    ax.grid(alpha=0.25)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as output_file:
        fig.savefig(output_file, format="png", dpi=200)
    plt.close(fig)

    print(f"{samples.size:,} samples · {sample_rate:,} Hz · {samples.size / sample_rate:.3f} s")
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
