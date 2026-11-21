"""Source-disjoint evaluation with an explicit insufficient-data state."""
from collections import Counter
import importlib.metadata

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import GroupShuffleSplit

from .dataset import LABELS
from .features import fft_baseline
from .io import write_csv, write_json

META = {"clip_id", "audio_path", "label", "source_recording", "source_group", "window_start_sec", "original_start_sec",
        "dataset_fold", "category", "annotation_level"}
BASELINE = {"min_hz": 2000.0, "max_hz": 4500.0, "rms_floor": 0.005}
SEED = 42


def grouped_split(table):
    """At least 3 sources/class: 2 train, 1 test. A project policy, not a theorem."""
    y = np.array([LABELS[t["label"]] for t in table])
    groups = np.array([t["source_group"] for t in table])
    counts = {k: len(set(groups[y == v])) for k, v in LABELS.items()}
    if min(counts.values()) < 3:
        return None, f"Need >=3 independent source groups per class; found {counts}. Window count does not create independence."
    folds = [r.get("dataset_fold", "") for r in table]
    if any(folds):
        if not all(f in {"1", "2", "3", "4", "5"} for f in folds):
            raise ValueError("Cannot mix official folds with missing/invalid fold metadata")
        train = np.flatnonzero(np.array(folds) != "5")
        test = np.flatnonzero(np.array(folds) == "5")
        if set(groups[train]) & set(groups[test]):
            raise ValueError("Source group crosses official train/test folds")
        if not all(len(set(groups[train][y[train] == label])) >= 2 and
                   len(set(groups[test][y[test] == label])) >= 1 for label in (0, 1)):
            return None, "Official fold 5 lacks sufficient source/class coverage"
        return (train, test), None
    # Search only class/group coverage, NEVER model scores.
    splitter = GroupShuffleSplit(n_splits=256, test_size=0.25, random_state=SEED)
    for train, test in splitter.split(np.zeros(len(y)), y, groups):
        valid = all(len(set(groups[train][y[train] == label])) >= 2 and
                    len(set(groups[test][y[test] == label])) >= 1 for label in (0, 1))
        if valid:
            assert not set(groups[train]) & set(groups[test])
            return (train, test), None
    return None, "No source-disjoint split with both classes and required source coverage was found."


def metric_report(y, pred):
    p, r, f, _ = precision_recall_fscore_support(y, pred, labels=[1], average=None, zero_division=0)
    return {"accuracy": float(accuracy_score(y, pred)), "precision_bird": float(p[0]),
            "recall_bird": float(r[0]), "f1_bird": float(f[0]),
            "confusion_matrix": confusion_matrix(y, pred, labels=[0, 1]).tolist(),
            "class_order": ["non_bird", "bird"],
            "per_class": classification_report(y, pred, labels=[0, 1], target_names=["non_bird", "bird"],
                                                output_dict=True, zero_division=0),
            "zero_division_policy": "undefined precision/recall are 0, inspect support"}


def fit_classifier(x, y, groups):
    counts = Counter(groups)
    weights = np.array([1.0 / counts[g] for g in groups])
    clf = RandomForestClassifier(n_estimators=200, max_depth=8, min_samples_leaf=1,
                                 class_weight="balanced_subsample", random_state=SEED, n_jobs=1)
    clf.fit(x, y, sample_weight=weights)
    return clf


def choose_threshold(y, scores, max_false_positive_rate=0.05):
    """Predeclared low-false-alarm operating point, chosen on validation only.

    Maximize bird recall subject to <=5% negative-window FPR, then minimize FPR,
    then prefer the lower threshold. No calibrated probability claim.
    """
    y, scores = np.asarray(y), np.asarray(scores)
    if set(y) != {0, 1} or not np.isfinite(scores).all():
        raise ValueError("Threshold selection requires finite scores and both validation classes")
    candidates = sorted(set([0.5, 1.0000000000000002] + [float(s) for s in scores if s >= 0.5]))
    choices = []
    for threshold in candidates:
        pred = scores >= threshold
        fpr = float(pred[y == 0].mean())
        recall = float(pred[y == 1].mean())
        if fpr <= max_false_positive_rate:
            choices.append((recall, -fpr, -threshold, threshold))
    return max(choices)[3]


