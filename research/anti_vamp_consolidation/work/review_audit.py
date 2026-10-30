from pathlib import Path
from decimal import Decimal, localcontext
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT = Path(r'C:\Users\moadl\OneDrive\Documents\ChatGPT\bonding curve research')
OUT = Path(__file__).resolve().parents[1] / 'outputs'
WORK = Path(__file__).resolve().parent
P1 = ROOT / 'research/narrative_consolidation/phase1'
SKIP = {'.git', '.venv', '__pycache__', '.hypothesis', '.pytest_cache', '.tmp', 'shared_bonding_lab.egg-info'}
DOCS = {
    'PRIOR_ART.md': Path(r'C:\Users\moadl\AppData\Local\Temp\codex-file-preview-Fd058q\Pasted text (2).txt'),
    'MECHANISM_DESIGNS.md': Path(r'C:\Users\moadl\AppData\Local\Temp\codex-file-preview-KpnHCQ\Pasted text (3).txt'),
    'ECONOMIC_INVARIANTS.md': Path(r'C:\Users\moadl\AppData\Local\Temp\codex-file-preview-zA63Fk\Pasted text (4).txt'),
    'RESEARCH_PLAN.md': Path(r'C:\Users\moadl\AppData\Local\Temp\codex-file-preview-gWpC3E\Pasted text (5).txt'),
}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inventory():
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(ROOT.rglob('*'))
            if p.is_file() and not any(x in SKIP for x in p.relative_to(ROOT).parts)}

if '--finish' in sys.argv:
    before = json.loads((WORK / 'repository_before.json').read_text())
    after = inventory()
    changes = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    evidence_path = OUT / 'REVIEW_EVIDENCE.json'
    result = json.loads(evidence_path.read_text())
    result['review_preservation'] = {
        'before_file_count': len(before), 'after_file_count': len(after),
        'changed_added_or_removed_paths': changes,
        'excluded_generated_or_environment_directories': sorted(SKIP),
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'repository_writes_performed': False,
    }
    evidence_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result['review_preservation'], indent=2))
    raise SystemExit(bool(changes))

before = inventory()
(WORK / 'repository_before.json').write_text(json.dumps(before, indent=2), encoding='utf-8')
manifest = json.loads((P1 / 'preservation_manifest.json').read_text())
original_failures = [name for name, item in manifest['files'].items()
                     if before.get(name) != item['sha256']]
document_evidence = {name: {'repository_sha256': digest(ROOT / name),
                            'uploaded_sha256': digest(upload),
                            'identical': digest(ROOT / name) == digest(upload)}
                     for name, upload in DOCS.items()}
suite_xml = ET.parse(P1 / 'baseline_pytest.xml').getroot()
suites = [suite_xml] if suite_xml.tag == 'testsuite' else suite_xml.findall('testsuite')
baseline = {field: sum(int(s.attrib.get(field, 0)) for s in suites)
            for field in ('tests', 'failures', 'errors', 'skipped')}
baseline['recorded_seconds'] = sum(float(s.attrib.get('time', '0')) for s in suites)
baseline['xml_sha256'] = digest(P1 / 'baseline_pytest.xml')
baseline['rerun_during_review'] = False

with localcontext() as ctx:
    ctx.prec = 70
    D = Decimal
    a, b, q = D('.01'), D('.0001'), D(1000)
    def reserve(x): return a*x + b*x*x/2
    def proceeds(total, quantity): return reserve(total) - reserve(total-quantity)
    support = D(30)
    x = 2*support / (a+b*q + ((a+b*q)**2+2*b*support).sqrt())
    depth = lambda capital: (2*D('.05')-D('.05')**2)*(capital+a*a/(2*b))
    analytical = {
        'scope': 'Deterministic analytical witnesses; zero fees/costs; not new architecture simulations or market observations',
        'reserve': str(reserve(q)), 'cap': str((a+b*q)*q),
        'D_equal_batch': {'total_tokens': str(q), 'total_principal': str(reserve(q)),
                          'each_buyer_cost': str(reserve(q)/2),
                          'first_exit': str(proceeds(q,q/2)),
                          'last_exit': str(proceeds(q/2,q/2)),
                          'first_exit_profit': str(proceeds(q,q/2)-reserve(q)/2)},
        'B_support_then_original_holders_exit': {
            'initial_reserve': str(reserve(q)), 'funded_support_spend': str(support),
            'fund_tokens': str(x), 'private_holder_sale': str(proceeds(q+x,q)),
            'remaining_locked_claim_reserve': str(reserve(x)),
            'support_cash_increment_paid_to_original_holders': str(proceeds(q+x,q)-reserve(q))},
        'depth_at_fixed_total_reserve_60': {
            'one_market_5pct': str(depth(D(60))),
            'two_markets_each_5pct': str(depth(D(30))),
            'two_market_sum_5pct': str(2*depth(D(30)))},
        'C_equal_retention': {'D': '100', 'acceptance': '.5', 'rejection_original_fraction': '0',
                              'r_W_and_r_L': '.4', 'extra_loss_K': '0',
                              'cohort_retained_delta': str(D(100)*(D('.5')*D('.4')-D('.4')))},
        'migration_frontrun': {'outlay': str(reserve(2*q)-reserve(q)),
                              'proceeds': str(reserve(3*q)-reserve(2*q)),
                              'profit': str((reserve(3*q)-reserve(2*q))-(reserve(2*q)-reserve(q)))},
    }
result = {'review_date': '2026-10-30', 'repository': str(ROOT),
          'uploaded_documents': document_evidence,
          'phase1_preservation_recheck': {'inventoried_files': len(manifest['files']),
                                         'changed_or_missing': original_failures},
          'archived_baseline': baseline, 'analytical_witnesses': analytical,
          'review_scope': 'Read-only review; no pytest, model imports, Phase 1 scripts or economic simulation runs',
          'review_preservation': {'status': 'pending final recheck'}}
(OUT / 'REVIEW_EVIDENCE.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
