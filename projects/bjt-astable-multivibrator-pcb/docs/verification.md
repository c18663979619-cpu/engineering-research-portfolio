# Evidence and verification record

Last portfolio inspection: **16 November 2026**. No new Fusion ERC/DRC or SPICE run was performed in this documentation revision.

| Claim | Available evidence | What it establishes |
|---|---|---|
| Pre-LED oscillation near 2.91 Hz | Report Figure 3, [waveform image](figures/spice-waveform.png), rounded edge-time readings | Reported simulated behavior; no raw waveform or exact rerun |
| Final circuit has battery connector and LEDs | [Final schematic image](figures/final-schematic.png) and `.fsch` XML | Final archived connectivity/components; not the same circuit as the waveform image |
| Board approximately 41.9 × 44.1 mm | Report Figure 5, [layout image](figures/pcb-layout.png) | Reported outline dimensions |
| One via and zero airwires | Layout screenshot and `.fbrd` XML inspection | One via; zero layer-19 unrouted wire segments in the archive |
| Historical ERC/DRC clear | Report Figures 4 and 7; [DRC image](figures/drc-result.png) | Historical result under the then-used rules |
| Later check has 12 warnings | [15 November screenshot](figures/drc-followup-2026-11-15.png) | Zero displayed errors; 12 warnings, with solder-mask warnings visible |
| Native files preserved | [SHA-256 inventory](source-inventory.json) | The supplied archives are inspectable and have not been changed in this revision |
| Physical board operates | No manufacturing or measurement evidence supplied | Not established |

## Reconciling the check results

The report records zero errors and warnings. The later Fusion screenshot displays an updated-design-rule notice and **0 errors / 12 warnings**, with a solder-mask warning category. Their co-occurrence does not establish the cause or harmlessness of every warning. The screenshot does not expose all detailed warning locations or settings.

Keep the historical result and later result separate. A future review should record the Fusion version, ruleset, each warning's affected objects, and the resolution or justified disposition, then capture a fresh complete result. No warning has been marked resolved or approved by this portfolio revision.

The archived board contains rule parameters including 6 mil minimum width/clearance, 0.35 mm minimum drill, and 40 mil copper-to-outline clearance. It also contains `checkStop=0`; the relationship between that saved setting and the later warning panel has not been established. See the full inventory rather than inferring a current manufacturing approval from these settings.

## Boundaries of this review

ZIP integrity, embedded component/model data, via/airwire counts, arithmetic, and documentation were checked. No simulator startup behavior, final LED-circuit transient response, manufacturing output, assembly, or bench result was verified. Those remain explicit next steps.
