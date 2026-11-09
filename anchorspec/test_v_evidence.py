"""Artifact integrity and statistical lineage checks for the completed V run."""
import hashlib
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results/v'
NAMES=('transport.json','kaist_transport.json','hust_transport.json','champion_augmentation.json','holdout6204.json')


def records():
    if not all((OUT/n).exists() for n in NAMES):pytest.skip('Local V artifacts absent')
    return {n:json.loads((OUT/n).read_text(encoding='utf8')) for n in NAMES}


def test_all_completed_runs_match_frozen_source():
    for record in records().values():
        for name,expected in record['code_sha256'].items():
            path=ROOT/name
            if name=='Y_selection':path=ROOT/'results/y/diagnostic_balanced.json'
            elif name=='generators.py':path=ROOT.parent/'generator_benchmark/generators.py'
            assert hashlib.sha256(path.read_bytes()).hexdigest()==expected,name


def test_strong_baseline_predictions_really_match_y():
    result=records()['champion_augmentation.json']
    old=json.loads((ROOT/'results/y/diagnostic_balanced.json').read_text())
    lookup={(r['target'],r['seed'],r['budget']):r for r in old['rows'] if r['control']=='clean'}
    assert len(result['rows'])==len(lookup)==180
    for row in result['rows']:
        original=lookup[(row['target'],row['seed'],row['budget'])]
        assert row['donor_events']==original['donor_events']
        assert row['classifier']==original['selection']['diagnostic_real']['chosen']
        for state in ('early','late'):
            assert row['scores']['real'][state]['prediction_counts']==original['scores']['diagnostic_real'][state]['prediction_counts']


def test_all_additional_evidence_has_disjoint_fault_lineage_and_consistent_counts():
    data=records()
    for row in data['holdout6204.json']['rows']:
        assert not set(row['train'])&set(row['test'])
        assert {r['donor'] for r in row['lineage']}==set(row['train'])
        for methods in row['scores'].values():
            for scores in methods.values():
                for c,v in scores.items():assert v['recall']==pytest.approx(v['counts'][int(c)]/sum(v['counts']))
    for row in data['champion_augmentation.json']['rows']:
        assert all(e.split(':')[1]!=row['target'] for e in row['donor_events'])
        for scores in row['scores'].values():
            for state in ('early','late'):
                v=scores[state];counts=v['prediction_counts']
                assert v['recall']==pytest.approx(counts[str(row['label'])]/sum(counts.values()))


def test_report_does_not_promote_failed_confirmation():
    records()
    r=json.loads((OUT/'validation.json').read_text())
    assert r['total_evaluation_tasks']==594
    assert not r['additional_geometry_checks']['mks']['beats_controls']
    assert not r['comprehensive_superiority_established']
