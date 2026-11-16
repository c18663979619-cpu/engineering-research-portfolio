# Native Fusion Electronics source

| File | Contents |
|---|---|
| `5CCE2EMP_Astable_Multivibrator_Schematic.fsch` | Final PCB schematic, including battery connector and LEDs |
| `5CCE2EMP_Astable_Multivibrator_Board.fbrd` | Corresponding supplied 2D board export |

Both original exports are retained without modification. Open working copies in Fusion Electronics and verify their association and consistency. See [the reproduction guide](../docs/reproducibility.md).

The schematic includes a generic `.MODEL QNPN NPN` definition. It is not a confirmed 2N3904 model or a complete recreation of the pre-LED simulation shown in the report. The embedded XML version `9.7.0` is not the recorded application version.

[Source inventory and SHA-256 hashes](../docs/source-inventory.json) can be regenerated with `python scripts/inspect_sources.py` from the project directory. Library definitions and linked assets retain their original provenance; no new open-source license is assigned to those dependencies by this revision.
