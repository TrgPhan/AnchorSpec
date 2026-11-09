import numpy as np
import pytest

from event_experts import Event, EventExperts, causal_average, validate_events
from y_metrics import macro, paired_delta, bearing_values


def test_target_faults_duplicates_and_unverified_labels_rejected():
    x = np.ones((2, 3))
    with pytest.raises(ValueError, match='leakage'):
        validate_events([Event('a', 'target', 1, x)], 'target')
    e = Event('a', 'donor', 1, x)
    with pytest.raises(ValueError, match='Duplicate'):
        validate_events([e, e], 'target')
    with pytest.raises(ValueError, match='Unverified'):
        validate_events([Event('a', 'donor', 1, x, False)], 'target')


def test_hierarchical_probabilities_and_missing_class_stream():
    rng = np.random.default_rng(1)
    healthy = rng.normal(0, .1, (20, 3))
    syn = {c: rng.normal(c, .1, (30, 3)) for c in (1, 2)}
    events = [Event(str(c), str(c), c, rng.normal(c, .1, (15, 3))) for c in (1, 2, 3, 4)]
    for subset in ([], events, events[2:]):
        model = EventExperts().fit(healthy, syn, subset, target_id='target')
        p = model.predict_proba(np.vstack((healthy, *[e.features for e in events])))
        assert p.shape == (80, 5)
        assert np.all(p >= 0)
        np.testing.assert_allclose(p.sum(1), 1)
    model = EventExperts().fit(healthy, syn, events, target_id='target')
    assert model.predict_proba(events[-1].features).argmax(1).mean() == 4


def test_causal_average_never_uses_future():
    p = np.arange(24).reshape(8, 3)
    actual = causal_average(p)
    for end in range(1, 9):
        np.testing.assert_allclose(actual[end-1], p[max(0, end-5):end].mean(0))


def test_bearing_bootstrap_is_not_window_weighted():
    a = {('a', 1): 1., ('b', 1): 0., ('c', 2): 1.}
    b = {k: v - .2 for k, v in a.items()}
    assert macro(a) == .75
    result = paired_delta(a, b)
    np.testing.assert_allclose(result['ci95'], [.2, .2])
    assert result['n_bearings'] == 3
    with pytest.raises(ValueError):
        paired_delta(a, {('x', 1): 0.})


def test_repeated_seeds_do_not_increase_bearing_count():
    rows = [{'budget': 1, 'control': 'clean', 'target': 'a', 'label': 1,
             'scores': {'m': {'late': {'recall': value}}}} for value in (0., 1.)]
    values = bearing_values(rows, 'm', 'recall', budget=1)
    assert values == {('a', 1): .5}
