from dataclasses import asdict
from bonding_lab.narrative.experiments import matrix
from bonding_lab.narrative.model import hash_obj,make_tape


def test_declared_matrix_is_unique_and_has_required_controls():
    cells=matrix();keys=[]
    for c in cells:
        row=asdict(c);row.pop('name');keys.append(hash_obj(row))
    assert len(keys)==len(set(keys))
    assert {'A','B','B_CREATOR','C','D','SINGLE_SPOT','SINGLE_BATCH','INDEPENDENT_BATCH','SPOT_LOCK'}<={c.name for c in cells}
    assert all(c.opportunities==480 and c.window==1800 and c.horizon==604800 for c in cells)


def test_opportunity_hash_excludes_hash_field_and_is_replayable():
    a=make_tape(17);stored=a.pop('_sha256')
    assert hash_obj(a)==stored
    assert make_tape(17)['_sha256']==stored
    assert all(r['budget']>=0 for r in a['opportunities'])
