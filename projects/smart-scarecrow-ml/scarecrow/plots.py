"""Headless publication figures; unavailable metrics stay visibly unavailable."""
import os
from pathlib import Path
import tempfile

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "smart-scarecrow-mpl"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .features import power_spectrum

COLORS = {"bird": "#158570", "non_bird": "#dc7845"}


def save(fig, path):
    with path.open("xb") as f:
        fig.savefig(f, format="png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def make_plots(output, clips, table, summary, evaluation, config):
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False,
                         "font.size": 10, "figure.facecolor": "white"})
    # At most six clips in overview; the complete table/audit remains exhaustive.
    selected = clips[:6]
    fig, axes = plt.subplots(len(selected), 2, figsize=(12, 3.2 * len(selected)), squeeze=False, layout="constrained")
    for (r, y), (wave, spec) in zip(selected, axes):
        centered = y - y.mean()
        wave.plot(np.arange(len(y)) / config.sample_rate, centered, color=COLORS[r["label"]], lw=0.6)
        wave.set(title=f"{r['clip_id']} | {r['label']}", xlabel="Time within annotated clip (s)", ylabel="Amplitude (full scale)")
        freq, power = power_spectrum(y, config)
        times = (np.arange(len(power)) * config.hop_length + config.n_fft / 2) / config.sample_rate
        im = spec.pcolormesh(times, freq, 10 * np.log10(np.maximum(power.T, 1e-12)), shading="auto", cmap="magma", vmin=-100, vmax=0)
        spec.set(title="Hamming short-time power spectrum", xlabel="Time within clip (s)", ylabel="Frequency (Hz)")
        fig.colorbar(im, ax=spec, label="Power (dB, relative units)")
    save(fig, output / "waveforms_spectrograms.png")
    fig, ax = plt.subplots(figsize=(10, 4), layout="constrained")
    for r, y in selected:
        freq, power = power_spectrum(y, config)
        ax.plot(freq, 10 * np.log10(np.maximum(power.mean(axis=0), 1e-12)), label=r["clip_id"], color=COLORS[r["label"]])
    ax.axvspan(2000, 4500, alpha=0.08, color="green", label="Illustrative baseline band")
    ax.set(title="Annotated clips: mean spectrum (descriptive only)", xlabel="Frequency (Hz)", ylabel="Power (dB, relative units)")
    ax.legend(); save(fig, output / "spectrum_comparison.png")
    features = ["rms", "centroid_mean_hz", "band_2000_4000_ratio", "bandwidth_mean_hz"]
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.8), layout="constrained")
    for ax, feature in zip(axes, features):
        for idx, label in enumerate(["non_bird", "bird"]):
            values = [t[feature] for t in table if t["label"] == label]
            ax.scatter(np.full(len(values), idx) + np.linspace(-0.05, 0.05, len(values)), values,
                       color=COLORS[label], alpha=0.8)
        ax.set(xticks=[0, 1], xticklabels=["Non-bird", "Bird"], title=feature.replace("_", "\n"))
    fig.suptitle("Window features — windows from the same recording are dependent")
    save(fig, output / "feature_analysis.png")
    fig, ax = plt.subplots(figsize=(10, 4.6), layout="constrained")
    if evaluation["status"] == "insufficient_data":
        ax.axis("off")
        counts = summary["independent_groups_by_label"]
        ax.text(0.5, 0.85, "EVALUATION NOT AVAILABLE", ha="center", fontsize=20, weight="bold", transform=ax.transAxes)
        ax.text(0.5, 0.61, f"Independent sources: Bird {counts['bird']} | Non-bird {counts['non_bird']}", ha="center", fontsize=14, transform=ax.transAxes)
        ax.text(0.5, 0.38, "Accuracy / Precision / Recall / F1 / Confusion matrix: N/A", ha="center", fontsize=13, transform=ax.transAxes)
        ax.text(0.5, 0.15, "Need at least 3 source groups per class for an exploratory holdout.\nNo training-set accuracy is presented as test performance.", ha="center", transform=ax.transAxes)
    else:
        keys = ["accuracy", "precision_bird", "recall_bird", "f1_bird"]
        for offset, (name, metrics) in zip([-0.18, 0.18], evaluation["metrics"].items()):
            ax.bar(np.arange(4) + offset, [metrics[k] for k in keys], width=0.35, label=name)
        ax.set(xticks=range(4), xticklabels=["Accuracy", "Precision", "Recall", "F1"], ylim=(0, 1.05), title="Exploratory source-disjoint holdout")
        ax.legend()
        matrix_fig, matrix_axes = plt.subplots(1, 2, figsize=(9, 4), layout="constrained")
        for m_ax, (name, m) in zip(matrix_axes, evaluation["metrics"].items()):
            cm = np.array(m["confusion_matrix"])
            m_ax.imshow(cm, cmap="Blues", vmin=0)
            for i in range(2):
                for j in range(2):
                    m_ax.text(j, i, str(cm[i, j]), ha="center", va="center")
            m_ax.set(title=name, xlabel="Predicted", ylabel="Actual", xticks=[0, 1], yticks=[0, 1],
                     xticklabels=["Non-bird", "Bird"], yticklabels=["Non-bird", "Bird"])
        save(matrix_fig, output / "confusion_matrices.png")
    save(fig, output / "model_performance.png")
    if (output.parent / "feature_importances.csv").exists():
        import csv
        rows = list(csv.DictReader((output.parent / "feature_importances.csv").open()))
        rows = sorted(rows, key=lambda r: float(r["importance"]), reverse=True)[:12][::-1]
        fig, ax = plt.subplots(figsize=(9, 5), layout="constrained")
        ax.barh([r["feature"] for r in rows], [float(r["importance"]) for r in rows], color="#158570")
        ax.set(title="Exploratory RF feature importance — not evidence of generalization", xlabel="Mean impurity decrease")
        save(fig, output / "feature_importance.png")
