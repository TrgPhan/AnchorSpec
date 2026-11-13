"""PLAN.md WP4: 'unknown' gate. kNN distance (k=5) in the weighted-standardized stage-1 feature space;
threshold = kappa x q95 of leave-one-event-out distances of the real library events. Causal mean over 5 windows."""
import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

KAPPAS = (1.0, 1.25, 1.5, 2.0, 3.0)


def causal_mean(d, width=5):
    c = np.r_[0., np.cumsum(d)]; end = np.arange(1, len(d) + 1); start = np.maximum(0, end - width)
    return (c[end] - c[start]) / (end - start)


def gate_data(b1, ids, test_x, k=5):
    """Returns (smoothed distance per test window, q95 LOO distance of real fault events)."""
    x, y, w = b1[:3]; ids = np.asarray(ids)
    sc = StandardScaler().fit(x, sample_weight=w); Z = sc.transform(x)
    d = NearestNeighbors(n_neighbors=k).fit(Z).kneighbors(sc.transform(test_x))[0].mean(1)
    loo = []
    for e in sorted(set(ids) - {'H'}):
        m = ids == e
        loo.append(NearestNeighbors(n_neighbors=k).fit(Z[~m]).kneighbors(Z[m])[0].mean(1))
    return causal_mean(d), float(np.quantile(np.concatenate(loo), .95))


def apply_gate(labels, dist, q95, kappa):
    out = np.asarray(labels).copy(); out[np.asarray(dist) > kappa * q95] = -1
    return out
