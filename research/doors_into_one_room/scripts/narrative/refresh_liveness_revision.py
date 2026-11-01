"""Regenerate gate, social/consensus studies and document tables from stored evidence.

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
    run('audit_replay_inputs.py')
    run('recall_bounds.py')
    run('label_dependency.py')
    run('calibrate_social.py')
    run('calibrate_consensus.py')
    run('probe_image_hosts.py', '--render-only')
    run('age_window_calibration.py')
    run("liveness_table.py", OUT / "liveness_reads.json", OUT / "liveness_quote_mints.json",
        OUT / "liveness_table.md")
    costs = run("gate_costs.py")
    (OUT / "gate_costs.md").write_text(costs, encoding="utf-8", newline="\n")
    audit = run("audit_liveness_brief.py")
    correction = audit.split("# Liveness brief correction: room age differs from idle time\n", 1)[1]
    doc_path = ROOT / "NARRATIVE_DETECTION.md"
    document = doc_path.read_text(encoding="utf-8")
    document = replace_block(document, "BRIEF CORRECTION", correction)
    rent=(OUT/'rent_correction.md').read_text(encoding='utf-8')
    document=replace_block(document,'RENT CORRECTION',rent)
    age=(OUT/'age_window_calibration.md').read_text(encoding='utf-8')
    age='\n'.join(line for line in age.splitlines() if not line.startswith('# '))
    document=replace_block(document,'AGE DISTRIBUTION',age)
    document = replace_block(document, "POISONING COSTS", costs)
    for name, filename in [('RECALL BOUNDS','recall_bounds.md'), ('LABEL DEPENDENCY','label_dependency.md')]:
        content=(OUT/filename).read_text(encoding='utf-8')
        content='\n'.join(line for line in content.splitlines() if not line.startswith('# '))
        document=replace_block(document,name,content)
    images=json.loads((OUT/'image_calibration.json').read_text(encoding='utf-8'))
    entropy=json.loads((OUT/'image_entropy_calibration.json').read_text(encoding='utf-8'))
    base=images['results'][0]
    h0=next(row for row in images['results'] if row['strong']==0)
    narrow=next(row for row in entropy['results'] if row['hamming']==0 and row['minimum_entropy_bits']==7.5)
    false_base=base['routed']-base['correct']
    false_image=h0['routed']-h0['correct']
    decision=(f"Archived all-live benchmark estimates, using assistant labels: at Hamming 0, "
              f"image-assisted recall rises from {base['recall']:.2%} to {h0['recall']:.2%} "
              f"(+{100*(h0['recall']-base['recall']):.2f} points), while precision falls from "
              f"{base['precision']:.2%} to {h0['precision']:.2%}. Estimated false routes rise from "
              f"{false_base:.2f} to {false_image:.2f} ({false_image/false_base:.2f}x). "
              f"The entropy-filtered candidate has only {narrow['assisted']} assisted routes in-sample. "
              "These are conditional historical research estimates, not production end-to-end results. "
              "They do not justify permanently absorbing a genuine launch through an image-assisted route.\n\n"
              "See `outputs/narrative/image_calibration.md`, `image_entropy_calibration.md`, "
              "`real_image_robustness.md` and the byte-hash manifests for the retained research evidence.")
    document=replace_block(document,'IMAGE DECISION',decision)
    doc_path.write_text(document, encoding="utf-8",newline='\n')
    spec_path=ROOT/'PERMANENT_CURVE_SPEC.md'
    spec=replace_block(spec_path.read_text(encoding='utf-8'),'RENT CORRECTION',rent)
    spec_path.write_text(spec,encoding='utf-8',newline='\n')
    print("Regenerated gate, cost, rent-audit and image document blocks from evidence.")


if __name__ == "__main__":
    main()
