"""Full-rank codec reconstruction and independent lineage of the S2 ablation."""
import hashlib
import json
import numpy as np
import pytest
from s_latent import WaveCodec
from s2_fullrank import ROOT,OUT,aggregate
from t_readiness import selective,measurements
from event_experts import causal_average
from diagnostic_experts import fault_labels


def test_full_rank_reconstructs_training_waves_before_sensor_precision():
    rng=np.random.default_rng(98);wave=rng.normal(0,.1,(24,128));wave-=wave.mean(1,keepdims=True)
    codec=WaveCodec().fit(wave,len(wave)-1)
    assert codec.diagnostics['relative_reconstruction_l2']<1e-6
    assert codec.diagnostics['explained_variance']==pytest.approx(1.)
    decoded,_=codec.decode(codec.train_z)
    np.testing.assert_allclose(decoded,wave,atol=2e-5,rtol=0)


def evidence():
    p=OUT/'fullrank.json'
    if not p.exists():pytest.skip('S2 not completed')
    return json.loads(p.read_text())


def test_s2_frozen_inputs_and_source_fold_reconstruction():
    r=evidence();assert len(r['rows'])==39 and not r['confirmatory']
    for path,digest in r['sha256'].items():assert hashlib.sha256((ROOT.parent/path).read_bytes()).hexdigest()==digest,path
    for row in r['rows']:
        assert len(row['donors'])==12 and row['target'] not in row['donors']
        codec=row['generation']['codec']
        assert codec['dimensions']==120 and codec['training_waveforms']==120
        assert codec['relative_reconstruction_l2']<1e-6
        for model in row['generation']['generators'].values():assert model['steps']==1500
        for count in row['counts'].values():assert count['real_count']==125 and count['real_weight']==pytest.approx(125)


def test_s2_predictions_and_paired_controls_reconstruct():
    r=evidence();old=json.loads((ROOT/'results/s/additive.json').read_text())
    lookup={(row['target'],row['seed']):row for row in old['rows']};merged=[]
    for row in r['rows']:
        for stages in row['scores'].values():
            for stage,record in stages.items():
                scores=causal_average(np.asarray(record['raw_scores']))
                for policy,pred in (('selective',selective(scores,0)),('conditional',fault_labels(scores))):
                    assert record['policies'][policy]==dict(predictions=pred.tolist(),**measurements(pred,0 if stage=='healthy' else row['label']))
        previous=lookup[row['target'],row['seed']]
        merged.append(dict(target=row['target'],seed=row['seed'],label=row['label'],scores=previous['scores']|row['scores']))
    assert aggregate(merged)==r['summary']
