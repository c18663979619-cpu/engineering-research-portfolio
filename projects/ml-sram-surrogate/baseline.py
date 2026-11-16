"""Milestone 0: training-mean and ordinary least-squares baselines at 1.0 V."""
import csv
import hashlib
import json
import os
import platform
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

FEATURES = ["vth_n1_v", "vth_p1_v", "vth_n2_v", "vth_p2_v"]
SEED = 42


def metrics(actual, predicted):
    residual = actual - predicted
    return {
        "mae_mv": float(np.mean(np.abs(residual))),
        "rmse_mv": float(np.sqrt(np.mean(residual ** 2))),
        "r2": float(1 - np.sum(residual ** 2) / np.sum((actual - actual.mean()) ** 2)),
    }


def main():
    manifest_path = ROOT / "data/source.json"
    manifest = json.loads(manifest_path.read_text())
    rows = []
    for part in manifest["parts"]:
        path = ROOT / "data/raw" / part["file"]
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != part["sha256"]:
            raise ValueError(f"Source hash mismatch: {path}")
        with path.open(newline="") as handle:
            rows.extend(csv.DictReader(handle))
    ids = np.array([int(row["sample_id"]) for row in rows])
    x = np.array([[float(row[name]) for name in FEATURES] for row in rows])
    y = np.array([float(row["snm_1v_mv"]) for row in rows])
    if not np.array_equal(ids, np.arange(10000)):
        raise ValueError("Expected exactly 10,000 ordered, unique source sample IDs")
    if not (np.isfinite(x).all() and np.isfinite(y).all()):
        raise ValueError("Non-finite input or target")

    # One row per sample at one voltage; splitting sample IDs prevents overlap.
    order = np.random.default_rng(SEED).permutation(len(ids))
    train, test = order[:8000], order[8000:]
    if set(ids[train]) & set(ids[test]):
        raise ValueError("Train/test sample overlap")
    # Learn centering from training data only. The intercept is explicit.
    center = x[train].mean(axis=0)
    design_train = np.column_stack([np.ones(len(train)), x[train] - center])
    design_test = np.column_stack([np.ones(len(test)), x[test] - center])
    coefficients, _, _, _ = np.linalg.lstsq(design_train, y[train], rcond=None)
    predictions = {
        "training_mean": np.full(len(test), y[train].mean()),
        "linear_regression": design_test @ coefficients,
    }
    results = ROOT / "results"
    figures = ROOT / "figures"
    results.mkdir(exist_ok=True)
    figures.mkdir(exist_ok=True)
    records = {name: metrics(y[test], values) for name, values in predictions.items()}
    with (results / "baseline_metrics.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["model", "mae_mv", "rmse_mv", "r2"])
        writer.writeheader()
        writer.writerows({"model": name, **values} for name, values in records.items())
    experiment = {
        "status": "In progress — milestone 0",
        "source_revision": manifest["revision"],
        "source_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "baseline_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "supply_v": 1.0,
        "features": FEATURES,
        "target": "snm_1v_mv",
        "split": {"generator": "numpy.default_rng / PCG64", "seed": SEED,
                  "train_rows": len(train), "test_rows": len(test),
                  "train_ids_sha256": hashlib.sha256(ids[train].astype("<i8").tobytes()).hexdigest(),
                  "test_ids_sha256": hashlib.sha256(ids[test].astype("<i8").tobytes()).hexdigest()},
        "fit": {"method": "ordinary least squares with intercept, numpy.linalg.lstsq",
                "feature_center_v": center.tolist(), "intercept_mv": float(coefficients[0]),
                "coefficients_mv_per_v": coefficients[1:].tolist()},
        "test_below_180mv_count": int(np.sum(y[test] < 180)),
        "metrics": records,
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "matplotlib": matplotlib.__version__},
    }
    (results / "experiment.json").write_text(json.dumps(experiment, indent=2) + "\n")

    fig, axes = plt.subplots(1, 2, figsize=(9, 4), layout="constrained")
    limits = [min(y[test].min(), *(v.min() for v in predictions.values())) - 3,
              max(y[test].max(), *(v.max() for v in predictions.values())) + 3]
    for ax, (name, values) in zip(axes, predictions.items()):
        ax.scatter(y[test], values, s=9, alpha=0.25, color="#326a9f", rasterized=True)
        ax.plot(limits, limits, "--", color="#b44e3c", linewidth=1, label="Ideal prediction")
        ax.set(xlim=limits, ylim=limits, xlabel="Behavioral model SNM (mV)",
               ylabel="Predicted SNM (mV)", title=f'{name.replace("_", " ").title()}\nMAE = {records[name]["mae_mv"]:.2f} mV')
        ax.set_aspect("equal")
        ax.grid(alpha=0.15)
    axes[0].legend(loc="upper left", fontsize=8)
    fig.suptitle("Initial baselines at 1.0 V | 2,000 held-out synthetic samples")
    fig.savefig(figures / "baseline_predictions.png", dpi=130)
    plt.close(fig)
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
