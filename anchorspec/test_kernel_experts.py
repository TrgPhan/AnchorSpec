import pickle
import numpy as np
import pytest

from event_experts import Event
from kernel_experts import KernelExperts, KernelModel


def test_single_binary_multiclass_scores_and_roundtrip():
    rng = np.random.default_rng(5)
    h = rng.normal(0, .1, (12, 3))
    syn = {c: rng.normal(c, .1, (15, 3)) for c in (1,2)}
    events = [Event(str(c), str(c), c, rng.normal(c, .1, (10, 3))) for c in range(1,5)]
    for ev, mass in (([], 0.), (events[:1], 0.), (events, .1)):
        model = KernelModel(1).fit(h, syn, ev, mass)
        p = model.predict_proba(h)
        assert p.shape == (12,5)
        assert np.isfinite(p).all()
        np.testing.assert_allclose(p.sum(1), 1)
        np.testing.assert_allclose(pickle.loads(pickle.dumps(model)).predict_proba(h), p)


def test_nested_kernel_rejects_target_and_unverified_events():
    h = np.ones((12,3))
    refs = {'target': {'mu': np.zeros(3), 'sd': np.ones(3)}}
    for event in (Event('e','target',1,h), Event('e','donor',1,h,False)):
        with pytest.raises(ValueError):
            KernelExperts().fit(h, {1:h,2:h}, [event], target_id='target', references=refs, donor_healthy={})


def test_frozen_fallback_without_events():
    rng = np.random.default_rng(10)
    h = rng.normal(0,.1,(10,3))
    refs = {'target': {'mu':np.zeros(3),'sd':np.ones(3)}}
    model = KernelExperts().fit(h,{1:h+1,2:h+2},[],target_id='target',references=refs,donor_healthy={})
    assert model.C_ == 1
    assert len(model.validation_) == 18
    assert model.inner_folds_ == []
    assert (model.predict_proba(h)[:,3:] == 0).all()
