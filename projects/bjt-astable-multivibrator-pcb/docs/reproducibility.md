# Reproduction and inspection guide

## Included files

The `source/` directory contains the supplied native Fusion schematic `.fsch` and PCB `.fbrd` archives. Their embedded EAGLE XML version is **9.7.0**; this is a file-format identifier, not the exact Fusion application version. [Source inventory](source-inventory.json) records archive hashes, embedded libraries, device values, model text, and board rules.

The archives include library definitions named **Tinkercad**, **Transistor**, and **Ngspice-Simulation** as applicable. Library/package references are retained. Availability of every linked 3D asset in another Fusion installation has not been tested.

## Inspect in Fusion Electronics

1. Make working copies of both exports and open/import them in a compatible Fusion Electronics installation. Record the installed Fusion version.
2. Inspect the schematic and 2D board. Confirm the expected components and values against `BOM.csv` and `source-inventory.json`.
3. When assembling an Electronics Design document, associate the existing schematic and PCB. Check the schematic/board consistency result; two separately exported files do not prove their relationship has been restored in a new installation.
4. Record the active design rules and review the later warnings before changing or exporting the board. See `verification.md`.

Autodesk provides guidance on [supported formats](https://help.autodesk.com/view/fusion360/ENU/?guid=TPD-SUPPORTED-FILE-FORMATS), [linking a schematic and board](https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/How-to-link-a-board-to-a-schematic-in-Fusion-360.html), and [local export and association](https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/How-to-export-Schematic-and-board-file-from-Fusion-360.html). Menu names may vary. These are inspection steps, not a claim that import was rerun in this review.

## Reproduce the analysis without Fusion

From the project directory, standard Python 3 is sufficient:

```bash
python analysis/design_calculations.py
python scripts/inspect_sources.py
```

The first command regenerates the analytical values CSV, including the corrected tolerance bounds. The second checks ZIP integrity and reads embedded XML without altering the exports. It does not run ERC, DRC, or SPICE.

## What is required to reproduce the transient simulation

The saved waveform belongs to the earlier **pre-LED simulation schematic**, using an ideal 9 V source. The supplied native schematic is the **final PCB version**, with a battery connector and LEDs. A directly executable copy of that earlier simulation setup and its raw output are not supplied.

Reported settings are transient analysis, 500 points, maximum 5,000 points, 25 °C, start 1 s, end 2 s, and maximum time step 0.001 s. The archived generic NPN library embeds:

```spice
.MODEL QNPN NPN
```

The archive therefore contains a model definition, but no explicit device parameter list. It does not establish the exact complete netlist, stimulus, startup/initial-condition settings, and model assignments used in the historical run. The final LED and battery parts also need simulation-compatible definitions when evaluating that version.

For a full rerun, capture the exact simulator/Fusion version, exported netlist and models, startup settings, final analysis settings, raw time-series data, and an objective frequency-measurement procedure. State whether the target is the historical pre-LED circuit or a new final-circuit validation. Preserve each as a distinct experiment.

## Measurement plan for a future physical prototype

After selecting components and resolving electrical/manufacturing questions, measure both collectors, supply voltage/current, oscillation period, duty cycle, and base-emitter stress with an appropriate setup. Record actual R/C values and device part numbers. Compare with a simulation of the same assembled circuit. No such measurements are claimed in the current portfolio.
