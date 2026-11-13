"""Feature-space Flow (FF): Flow matching (Truong's ResidualGenerator network) learns, per fault class, the distribution of
feature DELTAS d = fault-window features - mean healthy features of the same source machine, from real library events.
Synthetic rows = target healthy features + sampled delta (every fault class gets target-canvas rows -> source-balanced).
Control 'BS' = same but deltas bootstrapped from the empirical real deltas (no Flow)."""
import numpy as np
from event_experts import causal_average
from diagnostic_experts import fault_labels
from s3_spectral import ResidualGenerator
from m_dev import Model
import router_common as R
from v5_fg import mix_multi

N_PER_CLASS = 150


def source_healthy_f(ds, k, seed):
    if ds in ('uored', 'xjtu'):
        return R.record(ds, k)['healthy_f']
    if ds == 'hust':
        return R.hust('N', k[1])['healthy_f']
    return R.pb(R.P.healthy_for(k, seed))['healthy_f']


class DeltaGen:
    def __init__(self, ds, target, seed, lib):
        D, Y = [], []
        for c, keys in lib.items():
            for k in keys:
                d = R.record(ds, k)['donor_f'] - source_healthy_f(ds, k, seed).mean(0)
                D.append(d); Y += [c] * len(d)
        self.D, self.Y = np.concatenate(D), np.asarray(Y); self.classes = sorted(set(self.Y)); self.seed = seed
        self.mu, self.sd = self.D.mean(0), np.maximum(self.D.std(0), 1e-6)
        onehot = lambda y: np.eye(5)[y][:, 1:]
        cnt = {c: (self.Y == c).sum() for c in self.classes}
        self.gen = ResidualGenerator('flow', seed).fit(((self.D - self.mu) / self.sd).astype(np.float32), onehot(self.Y).astype(np.float32),
                                                       np.array([1 / cnt[c] for c in self.Y], np.float32))
        self.onehot = onehot
        h = R.target_healthy(ds, target, seed); self.canvas = h['healthy_f']
        self.rng = np.random.default_rng([seed, 4242, sum(map(ord, str(target)))])
        self.anchor = {c: self.canvas[self.rng.integers(len(self.canvas), size=N_PER_CLASS)] for c in self.classes}
        self.flow = {c: self.anchor[c] + self.gen.sample(self.onehot(np.full(N_PER_CLASS, c)).astype(np.float32), seed + 100 + c) * self.sd + self.mu
                     for c in self.classes}
        self.boot = {c: self.anchor[c] + self.D[self.Y == c][self.rng.integers((self.Y == c).sum(), size=N_PER_CLASS)] for c in self.classes}


# arm -> (generator 'ff'|'bs'|None, stage-1 share, stage-2 physics share, stage-2 generated share)
ARMS = {'hier': (None, 0, .25, 0), 'ff_t1': ('ff', .25, .25, 0), 'ff_t12': ('ff', .25, .125, .125), 'ff_t2': ('ff', 0, .125, .125),
        'bs_t1': ('bs', .25, .25, 0), 'bs_t12': ('bs', .25, .125, .125), 'bs_t2': ('bs', 0, .125, .125)}


def predict(arm, ds, target, seed, lib, base, inj, test, dg):
    g, s1, sp, s2 = ARMS[arm]; inj_f = inj[0]; rows = (dg.flow if g == 'ff' else dg.boot) if g else {}
    # stage 1: every fault class present in the library gets generated rows (balanced)
    t1 = {c: rows[c] for c in rows} if s1 else {}
    b1 = mix_multi(base, t1, {c: s1 for c in t1}) if t1 else base
    xb, yb, wb = b1; ring = np.isin(yb, (1, 2))
    m1 = Model('et500', seed).fit(xb, np.where(ring, 1, yb), np.where(ring, wb * .5, wb))
    # stage 2: inner vs outer, physics (+ generated)
    x2, y2, w2 = base
    parts = {1: [inj_f[1]], 2: [inj_f[2]]}; shares = {1: sp, 2: sp}
    if s2:
        xs, ys, ws = [x2], [y2], [w2.copy()]
        scale = len(x2) / (1 + len([c for c in np.unique(y2) if c > 0]))
        for c in (1, 2):
            xs[0] = xs[0]; ws[0][y2 == c] *= (1 - sp - s2)
            for a, sh in ((inj_f[c], sp), (rows[c], s2)):
                xs.append(a); ys.append(np.full(len(a), c, int)); ws.append(np.full(len(a), sh * scale / len(a)))
        x2, y2, w2 = np.concatenate(xs), np.concatenate(ys), np.concatenate(ws)
    else:
        x2, y2, w2 = mix_multi(base, {1: inj_f[1], 2: inj_f[2]}, shares)
    keep = np.isin(y2, (1, 2))
    m2 = Model('et500', seed).fit(x2[keep], y2[keep], w2[keep])
    p1, p2 = m1.predict_proba(test), m2.predict_proba(test)
    p = p1.copy(); p[:, 1], p[:, 2] = p1[:, 1] * p2[:, 1], p1[:, 1] * p2[:, 2]
    return fault_labels(causal_average(p)).tolist()
