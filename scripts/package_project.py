"""Create a portable source/results bundle without the virtualenv or Git data."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
output = ROOT/"shared-bonding-lab.zip"
files = [p for p in ROOT.iterdir() if p.is_file() and p.suffix in (".md",".toml",".txt",".py")]
files += [ROOT/".gitignore"]
for directory in ("bonding_lab","tests","scripts",".streamlit","results"):
    for p in (ROOT/directory).rglob("*"):
        relative = p.relative_to(ROOT)
        if p.is_file() and not {"scratch","__pycache__"}.intersection(relative.parts):
            files.append(p)
with zipfile.ZipFile(output,"w",zipfile.ZIP_DEFLATED) as z:
    for p in sorted(set(files)):
        z.write(p,Path("shared-bonding-lab")/p.relative_to(ROOT))
with zipfile.ZipFile(output) as z:
    assert z.testzip() is None
    print(f"Packaged {len(z.namelist())} files; {output.stat().st_size:,} bytes; archive integrity verified")
