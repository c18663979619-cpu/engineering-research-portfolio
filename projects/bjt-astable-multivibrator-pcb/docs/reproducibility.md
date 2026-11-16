# Reproducibility notes

## Evidence included

This portfolio package contains rendered evidence from the submitted report: the final schematic, transient waveform, PCB layout, DRC result, and 3D board view. The report records the component values and transient-analysis settings listed in the project README.

## Native Fusion Electronics exports

The native schematic (`.fsch`) and PCB (`.fbrd`) exports are in [`../source/`](../source/). They are separate Autodesk Fusion Electronics archive documents and can be opened for inspection or editing in Fusion Electronics. They do not, by themselves, establish a complete simulation setup: the exact application version, full SPICE model configuration, directives, and any required library dependencies still need to be documented.

## Reported transient settings

- Analysis: transient
- Points: 500; maximum points: 5000
- Temperature: 25 °C
- Start time: 1 s; end time: 2 s
- Maximum time step: 0.001 s (1 ms)

These values are transcribed from the submitted report.

## Design-check status

The submitted report records zero ERC and DRC errors and warnings. A later Fusion PCB check screenshot, following an updated design-rule notice, shows zero errors and 12 warnings, including solder-mask warnings. Those later warnings have not yet been reviewed or resolved. Treat the zero-warning result as the historical report result; do not claim the current board check is clear or ready for manufacturing until the warnings have been inspected.

## Remaining steps for a full rerun

1. Record the Autodesk Fusion Electronics version and relevant library names/versions.
2. Identify the exact transistor SPICE model, model parameters, directives, and initial conditions.
3. Document how to open the schematic and synchronize it with the PCB.
4. Record the ERC/DRC rule settings used for the report and the later check, and investigate the current solder-mask warnings.
5. Document the transient-analysis rerun steps and how to regenerate each image in [`figures/`](figures/).

## Practical validation

The available evidence documents a Fusion design and simulation; it does not establish that a physical PCB was manufactured or bench-tested. Before building, verify the selected transistor's reverse base-emitter voltage limit against the circuit's worst-case stress and document the protection strategy.
