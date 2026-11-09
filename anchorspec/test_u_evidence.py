"""Recompute evidence and verify the frozen natural-fault experiment lineage."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results/u'


def data(name):
    path=OUT/name
    if not path.exists():pytest.skip('Local U evidence absent')
    return json.loads(path.read_text(encoding='utf8'))


@pytest.mark.parametrize('name,count',[('natural.json',39),('joint.json',117),('retrospective.json',180)])
def test_frozen_sources_and_all_duplicate_scores(name,count):
    record=data(name);assert len(record['rows'])==count
    for filename,digest in record['code_sha256'].items():
        path=ROOT/filename if filename!='generators.py' else ROOT.parent/'generator_benchmark/generators.py'
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,filename
    for row in record['rows']:
        donors=row.get('donors',[e.split(':')[1] for e in row.get('donor_events',[])])
        assert row['target'] not in donors
        for family in ('svm1','svm10','rf'):
            assert row['scores'][f'{family}:real']==row['scores'][f'{family}:duplicate']
        for stages in row['scores'].values():
            for state,v in stages.items():
                counts=v['prediction_counts']
                assert v['recall']==pytest.approx(counts[str(row['label'])]/sum(counts.values()))


def test_native_snapshot_splits_are_disjoint_and_not_mixed_fault_bearings():
    data('natural.json')
    m=json.loads((ROOT.parent/'data/xjtu_u/manifest.json').read_text())
    assert len(m['members'])==390 and not m['publisher_sha_verified']
    for bearing in {r['bearing'] for r in m['members']}:
        assert bearing not in ('1_5','3_2')
        indices={s:{r['index'] for r in m['members'] if r['bearing']==bearing and r['stage']==s} for s in ('healthy','preterminal','terminal')}
        assert all(len(a)==10 for a in indices.values())
        assert max(indices['healthy'])<min(indices['preterminal'])<min(indices['terminal'])
        assert len(set.union(*indices.values()))==30


def test_joint_features_and_sensor_bounds_match_protocol():
    data('joint.json')
    for limit in (8,16,64):
        with np.load(ROOT.parent/'data/xjtu_u/joint'/f'1_1_{limit}.npz') as f:
            for stage in ('healthy','preterminal','terminal'):
                assert f[stage].shape==(10,2,4000)
                assert np.abs(f[stage]).max()<=limit
                assert f[stage+'_features'].shape==(10,96)


def test_primary_decisions_recomputed_from_results():
    result=data('natural.json');p=result['summary']['svm1']['transport'];b=result['summary']['svm1']['real']
    checks=dict(terminal_gain5pp_over_real=p['late']['differences']['real']['delta']>=.05,
        terminal_gain5pp_over_surrogate=p['late']['differences']['surrogate']['delta']>=.05,
        no_class_loss5pp=min(p['late']['per_class'][c]-b['late']['per_class'][c] for c in ('1','2','4'))>=-.05,
        positive_exploratory_ci=p['late']['differences']['real']['ci95'][0]>0,
        no_preterminal_loss2pp=p['early']['differences']['real']['delta']>=-.02)
    assert checks==result['primary_gate']['checks']
    assert all(checks.values())==result['primary_gate']['passed']
