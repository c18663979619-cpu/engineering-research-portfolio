"""Feature schema v1: Hamming STFT, power moments and explicit HTK mel MFCCs."""
from functools import lru_cache

import numpy as np
from scipy.fft import dct

from .audio import FeatureConfig

EPS = 1e-12


@lru_cache(maxsize=16)
def mel_bank(sr, n_fft, n_mels):
    mel_max = 2595 * np.log10(1 + (sr / 2) / 700)
    hz = 700 * (10 ** (np.linspace(0, mel_max, n_mels + 2) / 2595) - 1)
    freq = np.fft.rfftfreq(n_fft, 1 / sr)
    bank = np.zeros((n_mels, len(freq)))
    for i in range(n_mels):
        bank[i] = np.maximum(0, np.minimum((freq - hz[i]) / (hz[i + 1] - hz[i]),
                                         (hz[i + 2] - freq) / (hz[i + 2] - hz[i + 1])))
    if np.any(bank.sum(axis=1) == 0):
        raise ValueError("Empty mel filters; increase n_fft or reduce n_mels")
    return bank


def power_spectrum(y, config):
    y = np.asarray(y, dtype=np.float64)
    if y.ndim != 1 or len(y) < config.n_fft or not np.isfinite(y).all():
        raise ValueError("Expected finite mono audio at least n_fft samples long")
    y = y - y.mean()
    frames = np.lib.stride_tricks.sliding_window_view(y, config.n_fft)[::config.hop_length]
    win = np.hamming(config.n_fft)
    power = np.abs(np.fft.rfft(frames * win, axis=1)) ** 2 / (win @ win)
    power[:, 1:-1 if config.n_fft % 2 == 0 else None] *= 2
    return np.fft.rfftfreq(config.n_fft, 1 / config.sample_rate), power


def extract_features(y, config=FeatureConfig()):
    y = np.asarray(y, dtype=np.float64)
    if len(y) != config.window_samples:
        raise ValueError(f"Expected {config.window_samples} samples, got {len(y)}")
    y = y - y.mean()
    freq, p = power_spectrum(y, config)
    total = p.sum(axis=1)
    centroid = (p @ freq) / np.maximum(total, EPS)
    bandwidth = np.sqrt((p * (freq[None, :] - centroid[:, None]) ** 2).sum(axis=1)
                        / np.maximum(total, EPS))
    mean_power = p.mean(axis=0)
    energy = float(mean_power.sum())
    peak = float(freq[1 + np.argmax(mean_power[1:])]) if energy > EPS else 0.0
    features = {"rms": float(np.sqrt(np.mean(y ** 2))),
                "zcr": float(np.mean(np.signbit(y[1:]) != np.signbit(y[:-1]))),
                "peak_frequency_hz": peak,
                "centroid_mean_hz": float(centroid.mean()),
                "centroid_std_hz": float(centroid.std()),
                "bandwidth_mean_hz": float(bandwidth.mean()),
                "bandwidth_std_hz": float(bandwidth.std())}
    for lo, hi in [(0, 1000), (1000, 2000), (2000, 4000), (4000, 4800)]:
        mask = (freq >= lo) & ((freq <= hi) if hi == 4800 else (freq < hi))
        features[f"band_{lo}_{hi}_ratio"] = float(mean_power[mask].sum() / max(energy, EPS))
    # HTK frequency scale; unnormalized triangles; natural log; orthonormal DCT-II.
    log_mel = np.log(np.maximum(p @ mel_bank(config.sample_rate, config.n_fft, config.n_mels).T, EPS))
    mfcc = dct(log_mel, type=2, norm="ortho", axis=1)[:, :config.n_mfcc]
    for i in range(config.n_mfcc):
        features[f"mfcc_{i:02d}_mean"] = float(mfcc[:, i].mean())
        features[f"mfcc_{i:02d}_std"] = float(mfcc[:, i].std())
    if not np.isfinite(list(features.values())).all():
        raise ValueError("Non-finite feature output")
    return features


def fft_baseline(features, min_hz=2000.0, max_hz=4500.0, rms_floor=0.005):
    """Illustrative fixed rule, not a recovered historical calibrated detector."""
    return int(features["rms"] >= rms_floor and min_hz <= features["peak_frequency_hz"] <= max_hz)
