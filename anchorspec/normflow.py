"""NF: machine-relative features (each machine's features minus its own healthy mean, optionally / healthy std) + Flow
matching (Truong's ResidualGenerator) on the pooled machine-relative fault deltas, class-conditional. Every row - library
events, physics samples, Flow samples, test windows - lives in the same machine-relative space, so no row carries a
'which machine' cue. Controls: same space without Flow; bootstrap of real deltas."""
import numpy as np
from event_experts import causal_average
from diagnostic_experts import fault_labels
from s3_spectral import ResidualGenerator
from m_dev import Model
from u_natural import training
import router_common as R
from flowfeat import source_healthy_f
from v5_fg import mix_multi

N = 150


def stats(hf, mode):
    mu = hf.mean(0); sd = np.maximum(hf.std(0), np.median(hf.std(0)) * .5 + 1e-9) if mode == 'z' else 1.
    return mu, sd


def build(ds, target, seed, lib, inj_f, mode):
    th = R.target_healthy(ds, target, seed)['healthy_f']; tmu, tsd = stats(th, mode)
    tf = lambda x: (x - tmu) / tsd
    events, D, Y = [], [], []
    for c, keys in lib.items():
        for k in keys:
            hf = source_healthy_f(ds, k, seed); mu, sd = stats(hf, mode); d = (R.record(ds, k)['donor_f'] - mu) / sd
            events.append((str(k), c, d)); D.append(d); Y += [c] * len(d)
    base = training(tf(th), events, {}, 'real')
    return base, {c: tf(inj_f[c]) for c in (1, 2)}, tf, np.concatenate(D), np.asarray(Y)


def flow_rows(D, Y, seed):
    cls = sorted(set(Y)); mu, sd = D.mean(0), np.maximum(D.std(0), 1e-6); oh = lambda y: np.eye(5)[y][:, 1:].astype(np.float32)
    cnt = {c: (Y == c).sum() for c in cls}
    g = ResidualGenerator('flow', seed).fit(((D - mu) / sd).astype(np.float32), oh(Y), np.array([1 / cnt[c] for c in Y], np.float32))
    return {c: g.sample(oh(np.full(N, c)), seed + 300 + c) * sd + mu for c in cls}


def boot_rows(D, Y, seed):
    rng = np.random.default_rng([seed, 7070])
    return {c: D[Y == c][rng.integers((Y == c).sum(), size=N)] for c in sorted(set(Y))}


def two_stage(base, t1, s1, t2, seed, test, sp=.25):
    b1 = mix_multi(base, t1, {c: s1 for c in t1}) if t1 else base
    xb, yb, wb = b1; ring = np.isin(yb, (1, 2))
    m1 = Model('et500', seed).fit(xb, np.where(ring, 1, yb), np.where(ring, wb * .5, wb))
    x2, y2, w2 = mix_multi(base, t2, {c: sp for c in t2}); keep = np.isin(y2, (1, 2))
    m2 = Model('et500', seed).fit(x2[keep], y2[keep], w2[keep])
    p1, p2 = m1.predict_proba(test), m2.predict_proba(test)
    p = p1.copy(); p[:, 1], p[:, 2] = p1[:, 1] * p2[:, 1], p1[:, 1] * p2[:, 2]
    return fault_labels(causal_average(p)).tolist()


def arms(ds, target, seed, lib, inj_f, test_raw):
    out = {}
    for mode in ('m', 'z'):
        base, inj_n, tf, D, Y = build(ds, target, seed, lib, inj_f, mode); test = tf(test_raw)
        fr, br = flow_rows(D, Y, seed), boot_rows(D, Y, seed)
        out[f'norm{mode}'] = two_stage(base, {}, 0, inj_n, seed, test)                  # normalization only (no Flow)
        out[f'norm{mode}_flow_t1'] = two_stage(base, fr, .25, inj_n, seed, test)        # + Flow rows, stage 1, all fault classes
        out[f'norm{mode}_boot_t1'] = two_stage(base, br, .25, inj_n, seed, test)        # + bootstrap rows (control)
    return out
