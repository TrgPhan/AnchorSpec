"""Select representation and physics weight using only donor-bearing validation."""
from collections import defaultdict
from dataclasses import replace
import numpy as np
from sklearn.ensemble import RandomForestClassifier

from event_experts import validate_events, causal_average, _prob
from funnel import SMALL


def transform(z, reference, representation):
    if representation == 'z':
        return z
    delta = z * reference['sd']
    return delta if representation == 'delta' else delta + reference['mu']


def fit_weighted(healthy, synthetic, events, mass, seed):
    groups = [(0, 'healthy', healthy)]
    if mass:
        groups += [(c, 'synthetic', x) for c, x in synthetic.items()]
    groups += [(e.label, 'real', e.features) for e in events]
    sources = defaultdict(lambda: defaultdict(int))
    for c, s, x in groups:
        sources[c][s] += 1
    xs, ys, ws = [], [], []
    for c, s, x in groups:
        source_mass = 1.
        if 'synthetic' in sources[c] and 'real' in sources[c]:
            source_mass = mass if s == 'synthetic' else 1 - mass
        xs.append(x)
        ys.append(np.full(len(x), c, int))
        ws.append(np.full(len(x), source_mass / (sources[c][s] * len(x))))
    X, y, w = np.concatenate(xs), np.concatenate(ys), np.concatenate(ws)
    return RandomForestClassifier(random_state=seed, **dict(SMALL, class_weight=None)).fit(X, y, sample_weight=w * len(y))


def event_folds(events):
    """All events from one bearing remain in one fold, including mixed labels."""
    by_bearing = defaultdict(list)
    for event in events:
        by_bearing[event.bearing_id].append(event)
    by_label = defaultdict(list)
    for bearing_id, group in by_bearing.items():
        by_label[min(e.label for e in group)].append(bearing_id)
    n_folds = min(4, max((len(v) for v in by_label.values()), default=0))
    folds = [[] for _ in range(n_folds)]
    for group in by_label.values():
        for index, bearing_id in enumerate(group):
            folds[index % n_folds].extend(by_bearing[bearing_id])
    return folds


class AdaptiveExperts:
    """A model-selection procedure, not an unknown detector or label validator."""
    def __init__(self, seed=11, real_only=False):
        self.seed, self.real_only = seed, real_only

    def fit(self, healthy, synthetic, events, *, target_id, references, donor_healthy):
        validate_events(events, target_id)
        self.target_id_ = target_id
        self.reference_ = references[target_id]
        self.event_ids_ = tuple(e.event_id for e in events)
        self.validation_ = []
        folds = event_folds(events)
        self.inner_folds_ = [[e.event_id for e in f] for f in folds]
        for rep in ('z', 'delta', 'raw'):
            h = transform(healthy, self.reference_, rep)
            syn = {c: transform(x, self.reference_, rep) for c, x in synthetic.items()}
            ev = {e.event_id: replace(e, features=transform(e.features, references[e.bearing_id], rep)) for e in events}
            for mass in ((0.,) if self.real_only else (0., .1, .5)):
                scores = defaultdict(list)
                for fold in folds:
                    ids = {e.event_id for e in fold}
                    train = [ev[e.event_id] for e in events if e.event_id not in ids]
                    model = fit_weighted(h, syn, train, mass, self.seed)
                    for event in fold:
                        p = causal_average(_prob(model, ev[event.event_id].features, 5))
                        scores[event.label].append(float((p.argmax(1) == event.label).mean()))
                        held_healthy = transform(donor_healthy[event.bearing_id], references[event.bearing_id], rep)
                        scores[0].append(float((_prob(model, held_healthy, 5).argmax(1) == 0).mean()))
                objective = float(np.mean([np.mean(v) for v in scores.values()])) if scores else None
                self.validation_.append({'representation': rep, 'synthetic_mass': mass, 'score': objective})
        if folds:
            best = max(self.validation_, key=lambda r: (r['score'], -r['synthetic_mass'], -('z', 'delta', 'raw').index(r['representation'])))
        else:
            best = {'representation': 'z', 'synthetic_mass': 0. if self.real_only else .5}
        self.representation_ = best['representation']
        self.synthetic_mass_ = best['synthetic_mass']
        rep = self.representation_
        self.model_ = fit_weighted(transform(healthy, self.reference_, rep),
            {c: transform(x, self.reference_, rep) for c, x in synthetic.items()},
            [replace(e, features=transform(e.features, references[e.bearing_id], rep)) for e in events],
            self.synthetic_mass_, self.seed)
        return self

    def predict_proba(self, z):
        return _prob(self.model_, transform(z, self.reference_, self.representation_), 5)
