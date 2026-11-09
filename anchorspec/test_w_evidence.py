"""Data-contract properties for the spectral extension and source selection."""
import numpy as np
from w_spectral import spectral
from source_select import SourceSelector
from event_experts import Event
from w_hierarchy import combine


def test_spectral_is_finite_and_amplitude_invariant_without_changing_frequency():
    t=np.arange(4000)/4000
    a=np.stack([np.sin(2*np.pi*f*t)+.1*np.sin(2*np.pi*700*t) for f in (100,200)])
    f=spectral(a)
    assert f.shape==(2,196) and np.isfinite(f).all()
    np.testing.assert_allclose(f,spectral(3*a),atol=1e-8)
    assert np.linalg.norm(f[0,:128]-f[1,:128])>1


def test_inner_folds_keep_each_donor_out_and_support_every_class():
    rng=np.random.default_rng(7)
    events=[Event(f'{c}-{i}',f'b{c}-{i}',c,rng.normal(c*5,.1,(8,3))) for c in (1,2) for i in (0,1)]
    refs={e.bearing_id:dict(mu=np.zeros(3),sd=np.ones(3)) for e in events}
    refs['target']=dict(mu=np.zeros(3),sd=np.ones(3))
    derivatives={e.event_id:np.repeat(e.features,20,axis=0) for e in events}
    m=SourceSelector().fit(events,derivatives,{},target_id='target',references=refs)
    for ids in m.inner_folds_:
        assert {e.label for e in events if e.event_id not in ids}=={1,2}
        assert {e.label for e in events if e.event_id in ids}=={1,2}
    assert all(r['score'] is not None for r in m.validation_)


def test_hierarchy_mapping_and_normalization():
    group=np.array([[.5,.4,.1,0,0],[.5,.1,.4,0,0]])
    ring=np.array([[.2,.7,.1,0,0],[.2,.7,.1,0,0]])
    other=np.array([[.2,.1,.7,0,0],[.2,.1,.7,0,0]])
    result=combine(group,ring,other)
    np.testing.assert_allclose(result.sum(1),1)
    np.testing.assert_array_equal(result.argmax(1),[1,4])
    assert (result[:,0]==0).all()
