"""Audit corrected confirmation and exact identity of unaffected first-run worlds."""
from pathlib import Path
import csv,gzip,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
WORKSPACE=ROOT.parents[3]
sys.path.insert(0,str(WORKSPACE))
from bonding_lab.narrative.experiments import sources
from bonding_lab.narrative.model import hash_obj


def main():
    old=json.loads((ROOT.parent/'confirmation/manifest.json').read_text())
    current=json.loads((ROOT/'confirmation/manifest.json').read_text())
    oldplan=json.loads((ROOT.parent/'frozen_plan.json').read_text())
    plan=json.loads((ROOT/'frozen_plan.json').read_text())
    assert old['status']==current['status']=='complete'
    assert oldplan['targets']==plan['targets'] and oldplan['seeds']==plan['seeds']
    assert sources()==plan['source_sha256']
    assert current['completed_worlds']==current['planned_worlds']==10000
    assert all(n==100 for n in current['completed_by_cell'].values())
    changed=[key for key,digest in current['world_hashes'].items() if old['world_hashes'][key]!=digest]
    unexpected=[key for key in changed if not key.startswith('D_REFUSAL:')]
    assert not unexpected,unexpected
    unaffected=[key for key in current['world_hashes'] if not key.startswith('D_REFUSAL:')]
    assert len(unaffected)==9900
    for key in unaffected:assert current['world_hashes'][key]==old['world_hashes'][key]
    for seed in plan['seeds']:
        with gzip.open(ROOT/'confirmation/tapes'/f'{seed}.json.gz','rt',encoding='utf-8') as f:tape=json.load(f)
        assert hash_obj({k:v for k,v in tape.items() if k!='_sha256'})==tape['_sha256']
        assert tape['_sha256']==current['tape_hashes'][str(seed)]==old['tape_hashes'][str(seed)]
    rows=0;keys=set()
    with gzip.open(ROOT/'confirmation/runs.csv.gz','rt',encoding='utf-8',newline='') as f:
        for row in csv.DictReader(f):
            key=(row['name'],row['label'],row['seed']);assert key not in keys;keys.add(key)
            assert float(row['initial_world'])==39100
            for field in ('cohort_reserve','escrow','support_claims','protocol_cash','network_cash'):
                assert float(row[field])>=0
            rows+=1
    assert rows==90000
    digest=hashlib.sha256((ROOT/'confirmation/runs.csv.gz').read_bytes()).hexdigest()
    assert digest==current['raw_results_sha256']
    result=dict(status='passed',corrected_worlds=10000,paired_seeds=100,checkpoint_rows=rows,
                configurations_policies_seeds_unchanged=True,unchanged_world_hashes=9900,
                changed_D_REFUSAL_worlds=len(changed),unexpected_changed_worlds=unexpected,
                all_tape_hashes_unchanged=True,source_matches_corrected_freeze=True,
                first_run_worlds_preserved=10000,raw_results_sha256=digest)
    (ROOT/'correction_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
