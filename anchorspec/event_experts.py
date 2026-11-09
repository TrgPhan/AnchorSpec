"""Small event-aware diagnostic models; no target fault data are accepted by fit.

The protected model is a research hypothesis. Confidence is not calibrated and
unseen classes are not reliably detected. Features must already be normalized
against the healthy baseline of their source machine.
"""
from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from funnel import SMALL

CLASSES = ('healthy', 'inner', 'outer', 'ball', 'cage')


@dataclass(frozen=True)
class Event:
    event_id: str
    bearing_id: str
    label: int
    features: np.ndarray
    verified: bool = True


def validate_events(events, target_id):
    seen = set()
    for event in events:
        if event.bearing_id == target_id:
            raise ValueError('Target bearing fault leakage')
        if event.event_id in seen:
            raise ValueError('Duplicate event ID')
        seen.add(event.event_id)
        if not event.verified:
            raise ValueError('Unverified maintenance label cannot update model')
        if event.label not in range(1, len(CLASSES)):
            raise ValueError('Unsupported fault label')
        if event.features.ndim != 2 or not len(event.features) or not np.isfinite(event.features).all():
            raise ValueError('Invalid event features')


def _fit(groups, seed):
    """Equal class weight, equal source weight, equal event weight within source.

    Each group is (class, source, event features). Many overlapping windows must
    not give a long recording more authority than another independent event.
    """
    counts = {}
    for label, source, x in groups:
        counts.setdefault(label, {}).setdefault(source, 0)
        counts[label][source] += 1
    xs, ys, weights = [], [], []
    for label, source, x in groups:
        xs.append(x)
        ys.append(np.full(len(x), label, int))
        weights.append(np.full(len(x), 1 / (len(counts[label]) * counts[label][source] * len(x))))
    X, y, w = np.concatenate(xs), np.concatenate(ys), np.concatenate(weights)
    return RandomForestClassifier(random_state=seed, **dict(SMALL, class_weight=None)).fit(X, y, sample_weight=w * len(y))


def _prob(model, x, n):
    p = np.zeros((len(x), n))
    p[:, model.classes_.astype(int)] = model.predict_proba(x)
    return p


class EventExperts:
    """A reproducible RF baseline or real-event root with physics ring expert."""
    def __init__(self, method='protected', seed=11):
        if method not in ('injection', 'real', 'hybrid', 'protected'):
            raise ValueError(method)
        self.method, self.seed = method, seed

    def fit(self, healthy, synthetic, events, *, target_id):
        validate_events(events, target_id)
        if not len(healthy) or healthy.ndim != 2 or not np.isfinite(healthy).all():
            raise ValueError('Invalid healthy baseline')
        if set(synthetic) != {1, 2}:
            raise ValueError('Only validated inner/outer physics families are allowed')
        for x in list(synthetic.values()) + [e.features for e in events]:
            if x.ndim != 2 or x.shape[1] != healthy.shape[1] or not len(x) or not np.isfinite(x).all():
                raise ValueError('Invalid feature shape or values')
        self.event_ids_ = tuple(e.event_id for e in events)
        self.target_id_ = target_id
        bg = [(0, 'healthy', healthy)]
        syn = [(c, 'synthetic', x) for c, x in synthetic.items()]
        real = [(e.label, 'real', e.features) for e in events]
        self.root_ = None
        if self.method != 'protected' or not events:
            groups = bg + ([] if self.method == 'real' else syn)
            groups += [] if self.method == 'injection' else real
            self.model_ = _fit(groups, self.seed)
            return self
        # 0 healthy, 1 ring, 2 ball, 3 cage. No synthetic ball/cage labels.
        root = bg + [(1 if e.label in (1, 2) else e.label - 1, 'real', e.features) for e in events]
        if not any(e.label in (1, 2) for e in events):
            # Missing ring events: retain physical hypotheses as an explicit fallback.
            root += [(1, 'synthetic', x) for x in synthetic.values()]
        self.root_ = _fit(root, self.seed)
        self.model_ = _fit(bg + syn + [r for r in real if r[0] in (1, 2)], self.seed)
        return self

    def predict_proba(self, x):
        if self.root_ is None:
            return _prob(self.model_, x, 5)
        root = _prob(self.root_, x, 4)
        leaf = _prob(self.model_, x, 5)[:, 1:3]
        total = leaf.sum(1, keepdims=True)
        leaf = np.divide(leaf, total, out=np.full_like(leaf, .5), where=total > 0)
        return np.column_stack((root[:, 0], root[:, 1, None] * leaf, root[:, 2:]))


def causal_average(probabilities, width=5):
    if width < 1:
        raise ValueError('Window width must be positive')
    p = np.asarray(probabilities)
    c = np.vstack((np.zeros((1, p.shape[1])), np.cumsum(p, axis=0)))
    end = np.arange(1, len(p) + 1)
    start = np.maximum(0, end - width)
    return (c[end] - c[start]) / (end - start)[:, None]