def train_evaluate(table, audit, config, output, allow_demo=False, calibrate=False):
    if not table:
        raise ValueError("No valid complete audio windows; see manifest/quality checks")
    names = [k for k in table[0] if k not in META]
    x = np.array([[r[k] for k in names] for r in table], dtype=float)
    y = np.array([LABELS[r["label"]] for r in table])
    groups = np.array([r["source_group"] for r in table])
    split, reason = grouped_split(table)
    report = {"status": "insufficient_data", "reason": reason, "seed": SEED,
              "baseline_parameters": BASELINE, "baseline_origin": "illustrative fixed values, not tuned",
              "positive_class": "bird", "evaluation_unit": "complete 0.25 s window; inherits clip labels",
              "split_strategy": "official fold 5 test, folds 1-4 train" if any(r.get("dataset_fold") for r in table) else "source-group shuffle, seed 42",
              "metrics": {"fft_baseline": None, "random_forest": None},
              "limitations": "Exploratory only. Correlated windows are not independent trials; no field or hardware validation."}
    clf = None
    decision_threshold = 0.5
    trained_indices = np.arange(len(table))
    if split is not None:
        train, test = split
        if calibrate:
            # Deliberately use official folds 1-3 / 4 / 5; refuse a silent fallback.
            if not all(r.get("dataset_fold") in {"1", "2", "3", "4", "5"} for r in table):
                raise ValueError("--calibrate requires official 1-5 fold metadata")
            validation = np.array([i for i in train if table[i]["dataset_fold"] == "4"])
            train = np.array([i for i in train if table[i]["dataset_fold"] != "4"])
            if any(set(groups[a]) & set(groups[b]) for a, b in [(train, validation), (train, test), (validation, test)]):
                raise ValueError("Source leakage across train/validation/test")
            if set(y[train]) != {0, 1} or set(y[validation]) != {0, 1}:
                raise ValueError("Training and validation must each contain both classes")
        trained_indices = train
        clf = fit_classifier(x[train], y[train], groups[train])
        bird_idx = list(clf.classes_).index(1)
        if calibrate:
            val_scores = clf.predict_proba(x[validation])[:, bird_idx]
            decision_threshold = choose_threshold(y[validation], val_scores)
            report["threshold_selection"] = {"threshold": decision_threshold, "max_validation_fpr": 0.05,
                    "method": "maximize validation recall under FPR <= 0.05, then minimize FPR; no test optimization",
                    "validation_windows": len(validation), "validation_groups": sorted(set(groups[validation])),
                    "validation_metrics": metric_report(y[validation], val_scores >= decision_threshold)}
            report["split_strategy"] = "official folds 1-3 train, 4 threshold validation, 5 test; no refit"
            write_csv(output / "validation_predictions.csv", [{"clip_id": table[i]["clip_id"], "source_group": groups[i],
                        "truth": int(y[i]), "bird_score": float(score)} for i, score in zip(validation, val_scores)])
        probs = clf.predict_proba(x[test])[:, bird_idx]
        rf_pred = (probs >= decision_threshold).astype(int)
        baseline_pred = np.array([fft_baseline(table[i], **BASELINE) for i in test])
        report.update(status="exploratory_holdout", reason=None,
                      train_windows=len(train), test_windows=len(test),
                      train_groups=sorted(set(groups[train])), test_groups=sorted(set(groups[test])))
        report["metrics"] = {"fft_baseline": metric_report(y[test], baseline_pred),
                             "random_forest": metric_report(y[test], rf_pred)}
        assignment = []
        parts = [("train", train), ("test", test)]
        if calibrate:
            parts.insert(1, ("validation", validation))
        for part, indices in parts:
            assignment.extend({**{k: table[i][k] for k in META}, "split": part} for i in indices)
        write_csv(output / "split_assignment.csv", assignment, sorted(META) + ["split"])
        clip_predictions = []
        for clip_id in sorted({table[i]["clip_id"] for i in test}):
            positions = [j for j, i in enumerate(test) if table[i]["clip_id"] == clip_id]
            first = test[positions[0]]
            clip_predictions.append({"clip_id": clip_id, "source_group": table[first]["source_group"],
                     "truth": int(y[first]), "rf_prediction": int(probs[positions].mean() >= decision_threshold),
                     "bird_score_mean": float(probs[positions].mean()),
                     "fft_prediction": int(baseline_pred[positions].mean() >= 0.5)})
        report["clip_metrics"] = {name: metric_report([r["truth"] for r in clip_predictions], [r[key] for r in clip_predictions])
                                  for name, key in [("fft_baseline", "fft_prediction"), ("random_forest", "rf_prediction")]}
        report["clip_aggregation"] = f"RF mean uncalibrated score >={decision_threshold}; FFT majority vote >=0.5; complete windows only. Threshold selected on windows, not calibrated for clip metrics."
        write_csv(output / "test_clip_predictions.csv", clip_predictions)
        write_csv(output / "test_predictions.csv", [{"clip_id": table[i]["clip_id"], "source_group": groups[i],
                    "window_start_sec": table[i]["window_start_sec"], "truth": int(y[i]),
                    "fft_prediction": int(base), "rf_prediction": int(rf), "bird_score": float(prob)}
                   for i, base, rf, prob in zip(test, baseline_pred, rf_pred, probs)])
    elif allow_demo and len(set(y)) == 2:
        clf = fit_classifier(x, y, groups)
        report["demo_model"] = "Fitted on all available clips solely to exercise inference. No accuracy reported."
    if clf is not None:
        status = "demo_unvalidated" if split is None else "exploratory_unvalidated"
        filename = "model_demo.joblib" if split is None else "model_holdout.joblib"
        used_paths = {table[i]["audio_path"] for i in trained_indices}
        card = {"schema_version": 1, "status": status, "deployable": False,
                "feature_config": config.to_dict(), "feature_names": names,
                "baseline_parameters": BASELINE, "seed": SEED,
                "decision_threshold": decision_threshold,
                "training_groups": sorted(set(groups[trained_indices])),
                "training_audio_sha256": [a["audio_sha256"] for a in audit if a["audio_path"] in used_paths],
                "classifier_parameters": clf.get_params(),
                "versions": {p: importlib.metadata.version(p) for p in ["numpy", "scipy", "scikit-learn", "soundfile", "joblib"]},
                "score_interpretation": "Uncalibrated tree-vote score, not a real-world probability or confidence guarantee."}
        with (output / filename).open("xb") as f:
            joblib.dump({"classifier": clf, **card}, f)
        write_json(output / "model_card.json", card)
        write_csv(output / "feature_importances.csv", [{"feature": n, "importance": float(v)}
                                                       for n, v in zip(names, clf.feature_importances_)])
        report["model_file"] = filename
    write_json(output / "evaluation.json", report)
    return report


def load_model(path, allow_demo=False):
    """Only load trusted local joblib files: pickle deserialization executes code."""
    model = joblib.load(path)
    if model.get("schema_version") != 1:
        raise ValueError("Unsupported model schema")
    if model["status"] == "demo_unvalidated" and not allow_demo:
        raise ValueError("Demo model: inference requires --allow-demo; it is not field validated")
    return model
