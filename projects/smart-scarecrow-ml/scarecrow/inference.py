"""Identical offline/live preprocessing; scores are never called accuracy."""
import numpy as np

from .audio import FeatureConfig, load_audio, windows
from .features import extract_features, fft_baseline
from .io import sha256


def predict_window(y, model):
    config = FeatureConfig(**model["feature_config"])
    features = extract_features(y, config)
    if set(features) != set(model["feature_names"]):
        raise ValueError("Model/feature schema mismatch")
    x = np.array([[features[k] for k in model["feature_names"]]])
    clf = model["classifier"]
    idx = list(clf.classes_).index(1)
    score = float(clf.predict_proba(x)[0, idx])
    threshold = model.get("decision_threshold", 0.5)
    return {"prediction": "bird" if score >= threshold else "non_bird", "bird_score": score,
            "decision_threshold": threshold,
            "fft_prediction": "bird" if fft_baseline(features, **model["baseline_parameters"]) else "non_bird",
            "rms": features["rms"]}


def predict_file(path, model):
    config = FeatureConfig(**model["feature_config"])
    y, _ = load_audio(path, config.sample_rate)
    predictions = [{"window_start_sec": start / config.sample_rate, **predict_window(chunk, model)}
                   for start, chunk in windows(y, config)]
    if not predictions:
        raise ValueError("Audio shorter than one complete classification window")
    return {"audio_path": str(path), "model_status": model["status"],
            "known_training_file": sha256(path) in model["training_audio_sha256"],
            "training_file_check_limit": "Exact file hash only; renamed/transcoded relatives may still be training data.",
            "score_interpretation": model["score_interpretation"],
            "unused_tail_seconds": (len(y) % config.window_samples) / config.sample_rate,
            "predictions": predictions}


class TriggerGate:
    """Debounce, silence gate and cooldown shared by live deployment."""
    def __init__(self, threshold=0.8, consecutive=3, cooldown=10.0):
        self.threshold, self.consecutive, self.cooldown = threshold, consecutive, cooldown
        self.count = 0
        self.last_trigger = -float("inf")

    def reset(self):
        self.count = 0

    def update(self, prediction, now):
        positive = prediction["bird_score"] >= self.threshold and prediction["rms"] >= 0.005
        self.count = self.count + 1 if positive else 0
        if self.count >= self.consecutive and now - self.last_trigger >= self.cooldown:
            self.last_trigger = now
            self.count = 0
            return True
        return False
