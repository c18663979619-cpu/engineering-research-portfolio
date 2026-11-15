# Reproducibility notes

## Current status

This repository contains cropped visual evidence from the submitted report, a component list, and the report's stated transient-analysis settings. It does not contain the editable Autodesk Fusion Electronics design, complete simulator models, or library dependencies. Another person can inspect the design evidence, but cannot independently rerun the circuit simulation or regenerate the PCB from this repository yet.

## Reported transient settings

- Analysis: transient
- Points: 500; maximum points: 5000
- Temperature: 25 °C
- Start time: 1 s; end time: 2 s
- Maximum time step: 0.001 s (1 ms)

These values are transcribed from the submitted report. They are not a substitute for the missing project source and model configuration.

## Files needed for a complete rerun

Add the native schematic and board project, any custom SPICE models or directives, and the exact library dependencies. Then record:

1. Autodesk Fusion Electronics version and relevant libraries.
2. Transistor model, model parameters, and any initial conditions or simulator directives.
3. How to open the schematic and synchronize it with the PCB.
4. ERC and DRC rule settings used for the reported checks.
5. The steps used to rerun the transient analysis and export each figure in [figures/](figures/).

## Practical validation

The evidence documents a design and simulation. It does not establish that a physical PCB was manufactured or bench-tested. Before building, verify the selected transistor's reverse base-emitter voltage limit against the circuit's worst-case stress and document the protection strategy.
