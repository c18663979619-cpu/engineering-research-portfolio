"""Reproduce analytical estimates only; this does not run SPICE."""
import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rb, cap, rc, vcc, vf, vbe, vce = 47000., 5.1e-6, 1000., 9., 2., .7, .2
ideal = 1/(1.38*rb*cap)
vmin = vbe-(vcc-vce)
junction = 1/(2*rb*cap*math.log((vcc-vmin)/(vcc-vbe)))
rows = [
    ("required_capacitance_for_3hz", 1/(1.38*rb*3)*1e6, "uF", "First-order RC model"),
    ("first_order_frequency", ideal, "Hz", "1/(1.38*RB*C)"),
    ("junction_drop_estimate", junction, "Hz", "Assumed VBE=0.7V; VCEsat=0.2V; pre-LED circuit"),
    ("frequency_from_report_edge_times", 1/(2*(1.94-1.08)/5), "Hz", "Rounded screenshot readings; not raw waveform data"),
    ("capacitor_only_min", ideal/1.2, "Hz", "C +20%; R nominal"),
    ("capacitor_only_max", ideal/.8, "Hz", "C -20%; R nominal"),
    ("combined_tolerance_min", ideal/(1.05*1.2), "Hz", "R +5%; C +20%; first-order model"),
    ("combined_tolerance_max", ideal/(.95*.8), "Hz", "R -5%; C -20%; first-order model"),
    ("led_current_estimate", (vcc-vf-vce)/rc*1000, "mA", "Assumed LED Vf=2V; VCEsat=0.2V"),
]
out = ROOT / "analysis/calculated_values.csv"
with out.open("w", newline="") as f:
    w = csv.writer(f); w.writerow(["quantity", "value", "unit", "assumption"]); w.writerows(rows)
for name, value, unit, _ in rows: print(f"{name}: {value:.6f} {unit}")
