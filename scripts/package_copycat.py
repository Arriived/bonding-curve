"""Package completed research with code/tests and preserved development evidence."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parents[1]
base=ROOT/"research/copycat_diversion"
validation=json.loads((base/"report_validation.json").read_text())
assert validation["status"]=="complete"
output=ROOT/"copycat-diversion-research.zip"
files=[p for p in ROOT.iterdir() if p.is_file() and p.suffix in (".md",".py",".toml",".txt")]
files.append(ROOT/".gitignore")
for directory in ("bonding_lab","tests","scripts",".streamlit","research/copycat_diversion"):
    for p in (ROOT/directory).rglob("*"):
        relative=p.relative_to(ROOT)
        if p.is_file() and not {"__pycache__","smoke"}.intersection(relative.parts) and p.name!="secrets.toml":files.append(p)
with zipfile.ZipFile(output,"w",zipfile.ZIP_DEFLATED) as z:
    for p in sorted(set(files)):z.write(p,Path("bonding-lab-copycat")/p.relative_to(ROOT))
with zipfile.ZipFile(output) as z:
    assert z.testzip() is None
    assert "bonding-lab-copycat/research/copycat_diversion/FINDINGS.md" in z.namelist()
    count=len(z.namelist())
print(json.dumps(dict(archive=str(output),files=count,bytes=output.stat().st_size,
                      sha256=hashlib.sha256(output.read_bytes()).hexdigest(),zip_integrity="passed"),indent=2))
