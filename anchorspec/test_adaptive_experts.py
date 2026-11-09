import numpy as np
import pytest

from adaptive_experts import AdaptiveExperts, event_folds
from event_experts import Event


def sample_data():
    rng = np.random.default_rng(3)
    h = rng.normal(0, .1, (12, 3))
    syn = {c: rng.normal(c, .1, (20, 3)) for c in (1, 2)}
    events = [Event(f'{c}-{i}', f'{c}-{i}', c, rng.normal(c, .1, (10, 3)))
              for c in (1, 2, 3, 4) for i in (0, 1)]
    refs = {n: {'mu': np.zeros(3), 'sd': np.ones(3)} for n in ['target'] + [e.bearing_id for e in events]}
    donor_healthy = {e.bearing_id: h for e in events}
    return h, syn, events, refs, donor_healthy


def test_whole_bearing_folds_and_label_changes():
    h, _, events, _, _ = sample_data()
    events.append(Event('extra', '1-0', 4, h))
    folds = event_folds(events)
    ids = [{e.bearing_id for e in fold} for fold in folds]
    assert all(not a.intersection(b) for i, a in enumerate(ids) for b in ids[i+1:])
    assert sorted(e.event_id for f in folds for e in f) == sorted(e.event_id for e in events)


def test_adaptive_fit_rejects_target_fault_data():
    h, syn, events, refs, healthy = sample_data()
    with pytest.raises(ValueError, match='leakage'):
        AdaptiveExperts().fit(h, syn, events, target_id=events[0].bearing_id,
                             references=refs, donor_healthy=healthy)


def test_adaptive_selection_uses_only_donors_and_serializes():
    import pickle
    h, syn, events, refs, healthy = sample_data()
    model = AdaptiveExperts().fit(h, syn, events, target_id='target', references=refs, donor_healthy=healthy)
    assert len(model.validation_) == 9
    assert len(model.inner_folds_) == 2
    assert model.synthetic_mass_ in (0., .1, .5)
    assert model.representation_ in ('z', 'delta', 'raw')
    p = model.predict_proba(h)
    np.testing.assert_allclose(p.sum(1), 1)
    np.testing.assert_allclose(pickle.loads(pickle.dumps(model)).predict_proba(h), p)
    assert set(model.event_ids_) == {e.event_id for e in events}


def test_no_events_is_explicit_physics_fallback():
    h, syn, _, refs, _ = sample_data()
    model = AdaptiveExperts().fit(h, syn, [], target_id='target', references=refs, donor_healthy={})
    assert model.synthetic_mass_ == .5
    assert model.representation_ == 'z'
    assert model.inner_folds_ == []
    assert np.all(model.predict_proba(h)[:, 3:] == 0)
