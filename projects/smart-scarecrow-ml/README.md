# Smart Scarecrow ML

Reproducible Bird / Non-bird audio classification with a fixed FFT baseline, Random Forest, source-aware evaluation, and ATmega328P / Arduino UNO integration.

**Status: working research prototype, not field validated.** The public-data model improves classification accuracy, but the current experiments do **not** demonstrate fewer false alarms than the FFT baseline. The original local recordings alone are insufficient for an independent evaluation.

中文完整说明：[运行指南](docs/RUNNING_ZH.md) · [技术报告](docs/TECHNICAL_REPORT_ZH.md) · [硬件方案](docs/HARDWARE_ZH.md) · [数据说明](docs/DATASET_CARD.md)

## What is implemented

- Immutable original experiments and SHA-256 integrity verification.
- Audio/provenance/license audit; explicit recording groups and duplicate checks.
- 37 audio features: RMS, zero crossings, FFT peak, four band-energy ratios, spectral centroid/bandwidth, 13 MFCC means and standard deviations.
- Fixed FFT rule and 200-tree Random Forest using identical preprocessing.
- Recording-disjoint train/test splits; a separate validation-only threshold experiment.
- Offline prediction, optional Mac microphone inference, serial acquisition with CRC and gap detection.
- Compiled UNO sketches for A1 acquisition, D7 LED testing and full-system host ML control; a separate SRAM repair of the original master.
- Automatic figures, saved predictions, model cards, dependency lock, tests and CI configuration.

## Architecture

```mermaid
flowchart LR
    A[Local WAV / licensed ESC-50 subset] --> B[Manifest and quality audit]
    B --> C[Mono + polyphase resampling to 9600 Hz]
    C --> D[0.25 s windows / 37 features]
    D --> E[Fixed FFT baseline]
    D --> F[Random Forest on Mac]
    G[Original recording ID / official folds] --> H[Disjoint training, validation and test]
    H --> F
    F --> I[Scores, decisions and saved reports]
    I --> J[Debounce + cooldown + heartbeat]
    J --> K[UNO controller / D7 RGB LED first]
```

The UNO is an acquisition/control device. The Python Random Forest and MFCC pipeline run on the host; they are not embedded in the UNO.

## Quick start (Python 3.12)

From the portfolio repository, enter `projects/smart-scarecrow-ml`. On the original Mac, the project also remains at `~/Documents/Smart-Scarecrow-ML`. For a fresh checkout, create a Python 3.12 virtual environment first:

```bash
cd projects/smart-scarecrow-ml
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m scarecrow --help
```

For a fresh checkout, create the environment first with `python3.12 -m venv .venv`. `requirements-lock-macos.txt` records the exact versions tested on this Mac. Linux microphone use also needs PortAudio; file inference does not need microphone access.

Reproduce the local annotated-data demonstration (audio stays private):

```bash
python -m scarecrow run --demo-model
```

Reproduce the licensed public-data experiment:

```bash
# Downloads missing audio; verifies existing files against saved hashes.
python scripts/download_esc50_subset.py
python -m scarecrow run --manifest data/manifest_esc50.csv
# Optional, separate protocol: folds 1–3 train, 4 select threshold, 5 test.
python -m scarecrow run --manifest data/manifest_esc50.csv --calibrate
```

Every run creates a new directory in `results/runs/`. Existing output paths are refused. Models are local, trusted `joblib` files; do not load models from untrusted sources.

## Actual results — 21 November 2026

ESC-50 subset: 160 real five-second clips downloaded; 2 excluded by a fixed quality rule; 158 used. The retained data contains 132 original recording groups. The same Freesound recording ID never crosses partitions. The fixed test is official fold 5: **32 clips, 28 recording groups, 640 windows**. This is a custom binary subset, not the standard ESC-50 50-class benchmark.

