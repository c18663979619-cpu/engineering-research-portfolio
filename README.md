# Mohan Chen | Machine Learning, Signal Processing & Electronic Engineering

Engineering projects exploring **machine learning for sensor data, digital signal processing and embedded systems**, alongside circuit design and numerical modeling. My featured project, **Smart Scarecrow**, connects acoustic feature extraction and model evaluation with an Arduino sensing platform.

**Tools and methods explored in this portfolio** include Python, NumPy, scikit-learn, FFT/STFT, MFCCs, Random Forest classification, regression baselines, Monte Carlo simulation and Arduino C++. Each project links its methods to reproducible artifacts, measured results and current limitations.

## Selected projects

| Project | Engineering question | Work demonstrated | Evidence |
|---|---|---|---|
| [Smart Scarecrow — Audio machine learning & Arduino sensing](projects/smart-scarecrow-ml/) | How well can acoustic features distinguish bird sounds from environmental interference? | Python, NumPy, scikit-learn, FFT/STFT, MFCCs, Random Forest, evaluation by recording source and error analysis | 83.75% held-out accuracy, 0.8475 Bird F1, saved metrics, original Arduino code and real ADC capture |
| [Behavioral SRAM stability](https://github.com/c18663979619-cpu/sram-reliability-monte-carlo/tree/70023883ea8ac17d4296a5396efb0eae3d4ac80e) | How do threshold mismatch and supply assumptions affect static stability? | Python/NumPy modeling, Monte Carlo analysis, numerical verification, uncertainty | Executed notebook, 10,000 samples, four figures, data and tests |
| [BJT oscillator and PCB](projects/bjt-astable-multivibrator-pcb/) | How can an approximately 3 Hz oscillator be analyzed and translated into a compact PCB? | Circuit calculations, SPICE interpretation, schematic capture, placement and routing | Reported waveforms, native Fusion exports, BOM, check records |
| [ML surrogate for behavioral SRAM stability — In progress](projects/ml-sram-surrogate/) | Can regression approximate numerical stability calculations, and where does it fail? | Initial dataset preparation and NumPy regression baselines; nonlinear methods planned | Reproducible split, initial error table, prediction plot |

## Smart Scarecrow — Audio machine learning & Arduino sensing

An acoustic classification project connecting **Python machine learning, signal processing and embedded sensing**. Built on my school Smart Scarecrow controller, the ML extension investigates how to distinguish Bird from Non-bird sounds and how classification errors affect a physical alarm system.

**ML workflow demonstrated**

- **Audio preparation with Python and NumPy.** Audit audio provenance and quality, convert to mono, resample to 9.6 kHz and extract complete 0.25-second windows.
- **Signal processing and feature engineering.** Extract **37 acoustic features** using FFT/STFT, RMS, zero-crossing rate, frequency-band energy, spectral centroid and bandwidth, plus the means and standard deviations of 13 MFCCs.
- **Supervised learning with scikit-learn.** Train a **200-tree Random Forest** and compare it with a fixed FFT rule using the same preprocessing.
- **Evaluation on unseen recording sources.** Train on ESC-50 folds 1–4 and test on fold 5, keeping windows from the same original recording together. A separate experiment uses fold 4 for threshold selection.
- **Model assessment and error analysis.** Inspect precision, recall, F1, confusion matrices and errors by sound category, including false positives on cricket recordings and poor transfer to a local voice clip.

**Held-out results**

Custom ESC-50 Bird/Non-bird subset, evaluated on **640 windows from 32 clips and 28 original recording sources**. Windows from each source are correlated.

| Window-level measure | Fixed FFT baseline | Random Forest |
|---|---:|---:|
| Accuracy | 55.78% | **83.75%** |
| Bird precision | 69.47% | **79.83%** |
| Bird recall | 20.63% | **90.31%** |
| Bird F1 | 0.3181 | **0.8475** |
| Non-bird false-positive rate | 9.06% | 22.81% |

The Random Forest improves accuracy and Bird F1 while producing more non-bird false positives. The FFT comparator is an experimental software rule. Field false-alarm reduction remains to be validated against the original Arduino controller.

![Smart Scarecrow held-out model evaluation](projects/smart-scarecrow-ml/docs/figures/benchmark/model_performance.png)

**Arduino foundation and contribution.** I developed the original school-project control program integrating **two ultrasonic sensors, two PIR sensors and a Waveshare sound sensor** with two servo arms, RGB indication and a buzzer. It includes a standby/alarm/cooldown state machine and a 64-point FFT acoustic filter. The later audio/ML extension used **AI-assisted implementation**, with methods, code and evaluation records available for inspection.

**Current prototype.** Random Forest inference and MFCC extraction run on the host computer. Real board acquisition produced **30 frames / 7,680 ADC samples**, currently unlabelled and discontinuous. The new actuator firmware has been compiled, with assembled-system testing and continuous target-sensor validation still pending. A separate firmware revision reduces static SRAM from **1,767 B to 939 B**.

[Explore the project](projects/smart-scarecrow-ml/) · [Feature extraction code](projects/smart-scarecrow-ml/scarecrow/features.py) · [Training and evaluation code](projects/smart-scarecrow-ml/scarecrow/model.py) · [Saved experiment results](projects/smart-scarecrow-ml/docs/experiments/) · [Technical report](projects/smart-scarecrow-ml/docs/TECHNICAL_REPORT_ZH.md)

[Original Arduino master](projects/smart-scarecrow-ml/firmware/originals/5CCE2EMP_Control_SG90_HC-SR04/5CCE2EMP_Control_SG90_HC-SR04.ino) · [Hardware case study](projects/smart-scarecrow-ml/docs/HARDWARE_CASE_STUDY.md)

## Computational modeling: behavioral SRAM stability

**Method.** Model a pair of cross-coupled inverter voltage-transfer curves, apply independent threshold variation, and extract static noise margin over 10,000 samples and nine supply voltages. Compare the batched calculation against an independent reference and quantify finite-sample uncertainty.

**Result.** At 1.0 V and assumed threshold σ = 40 mV, mean SNM is **229.15 mV**. **8/10,000** samples fall below the chosen 180 mV criterion; the 95% Wilson interval is **0.041–0.158%**. Numerical comparisons on 66 cases at three supplies agree within **0.002 mV** at the default grid.

![Behavioral SNM and below-criterion fraction versus supply voltage](assets/sram-supply-sweep.png)

*Review snapshot using a fixed physical gain of 14 V⁻¹. The model is behavioral and uncalibrated; the results do not establish read/write yield or silicon reliability. This figure and the linked immutable revision belong to the same revision.*

[Read the study and reproduce it →](https://github.com/c18663979619-cpu/sram-reliability-monte-carlo/tree/70023883ea8ac17d4296a5396efb0eae3d4ac80e)

## Circuit and hardware design: BJT astable multivibrator

**Method.** Size the timing network, interpret transient switching, adapt the schematic for a battery and LEDs, and place/route a two-layer through-hole PCB. Completed as an individual 5CCE2EMP course design project.

**Result.** The report's pre-LED simulation gives approximately **2.91 Hz**. The final CAD board is approximately **41.9 × 44.1 mm**, with **one via and zero airwires**. Native schematic/board exports, analytical calculations, and a traceable BOM are included.

![Fusion CAD preview of the BJT oscillator board](projects/bjt-astable-multivibrator-pcb/docs/figures/pcb-3d-view.png)

*The waveform predates the LED adaptation. A later PCB check shows 12 warnings awaiting review; fabrication and bench measurements are not documented. The case study explains these verification boundaries and the next steps.*

[Explore the design case study →](projects/bjt-astable-multivibrator-pcb/)

## Machine learning for circuit analysis — In progress

**Question.** Can a learned surrogate approximate the behavioral SRAM calculation accurately enough to support faster parameter studies?

**Current milestone.** Reuse 10,000 synthetic samples at 1.0 V, fit training-mean and linear-regression baselines, and evaluate on 2,000 held-out samples. Both give approximately **9.57 mV MAE**; raw linear regression offers no meaningful improvement. Nonlinear modeling, multi-voltage generalization, and timing experiments are planned.

[View the initial experiment and roadmap →](projects/ml-sram-surrogate/)

## Research approach

- Start with a question and a measurable criterion.
- Make assumptions visible and compare theory with available evidence.
- Preserve sources and parameters so another person can inspect the work.
- Test numerical methods and separate simulation, design checks, and measurement.
- Use discrepancies to identify the next useful experiment.

**Current interests** include machine learning, signal processing, intelligent sensing, embedded systems, AI hardware, electronic circuits and reliability modeling.

