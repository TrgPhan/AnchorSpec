"""Evidence checks for nested selection without outer fault-label feedback."""
import hashlib
import json
import numpy as np
import pytest
from t_nested import ROOT,OUT,METHODS,choose,evaluate
from y_metrics import macro


def records():
    if not (OUT/'nested.json').exists():pytest.skip('Nested run absent')
    return json.loads((OUT/'nested.json').read_text()),json.loads((OUT/'nested_selection.json').read_text())


def test_small_validation_gain_keeps_real_control():
    s={m:dict(terminal_macro_recall=.70,healthy_false_fault=0.) for m in METHODS}
    s['transport']['terminal_macro_recall']=.719
    assert choose(s)==('real',True)
    s['transport']['terminal_macro_recall']=.73
    assert choose(s)==('transport',True)
    s['transport']['healthy_false_fault']=.06
    assert choose(s)==('real',True)


def test_failed_healthy_validation_is_flagged():
    s={m:dict(terminal_macro_recall=.90,healthy_false_fault=.10) for m in METHODS}
    assert choose(s)==('real',False)


def test_nested_folds_exclude_both_target_bearings_and_reconstruct_selection():
    result,selection=records();assert len(selection['rows'])==39
    for row in selection['rows']:
        assert len(row['inner_folds'])==12
        for fold in row['inner_folds']:
            assert fold['inner']!=row['target']
            assert row['target'] not in fold['donors'] and fold['inner'] not in fold['donors']
            assert len(set(fold['donors']))==11
        for method in METHODS:
            expected=macro({(f['inner'],f['label']):f['models'][method]['terminal']['recall'] for f in row['inner_folds']})
            assert expected==row['scores'][method]['terminal_macro_recall']
            false=np.mean([f['models'][method]['healthy']['fault_claim'] for f in row['inner_folds']])
            assert false==row['scores'][method]['healthy_false_fault']
        assert choose(row['scores'])==(row['selected'],row['healthy_selection_passed'])
    assert not result['confirmatory'] and result['inner_fits']==1872


def test_nested_frozen_inputs_and_outer_results_reconstruct():
    result,selection=records()
    assert result['sha256']==selection['sha256']==json.loads((OUT/'nested_prerun.json').read_text())
    for path,digest in result['sha256'].items():
        assert hashlib.sha256((ROOT.parent/path).read_bytes()).hexdigest()==digest,path
    evidence=json.loads((OUT/'readiness.json').read_text())
    assert evaluate(selection['rows'],evidence)==result['summary']