| Window-level test measure | FFT rule | RF, threshold 0.5 | RF, validation-selected threshold |
|---|---:|---:|---:|
| Accuracy | 55.78% | 83.75% | 70.00% |
| Bird precision | 69.47% | 79.83% | 79.91% |
| Bird recall | 20.63% | 90.31% | 53.44% |
| Bird F1 | 0.3181 | 0.8475 | 0.6404 |
| Non-bird false-positive rate | 9.06% | 22.81% | 13.44% |

RF at 0.5 trains on folds 1–4. The threshold experiment trains on folds 1–3 and selects its threshold, 0.751742, using fold 4 only; it does not refit. The two RF columns therefore differ in training data as well as decision threshold. The validation FPR was 4.38%, but the test FPR rose to 13.44%. We report this failure rather than tuning on test results.

At the **five-second clip level**, mean-score aggregation yields 90.63% accuracy for the default RF versus 56.25% for FFT. This is a different evaluation unit. All 40 held-out cricket windows were false positives for both RF variants; stronger hard-negative coverage and real field recordings are needed.

![Window-level model performance](docs/figures/benchmark/model_performance.png)

![Confusion matrices](docs/figures/benchmark/confusion_matrices.png)

Original private dataset: two 1.4-second clips, one source per class. It yields 10 complete windows and **N/A** test metrics. Demo-model predictions are not accuracy measurements. The ESC-50 model also misclassified four of five windows in the existing voice clip, a useful warning about domain shift.

Machine-readable evidence is in [docs/experiments](docs/experiments/). The complete feature tables and trained models remain in local `results/runs/` directories.

## Hardware status

| UNO sketch | Flash | Static SRAM | Scope |
|---|---:|---:|---|
| `uno_audio_capture` | 2,422 bytes | 1,222 bytes | A1, 8 kHz nominal, 10-bit samples, binary serial at 250000 baud |
| `uno_controller` | 2,392 bytes | 247 bytes | D7 RGB LED, heartbeat, 800 ms pulse, 10 s cooldown |
| `scarecrow_host_ml` | 7,634 bytes | 356 bytes | Actual full sensor/servo pin map; starts disarmed |
| `legacy_master_fixed` | 12,370 bytes | 939 bytes | Original master SRAM repair; original was 1,767 bytes |

These are compiler measurements, not on-board timing tests. The user also ran the new legacy capture tool locally: 30 real frames / 7,680 ADC samples were saved and analyzed; they remain unlabeled and discontinuous. No new sketch was uploaded during software verification. See the hardware guide before replacing any existing scarecrow firmware. The 8 kHz acquisition path has a 4 kHz Nyquist limit; resampling it to 9.6 kHz cannot restore missing frequencies.

## Repository layout

```text
scarecrow/             reusable audio, dataset, model, inference and serial modules
scripts/               public-data download and local verification helpers
firmware/              independent UNO acquisition and controller sketches
tests/                 synthetic software fixtures, never used as experiment data
data/manifest*.csv     labels, provenance, source groups, licenses and official folds
docs/                  running guide, report, dataset card, figures and evidence
results/runs/          local immutable runs, feature CSVs and model files (ignored)
backups/               original 29-file backup and hashes (ignored)
*.py                   original experimental scripts, preserved unchanged
```

## Data and publication

The ESC-50 dataset is distributed under **CC BY-NC 3.0**, with individual source credits and license tags retained in [the attribution bundle](docs/third_party/esc50/SELECTED_ATTRIBUTIONS.txt). See the [official dataset](https://github.com/karolpiczak/ESC-50) and [upstream license](https://github.com/karolpiczak/ESC-50/blob/master/LICENSE). This public project publishes code, documentation and curated experiment figures; source audio and model binaries are excluded. Audio, backups, environments and model binaries are excluded by `.gitignore`.

The existing XC1002645 recording's exact license is unresolved; its ID3 tags identify W. Agster. The existing voice recording's ownership/consent is unconfirmed. Code licensing remains an owner decision; third-party audio is not covered by a future repository code license. See [publication notes](docs/PUBLICATION.md).
