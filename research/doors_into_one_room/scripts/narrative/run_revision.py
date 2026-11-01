"""Reproduce the approved revision without editing generated tables by hand.

Default: regenerate math/gate/cost/docs and offline social/consensus/consolidation studies from
         checked-in observations and recorded hashes; no image fetch or decoding.
--images: also redo image replay, entropy, real-image edits and reference comparison;
          requires byte caches from fetch_token_images.py and pinned requirements_images.txt.
--fetch: fetch original sample metadata/images first (network); implies --images.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SCRIPTS=ROOT/'scripts'


def run(path,*args):
    subprocess.run([sys.executable,str(SCRIPTS/path),*map(str,args)],check=True,
                   env={**os.environ,'PYTHONUTF8':'1'})


def main():
    if '--fetch' in sys.argv:
        run(Path('narrative/fetch_token_images.py'))
    if '--images' in sys.argv or '--fetch' in sys.argv:
        run(Path('narrative/calibrate_images.py'))
        run(Path('narrative/calibrate_image_entropy.py'))
        run(Path('narrative/real_image_robustness.py'),400)
        run(Path('narrative/phash_reference_check.py'),'--real',ROOT/'outputs/narrative/real_phash_reference_check.txt')
    run(Path('refresh_spec_tables.py'))
    run(Path('narrative/refresh_liveness_revision.py'))
    run(Path('narrative/audit_consolidation_inputs.py'))
    run(Path('narrative/measure_consolidation_value.py'))
    run(Path('narrative/test_liveness.py'))
    run(Path('narrative/test_recall_evidence.py'))
    run(Path('narrative/test_social.py'))
    run(Path('narrative/test_consensus.py'))
    run(Path('narrative/test_consolidation.py'))
    run(Path('narrative/run_examples.py'),SCRIPTS/'narrative/examples')
    run(Path('narrative/revision_summary.py'))


if __name__=='__main__':
    main()
