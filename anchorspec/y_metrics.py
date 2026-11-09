"""Bearing-level metrics; windows and random seeds are not independent trials."""
from collections import defaultdict
import numpy as np


def bearing_values(rows, method, metric, *, budget, state='late', labels=None, control='clean'):
    groups = defaultdict(list)
    for r in rows:
        if r['budget'] != budget or r['control'] != control:
            continue
        if labels is not None and r['label'] not in labels:
            continue
        groups[(r['target'], r['label'])].append(r['scores'][method][state][metric])
    return {key: float(np.mean(values)) for key, values in groups.items()}


def macro(values):
    classes = defaultdict(list)
    for (_, label), value in values.items():
        classes[label].append(value)
    return float(np.mean([np.mean(v) for v in classes.values()])) if classes else None


def paired_delta(a, b, resamples=5000, seed=20261102):
    if not a or set(a) != set(b):
        raise ValueError('Paired metrics require identical nonempty bearing sets')
    groups = defaultdict(list)
    for key in sorted(a):
        groups[key[1]].append(a[key] - b[key])
    rng = np.random.default_rng(seed)
    boot = np.zeros(resamples)
    for values in groups.values():
        values = np.asarray(values)
        boot += values[rng.integers(len(values), size=(resamples, len(values)))].mean(1) / len(groups)
    return {'delta': macro(a) - macro(b), 'ci95': np.quantile(boot, [.025, .975]).tolist(),
            'n_bearings': len(a), 'n_by_class': {str(k): len(v) for k, v in groups.items()},
            'resamples': resamples, 'seed': seed}
