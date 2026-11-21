"""Synthetic fixtures test software behavior, NEVER project model performance."""
import csv
import json
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from scarecrow.audio import FeatureConfig, load_audio, windows
from scarecrow.dataset import build_dataset
from scarecrow.features import extract_features, fft_baseline
from scarecrow.inference import TriggerGate, predict_file
from scarecrow.io import write_json
from scarecrow.model import grouped_split, load_model, metric_report, train_evaluate
from scarecrow.serial_audio import PacketParser, encode_packet

CONFIG = FeatureConfig()


def tone(hz, sr=9600, seconds=0.25, dc=0.0):
    return dc + 0.2 * np.sin(2 * np.pi * hz * np.arange(round(sr * seconds)) / sr)


def test_tone_frequency_rms_and_band_partition():
    features = extract_features(tone(3000, dc=0.3))
    assert features["rms"] == pytest.approx(0.2 / np.sqrt(2), rel=0.002)
    assert features["peak_frequency_hz"] == pytest.approx(3000, abs=37.5)
    assert features["centroid_mean_hz"] == pytest.approx(3000, abs=50)
    assert features["band_2000_4000_ratio"] > 0.99
    assert sum(v for k, v in features.items() if k.startswith("band_")) == pytest.approx(1)
    assert fft_baseline(features) == 1
    assert len(features) == 37


@pytest.mark.parametrize("constant", [0.0, 0.7])
def test_silence_and_dc_are_finite_and_do_not_trigger(constant):
    features = extract_features(np.full(CONFIG.window_samples, constant))
    assert np.isfinite(list(features.values())).all()
    assert features["rms"] < 1e-12
    assert features["peak_frequency_hz"] == 0
    assert fft_baseline(features) == 0


def test_invalid_and_short_audio():
    with pytest.raises(ValueError):
        extract_features(np.zeros(256))
    with pytest.raises(ValueError):
        extract_features(np.full(2400, np.nan))
    assert len(list(windows(np.zeros(13440), CONFIG))) == 5
    with pytest.raises(ValueError):
        FeatureConfig(sample_rate=8000)


def test_stereo_pcm_and_resampling(tmp_path):
    path = tmp_path / "stereo.wav"
    y = tone(1500, sr=48000)
    sf.write(path, np.column_stack([y, y]), 48000, subtype="PCM_24")
    mono, sr = load_audio(path, 9600)
    assert sr == 9600 and len(mono) == 2400
    assert extract_features(mono)["peak_frequency_hz"] == pytest.approx(1500, abs=37.5)


def make_manifest(tmp_path, specs):
    rows = []
    for i, (label, source, hz) in enumerate(specs):
        file = tmp_path / f"clip{i}.wav"
        sf.write(file, tone(hz, seconds=0.5), 9600)
        rows.append(dict(clip_id=f"clip{i}", audio_path=file.name, label=label,
                         source_recording=source, source_group=source, original_path=file.name,
                         start_sec="0", end_sec="0.5", label_verified="yes", license_status="synthetic_test_only"))
    manifest = tmp_path / "manifest.csv"
    with manifest.open("w", newline="") as f:
        writer = csv.DictWriter(f, rows[0].keys()); writer.writeheader(); writer.writerows(rows)
    return manifest


def test_duplicates_merge_even_with_different_source_ids(tmp_path):
    path = make_manifest(tmp_path, [("bird", "A", 3000), ("bird", "B", 3000), ("non_bird", "C", 300)])
    table, audit, summary, _ = build_dataset(tmp_path, path, CONFIG)
    assert summary["independent_groups_by_label"] == {"non_bird": 1, "bird": 1}
    assert len(table) == 4
    assert audit[0]["effective_group"] == audit[1]["effective_group"]
    assert summary["skipped"][0]["reasons"] == ["exact_duplicate_clip"]


def test_contradictory_duplicate_labels_fail(tmp_path):
    path = make_manifest(tmp_path, [("bird", "A", 3000), ("non_bird", "B", 3000)])
    with pytest.raises(ValueError, match="contradictory"):
        build_dataset(tmp_path, path, CONFIG)


def test_insufficient_sources_no_fake_metrics_and_demo_guard(tmp_path):
    path = make_manifest(tmp_path, [("bird", "A", 3000), ("non_bird", "B", 300)])
    table, audit, summary, _ = build_dataset(tmp_path, path, CONFIG)
    output = tmp_path / "run"; output.mkdir()
    report = train_evaluate(table, audit, CONFIG, output, allow_demo=True)
    assert report["status"] == "insufficient_data"
    assert report["metrics"] == {"fft_baseline": None, "random_forest": None}
    with pytest.raises(ValueError, match="--allow-demo"):
        load_model(output / "model_demo.joblib")
    model = load_model(output / "model_demo.joblib", allow_demo=True)
    result = predict_file(tmp_path / "clip0.wav", model)
    assert result["known_training_file"] is True and len(result["predictions"]) == 2


def test_source_holdout_complete_and_deterministic(tmp_path):
    specs = [("bird", f"B{i}", 2600 + i * 150) for i in range(3)]
    specs += [("non_bird", f"N{i}", 200 + i * 150) for i in range(3)]
    path = make_manifest(tmp_path, specs)
    table, audit, _, _ = build_dataset(tmp_path, path, CONFIG)
    (train, test), reason = grouped_split(table)
    assert reason is None
    assert not {table[i]["source_group"] for i in train} & {table[i]["source_group"] for i in test}
    assert {table[i]["label"] for i in test} == {"bird", "non_bird"}
    np.testing.assert_array_equal(train, grouped_split(table)[0][0])
    output = tmp_path / "synthetic_software_test"; output.mkdir()
    report = train_evaluate(table, audit, CONFIG, output)
    assert report["status"] == "exploratory_holdout"
    assert sum(map(sum, report["metrics"]["random_forest"]["confusion_matrix"])) == len(test)
    split_rows = list(csv.DictReader((output / "split_assignment.csv").open()))
    for group in {r["source_group"] for r in split_rows}:
        assert len({r["split"] for r in split_rows if r["source_group"] == group}) == 1


