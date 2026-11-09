"""Audit isolation, rejection bookkeeping, and frozen evidence, not score targets."""
import hashlib
import json
import numpy as np
import pytest
from t_readiness import ROOT,OUT,measurements,selective,THRESHOLDS
from diagnostic_experts import fault_labels
from event_experts import causal_average


def evidence():
    p=OUT/'readiness.json'
    if not p.exists():pytest.skip('T evidence not generated')
    return json.loads(p.read_text())


def test_rejection_cannot_artificially_raise_effective_recall():
    p=np.array([[.1,.6,.1,.1,.1],[.05,.9,.02,.02,.01]])
    assert measurements(selective(p,0),1)['recall']==1
    assert measurements(selective(p,.7),1)['recall']==.5
    assert measurements(selective(p,.95),1)['recall']==0


def test_healthy_choice_and_abstention_are_different():
    p=np.array([[.9,.1,0,0,0],[.4,.3,.3,0,0]])
    pred=selective(p,.5)
    np.testing.assert_array_equal(pred,[0,-1])
    assert measurements(pred,4)['recall']==0
    assert measurements(pred,0)['recall']==.5


@pytest.mark.parametrize('p',[np.zeros((2,5)),[[np.nan,0,0,0,1]],[[1,0]],[[1.1,-.1,0,0,0]]])
def test_invalid_scores_do_not_emit_diagnosis(p):
    with pytest.raises(ValueError):selective(p,.5)


def test_all_source_and_cache_hashes_match_prerun():
    r=evidence();pre=json.loads((OUT/'prerun.json').read_text())
    assert r['sha256']==pre['sha256']
    for path,digest in r['sha256'].items():
        assert hashlib.sha256((ROOT.parent/path).read_bytes()).hexdigest()==digest,path


def test_whole_bearing_isolation_and_duplicate_invariance():
    r=evidence();assert len(r['rows'])==39
    for row in r['rows']:
        assert set(row['reference_indices']).isdisjoint(row['healthy_test_indices'])
        assert row['reference_indices']==[1,2,3,4,5]
        assert row['healthy_test_indices']==[6,7,8,9,10]
        for library,record in row['libraries'].items():
            assert row['target'] not in record['donors']
            if library=='missing_cage':assert not {'1_4','2_3'}.intersection(record['donors'])
            for family in ('rf','svm1'):
                assert record['models'][family+':real']==record['models'][family+':duplicate']


def test_saved_predictions_and_metrics_reconstruct_from_scores():
    for row in evidence()['rows']:
        for library in row['libraries'].values():
            for model in library['models'].values():
                for stage,record in model.items():
                    raw=np.asarray(record['raw_scores']);scores=causal_average(raw)
                    assert raw.shape==((5,5) if stage=='healthy' else (10,5))
                    np.testing.assert_allclose(scores,record['scores'],rtol=0,atol=0)
                    policies={'conditional':fault_labels(scores)}
                    policies.update({f'selective_{v:g}':selective(scores,v) for v in THRESHOLDS})
                    for policy,pred in policies.items():
                        actual=record['policies'][policy]
                        assert actual==dict(predictions=pred.tolist(),**measurements(pred,0 if stage=='healthy' else row['label']))


def test_research_gate_does_not_mean_factory_ready():
    from t_readiness import aggregate
    r=evidence();summary,gate=aggregate(r['rows'])
    assert summary==r['summary'] and gate==r['research_gate']
    assert not gate['factory_ready'] and not r['confirmatory']


def test_lubrication_design_does_not_count_channels_as_runs():
    p=OUT/'lubrication_design.json'
    if not p.exists():pytest.skip('Design audit absent')
    r=json.loads(p.read_text());assert len(r['runs'])==8
    matches=[g for g in r['matched_regimes'] if g['lubricated_runs'] and g['unlubricated_runs']]
    assert len(matches)==1
    assert matches[0]['lubricated_runs']==[1,2,3] and matches[0]['unlubricated_runs']==[5]
    assert not any(g['leave_run_out_both_classes_in_training_possible'] for g in r['matched_regimes'])
