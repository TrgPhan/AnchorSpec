"""Identity, signal phase, lineage and CPU generator numerical contracts."""
import hashlib
import json
import numpy as np
import pytest
from s3_spectral import SpectralResidual,ResidualGenerator


def fixture():
    rng=np.random.default_rng(11);x=rng.normal(size=(12,4000));x-=x.mean(1,keepdims=True)
    x[0]*=10  # centered amplitude above old 8 g output clamp
    codec=SpectralResidual().fit(x,np.repeat(np.arange(3),4),np.eye(3).repeat(4,axis=0))
    return x,codec


def test_identity_and_same_donor_pair_lineage():
    x,c=fixture();limits=np.abs(x).max(1)
    reconstructed,info=c.apply(x,np.zeros((len(x),24)),1,limits)
    np.testing.assert_allclose(reconstructed,x,rtol=1e-12,atol=1e-12)
    assert reconstructed[0].max()>8 and info['residual_clamp_fraction']==0
    assert len(c.pairs)==36 and np.all(c.pairs[:,0]!=c.pairs[:,1])
    assert np.all(c.pairs[:,0]//4==c.pairs[:,1]//4)


def test_phase_preserved_and_peak_bounded():
    x,c=fixture();rng=np.random.default_rng(7);limits=np.abs(x).max(1)
    y,_=c.apply(x,rng.normal(size=(len(x),24)),.5,limits)
    assert np.all(np.abs(y).max(1)<=limits+1e-10)
    a=np.fft.rfft(x,axis=1)[:,1:];b=np.fft.rfft(y,axis=1)[:,1:]
    np.testing.assert_allclose(np.angle(b/a),0,atol=1e-9)
    with pytest.raises(ValueError):c.apply(x,np.full((len(x),24),np.nan),.5,limits)


@pytest.mark.parametrize('kind',['flow','diffusion'])
def test_cpu_objectives_finite_reproducible_and_evaluation_budget(kind):
    _,c=fixture();m=ResidualGenerator(kind,11,steps=3).fit(c.z,c.conditions[c.pairs[:,0]],np.ones(len(c.z)))
    assert next(m.model.parameters()).device.type=='cpu'
    for evaluations in (4,8,16):
        a=m.sample(c.conditions[:3],19,evaluations);b=m.sample(c.conditions[:3],19,evaluations)
        assert a.shape==(3,24) and np.isfinite(a).all();np.testing.assert_array_equal(a,b)


def test_frozen_completed_evidence_and_scores():
    from s3_cpu_benchmark import OUT,ROOT
    from event_experts import causal_average
    from diagnostic_experts import fault_labels
    from t_readiness import selective,measurements
    path=OUT/'spectral.json'
    if not path.exists():pytest.skip('S3 full run not complete')
    r=json.loads(path.read_text());assert len(r['rows'])==39 and not r['confirmatory']
    for path,digest in r['sha256'].items():assert hashlib.sha256((ROOT.parent/path).read_bytes()).hexdigest()==digest,path
    for row in r['rows']:
        assert row['target'] not in row['donors'] and len(row['donors'])==12
        assert row['generation']['derived_pairs']==1080 and row['generation']['training_windows']==120
        for count in row['counts'].values():
            assert count['real_count']==125 and count['synthetic_count']==120
            assert count['real_weight']==pytest.approx(125) and count['synthetic_weight']==pytest.approx(23.4375)
        for stages in row['scores'].values():
            for stage,rec in stages.items():
                p=causal_average(np.asarray(rec['raw_scores']));truth=0 if stage=='healthy' else row['label']
                for policy,pred in (('selective',selective(p,0)),('conditional',fault_labels(p))):
                    assert rec['policies'][policy]==dict(predictions=pred.tolist(),**measurements(pred,truth))


def test_fast_decoder_matches_reference_and_grouping_preserves_order():
    from s3_fast_cpu import decode,grouped_features
    from u_natural import ORDERS
    import funnel as Fu
    x,c=fixture();limits=np.abs(x).max(1)
    residual=np.random.default_rng(1).normal(size=(len(x),24))
    expected,_=c.apply(x,residual,.5,limits)
    actual=decode(c,x,residual,.5,limits)
    np.testing.assert_allclose(actual,expected,rtol=1e-12,atol=1e-12)
    speeds=np.array([35,40,37.5]*4)
    reference=np.concatenate([Fu.feats(x[i:i+1,None,:],4000,float(fr),ORDERS) for i,fr in enumerate(speeds)])
    np.testing.assert_allclose(grouped_features(x,speeds),reference,rtol=1e-12,atol=1e-12)


def test_cached_fft_and_features_are_exact_and_cache_is_keyed_by_speed():
    from s3_cached_features import CachedDecoder,extract,plan
    from features import extract as reference_extract
    from u_natural import ORDERS
    x,c=fixture();limits=np.abs(x).max(1);residual=np.random.default_rng(9).normal(size=(len(x),24))
    expected,_=c.apply(x,residual,.5,limits)
    np.testing.assert_array_equal(CachedDecoder(c,x,limits)(residual),expected)
    plan.cache_clear()
    for speed in (35.,40.,37.5,35.):
        np.testing.assert_array_equal(extract(expected,4000,speed,ORDERS),reference_extract(expected,4000,speed,ORDERS))
    assert plan.cache_info().misses==3 and plan.cache_info().hits==1


def test_step_ablation_and_recomputed_class_means():
    from s3_cpu_benchmark import ROOT,OUT
    from event_experts import causal_average
    from diagnostic_experts import fault_labels
    from t_readiness import selective,measurements
    for filename in ('spectral.json','steps.json'):
        path=OUT/filename
        if not path.exists():pytest.skip('Full evidence incomplete')
        r=json.loads(path.read_text())
        if filename=='steps.json':assert r['models_retrained']==0 and r['replay_16_all_folds']
        for path,digest in r['sha256'].items():assert hashlib.sha256((ROOT.parent/path).read_bytes()).hexdigest()==digest,path
        for key in r['rows'][0]['scores']:
            for policy in ('selective','conditional'):
                for stage in ('terminal','preterminal'):
                    vals={}
                    for row in r['rows']:
                        rec=row['scores'][key][stage];p=causal_average(np.asarray(rec['raw_scores']))
                        pred=selective(p,0) if policy=='selective' else fault_labels(p)
                        assert rec['policies'][policy]==dict(predictions=pred.tolist(),**measurements(pred,row['label']))
                        vals.setdefault((row['target'],row['label']),[]).append(rec['policies'][policy]['recall'])
                    expected=np.mean([np.mean([np.mean(v) for (n,label),v in vals.items() if label==c]) for c in (1,2,4)])
                    assert r['summary'][key][policy][stage]['recall']==pytest.approx(expected)