def test_metric_positive_class_and_matrix_order():
    m = metric_report([0, 0, 1, 1], [0, 1, 0, 1])
    assert m["confusion_matrix"] == [[1, 1], [1, 1]]
    assert m["accuracy"] == 0.5 and m["f1_bird"] == 0.5


def test_exclusive_output(tmp_path):
    p = tmp_path / "important.json"
    write_json(p, {"original": True})
    with pytest.raises(FileExistsError):
        write_json(p, {"original": False})
    assert json.loads(p.read_text())["original"] is True


def test_serial_partial_packets_crc_and_resynchronization():
    parser = PacketParser()
    packet = encode_packet(7, list(range(256)))
    assert parser.feed(b"startup noise" + packet[:80]) == []
    result = parser.feed(packet[80:])
    assert result[0]["sequence"] == 7
    np.testing.assert_array_equal(result[0]["samples"], np.arange(256))
    bad = bytearray(packet); bad[-1] ^= 1
    result = parser.feed(bad + encode_packet(8, [512] * 256))
    assert parser.bad_packets == 1 and result[0]["sequence"] == 8


def test_trigger_debounce_cooldown_and_silence():
    gate = TriggerGate()
    positive = {"bird_score": 0.9, "rms": 0.02}
    assert not gate.update(positive, 0)
    assert not gate.update(positive, .25)
    assert gate.update(positive, .5)
    assert not gate.update(positive, .75)
    gate.reset()
    assert not gate.update({"bird_score": 1, "rms": 0}, 20)
    assert not gate.update(positive, 20.25)
    assert not gate.update(positive, 20.5)
    assert gate.update(positive, 20.75)


def test_official_fold_split_keeps_all_related_takes_together():
    table = [{"label": label, "source_group": f"{label}_{fold}", "dataset_fold": str(fold)}
             for label in ["bird", "non_bird"] for fold in range(1, 6) for _ in range(3)]
    (train, test), reason = grouped_split(table)
    assert reason is None and len(test) == 6
    assert all(table[i]["dataset_fold"] == "5" for i in test)
    table[-1]["source_group"] = "bird_1"
    with pytest.raises(ValueError, match="crosses"):
        grouped_split(table)


def test_segment_cli_bounds_and_no_overwrite(tmp_path):
    from scarecrow.__main__ import main
    source, output = tmp_path / "input.wav", tmp_path / "segment.wav"
    sf.write(source, tone(1000, seconds=1), 9600)
    argv = ["segment", "--audio", str(source), "--start", "0.1", "--end", "0.6", "--output", str(output)]
    main(argv)
    assert sf.info(output).frames == 4800
    with pytest.raises(SystemExit) as error:
        main(argv)
    assert error.value.code == 2


def test_live_demo_cannot_actuate_before_opening_devices(tmp_path):
    from scarecrow.live import live
    with pytest.raises(ValueError, match="demo models cannot actuate"):
        live({"status": "demo_unvalidated"}, tmp_path / "events.json", serial_port="fake", enable_actuator=True)


def test_threshold_is_chosen_on_validation_false_positive_constraint():
    from scarecrow.model import choose_threshold
    y = np.array([0] * 20 + [1] * 20)
    scores = np.array(list(np.linspace(0.1, 0.85, 20)) + list(np.linspace(0.6, 1.0, 20)))
    threshold = choose_threshold(y, scores)
    assert np.mean(scores[:20] >= threshold) <= 0.05
    assert threshold > 0.5


def test_calibration_never_fits_validation_or_test_groups(tmp_path):
    specs = [(label, f"{label}_{fold}", (2400 if label == "bird" else 200) + fold * 75)
             for label in ["bird", "non_bird"] for fold in range(1, 6)]
    path = make_manifest(tmp_path, specs)
    table, audit, _, _ = build_dataset(tmp_path, path, CONFIG)
    for row in table:
        row["dataset_fold"] = row["source_group"].rsplit("_", 1)[-1]
    output = tmp_path / "calibration_test"; output.mkdir()
    report = train_evaluate(table, audit, CONFIG, output, calibrate=True)
    model = load_model(output / "model_holdout.joblib")
    assert all(g.endswith(("_1", "_2", "_3")) for g in model["training_groups"])
    assert all(g.endswith("_4") for g in report["threshold_selection"]["validation_groups"])
    assert all(g.endswith("_5") for g in report["test_groups"])
    assert model["decision_threshold"] == report["threshold_selection"]["threshold"]


def test_legacy_frame_parser_rejects_partial_and_out_of_range_frames():
    from scarecrow.legacy_serial import LegacyFrameParser
    parser = LegacyFrameParser()
    parser.feed("FRAME_START,1,256")
    for i in range(256):
        parser.feed(f"Audio:{i}")
    result = parser.feed("FRAME_END,1")
    assert result["frame_id"] == 1 and result["samples"] == list(range(256))
    parser.feed("FRAME_START,2,256")
    parser.feed("Audio:1024")
    assert parser.feed("FRAME_END,2") is None
    parser.feed("FRAME_START,3,256")
    parser.feed("Audio:512")
    assert parser.feed("FRAME_END,3") is None
    assert parser.rejected >= 2
