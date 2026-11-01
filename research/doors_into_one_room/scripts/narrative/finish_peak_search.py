"""Finish the authorized long-running top-20 search and optionally publish it.

Publication requires all 20 validated histories, a fresh offline replay, tests,
unchanged source files, the requested branch and a normal non-force push.
"""
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

from audit_liveness_brief import OUT,ROOT
from history_cache import utc

BRANCH='claude/gallant-heisenberg-fi5c0c'
HERE=pathlib.Path(__file__).resolve().parent
STATE=ROOT/'.tmp'/'peak_search_job.json'


def run(arguments):
    subprocess.run(arguments,check=True,cwd=ROOT)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish',action='store_true',help='commit and push the already-authorized generated results')
    args=parser.parse_args();STATE.parent.mkdir(exist_ok=True)
    state={'state':'running','started_at_utc':utc(),'publish_requested':args.publish}
    def save(**updates):
        state.update(updates);STATE.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8',newline='\n')
    fixed=list(HERE.glob('*.py'))+[OUT/name for name in ('peak_preregistration.json','peak_search_protocol.json',
        'peak_event_sources.json','peak_activity_ranking.json','peak_search_selection.json')]
    source={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in fixed}
    save()
    try:
        branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
        assert branch==BRANCH,'requested branch is no longer checked out'
        run([sys.executable,str(HERE/'collect_peak_transactions.py'),'--qps','0.8','--batch-size','1','--workers','8'])
        save(state='offline_verification')
        run([sys.executable,str(HERE/'measure_peak_consolidation.py'),'--offline'])
        run([sys.executable,str(HERE/'report_peak_consolidation.py')])
        result=json.loads((OUT/'peak_consolidation.json').read_text(encoding='utf-8'))
        assert result['all_top20_measured'],'all 20 histories must validate before publication'
        run([sys.executable,'-m','unittest','discover','-s',str(HERE),'-p','test_*.py'])
        run([sys.executable,str(HERE/'run_examples.py'),str(HERE/'examples')])
        run([sys.executable,str(HERE/'archive_peak_cache.py')])
        assert all(hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==digest for p,digest in source.items()),'source changed during collection; review before publication'
        if args.publish:
            save(state='publishing')
            assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()==BRANCH
            files=[ROOT/'PEAK_CONSOLIDATION_VALUE.md',OUT/'peak_consolidation.json',OUT/'peak_consolidation_clusters.csv',
                   OUT/'peak_transaction_collection.json',OUT/'peak_search_selection.json']
            files+=sorted((OUT/'peak_trades').glob('*.json'))+sorted((OUT/'peak_trades').glob('*.jsonl.gz'))
            files+=sorted((OUT/'peak_history_archive').glob('*'))
            paths=[str(p) for p in files]
            run(['git','add','--',*paths])
            changed=subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip()
            if changed:run(['git','commit','--only','-m','Measure the top-20 peak-pooled consolidation search','--',*paths])
            run(['git','push','origin','HEAD:refs/heads/'+BRANCH])
            state['commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        save(state='complete',finished_at_utc=utc(),spec_additional_count=result['additional_counts_measured']['spec default'],
             primary_c=result['primary_c_metrics']['c_peak_weighted'],
             gross_pooled_c=result['primary_c_metrics']['c_gross_pooled'],
             conditional_remainder_envelope_lamports=result['drawdown']['conditional_envelope_lamports'])
        print('SEARCH COMPLETE '+json.dumps(state),flush=True)
    except BaseException as error:
        save(state='needs_review',stopped_at_utc=utc(),error=str(error))
        # Preserve a reviewable checkpoint; it never claims completion.
        for script in ('report_peak_consolidation.py','archive_peak_cache.py'):
            try:run([sys.executable,str(HERE/script)])
            except BaseException:pass
        raise


if __name__=='__main__':main()
