"""Matched controls and donor lineage for the external-library experiment."""
import hashlib
import json
import numpy as np
import pytest
from t_external import ROOT,OUT,aggregate
from t_readiness import selective,measurements
from event_experts import causal_average


def evidence():
    p=OUT/'external.json'
    if not p.exists():pytest.skip('External evidence absent')
    return json.loads(p.read_text())


def test_external_sources_frozen_and_target_fault_excluded():
    r=evidence();assert len(r['rows'])==39 and not r['confirmatory']
    assert r['sha256']==json.loads((OUT/'external_prerun.json').read_text())
    for path,digest in r['sha256'].items():
        assert hashlib.sha256((ROOT.parent/path).read_bytes()).hexdigest()==digest,path
    for row in r['rows']:
        for key,setting in row['settings'].items():
            assert 'xjtu:'+row['target'] not in setting['donors']
            assert len(setting['donors'])==(27 if key.startswith('combined') else 12)
            if key.startswith('combined'):
                assert all('uored:'+str(i) in setting['donors'] for i in range(16,21))
            assert setting['models']['real']==setting['models']['duplicate']


def test_xjtu_raw_reproduces_preexisting_matched_baselines():
    t=json.loads((OUT/'readiness.json').read_text())
    lookup={(row['target'],row['seed']):row for row in t['rows']}
    for row in evidence()['rows']:
        previous=lookup[row['target'],row['seed']]['libraries']['closed']['models']
        for method in ('real','duplicate','surrogate','severity'):
            for stage,record in row['settings']['xjtu:raw']['models'][method].items():
                assert record['raw_scores']==previous['rf:'+method][stage]['raw_scores']
                assert record['predictions']==previous['rf:'+method][stage]['policies']['selective_0']['predictions']


def test_external_predictions_and_aggregate_reconstruct():
    r=evidence()
    for row in r['rows']:
        for setting in row['settings'].values():
            for model in setting['models'].values():
                for stage,record in model.items():
                    pred=selective(causal_average(np.asarray(record['raw_scores'])),0)
                    metrics=measurements(pred,0 if stage=='healthy' else row['label'])
                    assert record==dict(raw_scores=record['raw_scores'],predictions=pred.tolist(),**metrics)
    assert aggregate(r['rows'])==r['summary']
