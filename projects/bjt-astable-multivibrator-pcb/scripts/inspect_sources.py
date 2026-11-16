"""Inspect archived Fusion source without altering or re-exporting it."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
records = []
for path in sorted((ROOT / "source").glob("*.f*")):
    if path.suffix not in {".fsch", ".fbrd"}: continue
    record = {"file": path.name, "bytes": path.stat().st_size,
              "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None: raise ValueError("Archive checksum failure")
        member = next(n for n in z.namelist() if n.endswith((".sch", ".brd")))
        root = ET.fromstring(z.read(member))
        record.update({"embedded_xml_version": root.get("version"),
                       "libraries": [x.attrib for x in root.findall(".//libraries/library")],
                       "parts": [x.attrib for x in root.findall(".//parts/part")],
                       "elements": [x.attrib for x in root.findall(".//elements/element")],
                       "spice_models": [{"name": x.get("name"), "definition": (x.text or "").strip()} for x in root.iter("model")],
                       "via_count": len(root.findall(".//signals/signal/via")),
                       "unrouted_wire_count": len(root.findall('.//signals/signal/wire[@layer="19"]')),
                       "design_rules": [x.attrib for x in root.findall(".//designrules/param")]})
    records.append(record)
out = ROOT / "docs/source-inventory.json"
out.write_text(json.dumps({"method": "ZIP integrity and embedded XML inspection; no Fusion or SPICE rerun", "sources": records}, indent=2)+"\n")
print(f"Inspected {len(records)} archives; wrote {out.name}")
