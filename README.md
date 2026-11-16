# Mohan Chen | Engineering Research & Design Portfolio

Projects exploring **electronics and computer engineering** through circuit analysis, numerical modeling, and hardware design. Each case study connects an engineering question with an explicit method, evidence, reproducible artifacts, and limitations.

## Selected projects

| Project | Engineering question | Work demonstrated | Evidence |
|---|---|---|---|
| [Behavioral SRAM stability](https://github.com/c18663979619-cpu/sram-reliability-monte-carlo/tree/portfolio-review-2026-11-16) | How do threshold mismatch and supply assumptions affect static stability? | Python/NumPy modeling, Monte Carlo analysis, numerical verification, uncertainty | Executed notebook, 10,000 samples, four figures, data and tests |
| [BJT oscillator and PCB](projects/bjt-astable-multivibrator-pcb/) | How can an approximately 3 Hz oscillator be analyzed and translated into a compact PCB? | Circuit calculations, SPICE interpretation, schematic capture, placement and routing | Reported waveforms, native Fusion exports, BOM, check records |

## 01 · Computational modeling: behavioral SRAM stability

**Method.** Model a pair of cross-coupled inverter voltage-transfer curves, apply independent threshold variation, and extract static noise margin over 10,000 samples and nine supply voltages. Compare the batched calculation against an independent reference and quantify finite-sample uncertainty.

**Result.** At 1.0 V and assumed threshold σ = 40 mV, mean SNM is **229.15 mV**. **8/10,000** samples fall below the chosen 180 mV criterion; the 95% Wilson interval is **0.041–0.158%**. Numerical comparisons on 66 cases at three supplies agree within **0.002 mV** at the default grid.

![Behavioral SNM and below-criterion fraction versus supply voltage](assets/sram-supply-sweep.png)

*Review snapshot using a fixed physical gain of 14 V⁻¹. The model is behavioral and uncalibrated; the results do not establish read/write yield or silicon reliability. This figure and the linked review branch belong to the same revision.*

[Read the study and reproduce it →](https://github.com/c18663979619-cpu/sram-reliability-monte-carlo/tree/portfolio-review-2026-11-16)

## 02 · Circuit and hardware design: BJT astable multivibrator

**Method.** Size the timing network, interpret transient switching, adapt the schematic for a battery and LEDs, and place/route a two-layer through-hole PCB. Completed as an individual 5CCE2EMP course design project.

**Result.** The report's pre-LED simulation gives approximately **2.91 Hz**. The final CAD board is approximately **41.9 × 44.1 mm**, with **one via and zero airwires**. Native schematic/board exports, analytical calculations, and a traceable BOM are included.

![Fusion CAD preview of the BJT oscillator board](projects/bjt-astable-multivibrator-pcb/docs/figures/pcb-3d-view.png)

*The waveform predates the LED adaptation. A later PCB check shows 12 warnings awaiting review; fabrication and bench measurements are not documented. The case study explains these verification boundaries and the next steps.*

[Explore the design case study →](projects/bjt-astable-multivibrator-pcb/)

## Research approach

- Start with a question and a measurable criterion.
- Make assumptions visible and compare theory with available evidence.
- Preserve sources and parameters so another person can inspect the work.
- Test numerical methods and separate simulation, design checks, and measurement.
- Use discrepancies to identify the next useful experiment.

**Current interests:** electronic circuits, computer engineering, reliability modeling, and reproducible engineering analysis.
