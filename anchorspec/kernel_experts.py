"""Nested event-level small-data SVM control; outputs are uncalibrated scores."""
from collections import defaultdict
from dataclasses import replace
import numpy as np
from scipy.special import softmax
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from adaptive_experts import transform, event_folds
from event_experts import validate_events, causal_average


class KernelModel:
    def __init__(self, C):
        self.C = C

    def fit(self, healthy, synthetic, events, mass):
        groups = [(0, 'healthy', healthy)]
        if mass:
            groups += [(c, 'synthetic', x) for c, x in synthetic.items()]
        groups += [(e.label, 'real', e.features) for e in events]
        counts = defaultdict(lambda: defaultdict(int))
        for c, source, x in groups:
            counts[c][source] += 1
        xs, ys, ws = [], [], []
        for c, source, x in groups:
            portion = 1.
            if 'synthetic' in counts[c] and 'real' in counts[c]:
                portion = mass if source == 'synthetic' else 1 - mass
            xs.append(x)
            ys.append(np.full(len(x), c, int))
            ws.append(np.full(len(x), portion / (counts[c][source] * len(x))))
        x, y, w = np.concatenate(xs), np.concatenate(ys), np.concatenate(ws)
        w *= len(w) / w.sum()
        self.classes_ = np.unique(y)
        self.scaler_ = StandardScaler().fit(x, sample_weight=w)
        self.model_ = None
        if len(self.classes_) > 1:
            self.model_ = SVC(C=self.C, gamma='scale', decision_function_shape='ovr').fit(self.scaler_.transform(x), y, sample_weight=w)
        return self

    def predict_proba(self, x):
        # API compatibility only: these scores are NOT calibrated probabilities.
        p = np.zeros((len(x), 5))
        if self.model_ is None:
            p[:, self.classes_[0]] = 1
        else:
            decision = self.model_.decision_function(self.scaler_.transform(x))
            if len(self.classes_) == 2:
                decision = np.column_stack((-decision, decision))
            p[:, self.classes_] = softmax(decision, axis=1)
        return p


class KernelExperts:
    def __init__(self, seed=11, real_only=False):
        self.seed, self.real_only = seed, real_only

    def fit(self, healthy, synthetic, events, *, target_id, references, donor_healthy):
        validate_events(events, target_id)
        self.reference_ = references[target_id]
        self.target_id_, self.event_ids_ = target_id, tuple(e.event_id for e in events)
        folds = event_folds(events)
        self.inner_folds_ = [[e.event_id for e in fold] for fold in folds]
        self.validation_ = []
        for rep in ('z', 'delta', 'raw'):
            h = transform(healthy, self.reference_, rep)
            syn = {c: transform(x, self.reference_, rep) for c, x in synthetic.items()}
            ev = {e.event_id: replace(e, features=transform(e.features, references[e.bearing_id], rep)) for e in events}
            for C in (1., 10.):
                for mass in ((0.,) if self.real_only else (0., .1, .5)):
                    scores = defaultdict(list)
                    for fold in folds:
                        ids = {e.event_id for e in fold}
                        model = KernelModel(C).fit(h, syn, [ev[e.event_id] for e in events if e.event_id not in ids], mass)
                        for event in fold:
                            pred = causal_average(model.predict_proba(ev[event.event_id].features)).argmax(1)
                            scores[event.label].append(float((pred == event.label).mean()))
                            xh = transform(donor_healthy[event.bearing_id], references[event.bearing_id], rep)
                            scores[0].append(float((model.predict_proba(xh).argmax(1) == 0).mean()))
                    objective = float(np.mean([np.mean(v) for v in scores.values()])) if scores else None
                    self.validation_.append({'representation': rep, 'synthetic_mass': mass, 'C': C, 'score': objective})
        if folds:
            best = max(self.validation_, key=lambda r: (r['score'], -r['synthetic_mass'], -r['C'], -('z','delta','raw').index(r['representation'])))
        else:
            best = {'representation': 'z', 'synthetic_mass': 0. if self.real_only else .5, 'C': 1.}
        self.representation_, self.synthetic_mass_, self.C_ = best['representation'], best['synthetic_mass'], best['C']
        rep = self.representation_
        self.model_ = KernelModel(self.C_).fit(transform(healthy, self.reference_, rep),
            {c: transform(x, self.reference_, rep) for c, x in synthetic.items()},
            [replace(e, features=transform(e.features, references[e.bearing_id], rep)) for e in events], self.synthetic_mass_)
        return self

    def predict_proba(self, z):
        return self.model_.predict_proba(transform(z, self.reference_, self.representation_))
