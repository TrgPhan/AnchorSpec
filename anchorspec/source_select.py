"""Donor-group selection of augmentation; all outputs are uncalibrated scores."""
from collections import defaultdict
from dataclasses import replace

import numpy as np
from scipy.special import softmax
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from adaptive_experts import event_folds, transform
from event_experts import causal_average, validate_events
from funnel import SMALL

SOURCES = ('real', 'surrogate_ring', 'physics', 'surrogate_all')
FAMILIES = ('rf', 'svm1', 'svm10', 'ridge')
REPS = ('raw', 'delta')


def training_arrays(events, derivatives, physics, source):
    """Only derivatives of explicitly supplied training events can enter a fit."""
    if source not in SOURCES or not events:
        raise ValueError('Known source and nonempty real events required')
    by_label = defaultdict(list)
    for e in events:
        by_label[e.label].append(e)
    groups = []
    quota = {}
    for label, ev in by_label.items():
        if source == 'physics' and label in physics:
            quota[label] = physics[label]
        elif source.startswith('surrogate') and (source == 'surrogate_all' or label in (1, 2)):
            # Round-robin ensures each donor contributes equally, at most 150.
            arr = [derivatives[e.event_id] for e in ev]
            take = 150 // len(arr)
            quota[label] = np.concatenate([a[:take] for a in arr])
        portion = .5 if label in quota else 1.
        groups += [(e.features, label, portion / len(ev)) for e in ev]
        if label in quota:
            groups.append((quota[label], label, .5))
    x = np.concatenate([a for a, _, _ in groups])
    y = np.concatenate([np.full(len(a), c, int) for a, c, _ in groups])
    w = np.concatenate([np.full(len(a), mass / len(a)) for a, _, mass in groups])
    # Keep the SVM penalty budget invariant to synthetic sample count.
    w *= sum(len(e.features) for e in events) / w.sum()
    if not np.isfinite(x).all():
        raise ValueError('Nonfinite training features')
    return x, y, w


class FaultModel:
    def __init__(self, family='rf', seed=11):
        if family not in FAMILIES:
            raise ValueError(family)
        self.family, self.seed = family, seed

    def fit(self, x, y, w):
        self.classes_ = np.unique(y)
        self.scaler_ = StandardScaler().fit(x, sample_weight=w)
        z = self.scaler_.transform(x)
        self.model_ = None
        if self.family == 'ridge':
            design = np.column_stack((z, np.ones(len(z))))
            hot = (y[:, None] == self.classes_).astype(float)
            penalty = np.eye(design.shape[1]); penalty[-1, -1] = 0
            self.coef_ = np.linalg.solve(design.T @ (w[:, None] * design) + penalty,
                                         design.T @ (w[:, None] * hot))
        elif len(self.classes_) > 1:
            if self.family == 'rf':
                self.model_ = RandomForestClassifier(random_state=self.seed, **dict(SMALL, class_weight=None))
            else:
                self.model_ = SVC(C=1 if self.family == 'svm1' else 10, gamma='scale', decision_function_shape='ovr')
            self.model_.fit(z, y, sample_weight=w)
        return self

    def predict_proba(self, x):
        z = self.scaler_.transform(x)
        if self.family == 'ridge':
            p = softmax(np.column_stack((z, np.ones(len(z)))) @ self.coef_, axis=1)
        elif self.model_ is None:
            p = np.ones((len(z), 1))
        elif self.family == 'rf':
            p = self.model_.predict_proba(z)
        else:
            score = self.model_.decision_function(z)
            if len(self.classes_) == 2:
                score = np.column_stack((-score, score))
            p = softmax(score, axis=1)
        out = np.zeros((len(x), 5))
        out[:, self.classes_] = p
        return out


class SourceSelector:
    def __init__(self, seed=11):
        self.seed = seed

    def fit(self, events, derivatives, physics, *, target_id, references):
        validate_events(events, target_id)
        if not events:
            raise ValueError('At least one confirmed fault event is required')
        self.reference_ = references[target_id]
        self.event_ids_ = [e.event_id for e in events]
        folds = event_folds(events)
        labels = {e.label for e in events}
        valid = all({e.label for e in events if e.event_id not in {v.event_id for v in fold}} == labels for fold in folds)
        self.inner_folds_ = [[e.event_id for e in f] for f in folds] if valid else []
        self.validation_ = []
        self.transformed_ = {}
        for rep in REPS:
            ev = [replace(e, features=transform(e.features, references[e.bearing_id], rep)) for e in events]
            der = {e.event_id: transform(derivatives[e.event_id], references[e.bearing_id], rep) for e in events}
            phy = {c: transform(a, self.reference_, rep) for c, a in physics.items()}
            self.transformed_[rep] = (ev, der, phy)
            if not valid:
                continue
            for source in SOURCES:
                for family in FAMILIES:
                    per_class = defaultdict(list)
                    for fold in folds:
                        ids = {e.event_id for e in fold}
                        train = [e for e in ev if e.event_id not in ids]
                        # training_arrays accesses only training event IDs.
                        model = FaultModel(family, self.seed).fit(*training_arrays(train, der, phy, source))
                        for e in ev:
                            if e.event_id in ids:
                                p = causal_average(model.predict_proba(e.features))
                                per_class[e.label].append(float((p.argmax(1) == e.label).mean()))
                    self.validation_.append(dict(source=source, family=family, representation=rep,
                        score=float(np.mean([np.mean(v) for v in per_class.values()]))))
        def key(row):
            return (row['score'], -SOURCES.index(row['source']), -FAMILIES.index(row['family']), -REPS.index(row['representation']))
        self.choices_ = {}
        for source in SOURCES:
            rows = [r for r in self.validation_ if r['source'] == source]
            self.choices_[source] = max(rows, key=key) if rows else dict(source=source, family='svm1', representation='raw', score=None)
        self.choices_['select'] = max(self.validation_, key=key) if valid else self.choices_['real']
        self.models_ = {}
        for name, choice in self.choices_.items():
            if name == 'select':
                self.models_[name] = self.models_[choice['source']]
            else:
                self.models_[name] = FaultModel(choice['family'], self.seed).fit(
                    *training_arrays(*self.transformed_[choice['representation']], choice['source']))
        del self.transformed_
        return self

    def predict(self, z, name='select', abnormal_event=True):
        if not abnormal_event:
            return np.zeros(len(z), int)
        p = self.models_[name].predict_proba(transform(z, self.reference_, self.choices_[name]['representation']))
        return causal_average(p).argmax(1)
