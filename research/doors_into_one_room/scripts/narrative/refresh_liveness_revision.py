"""Regenerate the reserve-floor revision and its document tables from stored evidence.

Usage (any working directory): python3 <path>/refresh_liveness_revision.py
No on-chain reads. Run the existing collector scripts separately to replace source evidence.
"""
import os
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "narrative"
OUT = ROOT / "outputs" / "narrative"


def run(script, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                          check=True, capture_output=True, encoding="utf-8",
                          env={**os.environ, "PYTHONUTF8": "1"}).stdout


def replace_block(document, name, content):
    begin = f"<!-- BEGIN GENERATED {name} -->"
    end = f"<!-- END GENERATED {name} -->"
    before, tail = document.split(begin, 1)
    _, after = tail.split(end, 1)
    return before + begin + "\n" + content.strip() + "\n" + end + after


def main():
    run('audit_rent_model.py')
    run("liveness_table.py", OUT / "liveness_reads.json", OUT / "liveness_quote_mints.json",
        OUT / "liveness_table.md")
    costs = run("gate_costs.py")
    (OUT / "gate_costs.md").write_text(costs, encoding="utf-8", newline="\n")
    audit = run("audit_liveness_brief.py")
    selected = (OUT / "liveness_table.md").read_text(encoding="utf-8").split(
        "### C. Reserve-and-idle baseline, before age and volume clauses\n", 1)[1]
    correction = audit.split("# Liveness brief correction: room age differs from idle time\n", 1)[1]
    doc_path = ROOT / "NARRATIVE_DETECTION.md"
    document = doc_path.read_text(encoding="utf-8")
    document = replace_block(document, "BRIEF CORRECTION", correction)
    rent=(OUT/'rent_correction.md').read_text(encoding='utf-8')
    document=replace_block(document,'RENT CORRECTION',rent)
    document = replace_block(document, "SELECTED GATE", selected)
    document = replace_block(document, "POISONING COSTS", costs)
    for name,path in [('IMAGE CALIBRATION','image_calibration.md'),('IMAGE ENTROPY','image_entropy_calibration.md'),
                      ('REAL PHASH CHECK','real_phash_reference_check.txt')]:
        content=(OUT/path).read_text(encoding='utf-8')
        content='\n'.join(line for line in content.splitlines() if not line.startswith('# '))
        document=replace_block(document,name,content)
    robustness=json.loads((OUT/'real_image_robustness.json').read_text(encoding='utf-8'))
    fetch=json.loads((OUT/'image_fetch_summary.json').read_text(encoding='utf-8'))
    lines=[f"Real-image corpus: {fetch['unique_image_sha256']} distinct byte hashes; "
           f"{len(robustness['sample_sha256'])} edit-positive sources; seed {robustness['seed']}. "
           f"Images decoded for {fetch['launches_with_phash']}/{fetch['launches']} launches; "
           f"{fetch['metadata_failures']} metadata failures and {fetch['image_failures']} image failures.",'',
           '| edit | within Hamming 10 | within Hamming 16 |','|---|---|---|']
    for name in ('re-encode JPEG q85','JPEG q40','rescale to 128 px','rescale to 512 px',
                 'hue rotate 60 deg','hue rotate 180 deg','grayscale','centre crop 5%',
                 'centre crop 10%','centre crop 20%','caption bar (bottom 15%)',
                 'sticker in corner (1/16 area)','mirror (left-right)'):
        distances=robustness['distances'][name]
        lines.append(f"| {name} | {sum(d<=10 for d in distances)/len(distances):.1%} | "
                     f"{sum(d<=16 for d in distances)/len(distances):.1%} |")
    document=replace_block(document,'REAL ROBUSTNESS','\n'.join(lines))
    doc_path.write_text(document, encoding="utf-8",newline='\n')
    spec_path=ROOT/'PERMANENT_CURVE_SPEC.md'
    spec=replace_block(spec_path.read_text(encoding='utf-8'),'RENT CORRECTION',rent)
    spec_path.write_text(spec,encoding='utf-8',newline='\n')
    print("Regenerated gate, cost, rent-audit and image document blocks from evidence.")


if __name__ == "__main__":
    main()
