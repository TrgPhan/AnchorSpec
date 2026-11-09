"""Preserve real evidence, constrain outputs, and audit generator-held-out lineage."""
import hashlib
import json
import numpy as np
import pytest
from s_latent import WaveCodec,LatentGenerator,schedule
from s_additive import ROOT,OUT,additive_training,aggregate
from u_natural import training
from t_readiness import selective,measurements
from diagnostic_experts import fault_labels
from event_experts import causal_average


@pytest.mark.parametrize('ratio,count',[(.5,5),(1.,10),(2.,20)])
@pytest.mark.parametrize('alpha',[.25,1.])
def test_augmentation_keeps_every_real_row_label_and_weight(ratio,count,alpha):
    rng=np.random.default_rng(4);healthy=rng.normal(size=(5,4))
    events=[('a',1,rng.normal(size=(10,4))),('b',2,rng.normal(size=(10,4)))]
    derived={n:{'flow':rng.normal(size=(20,4))} for n,c,x in events}
    baseline=training(healthy,events,{},'real');x,y,w,meta=additive_training(healthy,events,derived,'flow',ratio,alpha)
    for expected,actual in zip(baseline,(x,y,w)):np.testing.assert_array_equal(actual[:25],expected)
    assert meta['real_count']==25 and meta['synthetic_count']==count*2
    # Real fault weight is two of three equal class masses. Each synthetic row
    # receives alpha times the corresponding per-donor real-window weight.
    assert meta['synthetic_weight']==pytest.approx(25*2/3*ratio*alpha)


def test_codec_and_two_objectives_produce_finite_waveforms_without_test_data():
    rng=np.random.default_rng(12);waves=rng.normal(size=(40,64));codec=WaveCodec().fit(waves,8)
    c=np.eye(2)[np.arange(40)%2]
    beta,bar=schedule();assert np.all(np.diff(bar.numpy())<0) and beta.min()>0 and beta.max()<1
    for kind in ('flow','diffusion'):
        model=LatentGenerator(kind,11,steps=3).fit(codec.train_z,c,np.ones(40))
        first=model.sample(c[:4],18);second=model.sample(c[:4],18)
        np.testing.assert_array_equal(first,second)
        reconstructed,meta=codec.decode(first)
        assert reconstructed.shape==(4,64) and np.isfinite(reconstructed).all()
        assert np.abs(reconstructed).max()<=8 and len(model.losses)==2
    with pytest.raises(ValueError):codec.decode(np.full((4,9),np.nan))


def evidence():
    path=OUT/'additive.json'
    if not path.exists():pytest.skip('S experiment not completed')
    return json.loads(path.read_text())


def test_frozen_sources_target_exclusion_and_matched_amounts():
    r=evidence();assert len(r['rows'])==39 and r['baseline_T_reproduced'] and not r['confirmatory']
    for path,digest in r['sha256'].items():assert hashlib.sha256((ROOT.parent/path).read_bytes()).hexdigest()==digest,path
    for row in r['rows']:
        assert len(row['donors'])==12 and row['target'] not in row['donors']
        assert set(row['reference_indices']).isdisjoint(row['healthy_test_indices'])
        for key,counts in row['counts'].items():
            assert counts['real_count']==125 and counts['real_weight']==pytest.approx(125)
            if key!='real':
                ratio=float(key.split(':')[1][1:]);alpha=float(key.split(':')[2][1:])
                assert counts['synthetic_count']==120*ratio
                assert counts['synthetic_weight']==pytest.approx(125*.75*ratio*alpha)
        for gen in row['generation']['generators'].values():assert gen['steps']==1500 and gen['loss'][-1]['step']==1500


def test_all_saved_predictions_reconstruct_and_scores_reaggregate():
    r=evidence()
    for row in r['rows']:
        for stages in row['scores'].values():
            for stage,record in stages.items():
                p=causal_average(np.asarray(record['raw_scores']))
                for policy,pred in (('selective',selective(p,0)),('conditional',fault_labels(p))):
                    assert record['policies'][policy]==dict(predictions=pred.tolist(),**measurements(pred,0 if stage=='healthy' else row['label']))
    assert aggregate(r['rows'])==r['summary']
