"""PCM decoding, amplitude-preserving resampling and explicit windowing."""
from dataclasses import asdict, dataclass
from math import gcd
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly


@dataclass(frozen=True)
class FeatureConfig:
    sample_rate: int = 9600
    window_seconds: float = 0.25
    n_fft: int = 256
    hop_length: int = 128
    n_mels: int = 26
    n_mfcc: int = 13
    version: str = "1"

    def __post_init__(self):
        if self.sample_rate != 9600 or self.version != "1":
            raise ValueError("Feature schema v1 requires 9600 Hz")
        if not np.isfinite(self.window_seconds) or self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if not 16 <= self.n_fft <= self.window_samples:
            raise ValueError("n_fft must fit in a complete classification window")
        if not 1 <= self.hop_length <= self.n_fft:
            raise ValueError("Invalid STFT hop")
        if not 1 <= self.n_mfcc <= self.n_mels <= self.n_fft // 2:
            raise ValueError("Invalid mel/MFCC configuration")

    @property
    def window_samples(self):
        return round(self.sample_rate * self.window_seconds)

    def to_dict(self):
        return asdict(self)


def load_audio(path: Path, target_sr: int | None = None):
    """Return normalized mono floats, without peak normalization or DC removal."""
    y, sr = sf.read(str(path), dtype="float64", always_2d=True)
    if not len(y) or not np.isfinite(y).all():
        raise ValueError(f"Empty or non-finite audio: {path}")
    y = y.mean(axis=1)
    if target_sr is not None and sr != target_sr:
        g = gcd(sr, target_sr)
        y = resample_poly(y, target_sr // g, sr // g)
        sr = target_sr
    return y, sr


def windows(y, config: FeatureConfig):
    """Non-overlapping complete windows. Never pad partial inference windows."""
    n = config.window_samples
    for start in range(0, len(y) - n + 1, n):
        yield start, y[start:start + n]


def quality(y, sr):
    centered = y - y.mean()
    rms = float(np.sqrt(np.mean(centered ** 2)))
    return {
        "sample_rate": int(sr), "samples": len(y), "duration_seconds": len(y) / sr,
        "dc_offset": float(y.mean()), "rms": rms,
        "peak_abs": float(np.abs(y).max()),
        "clipped_fraction": float(np.mean(np.abs(y) >= 0.999)),
        "near_silent": rms < 1e-5,
    }
