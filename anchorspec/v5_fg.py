"""PLAN v5: half physics (inner/outer) + half Flow-gain (ball/cage), source-balanced stage 1.
Knobs (tuned on UORED only): ring physics share in stage 1, Flow-gain share, Flow-gain rows per class."""
import numpy as np
from event_experts import causal_average
from diagnostic_experts import fault_labels
from s3_spectral import SpectralResidual, ResidualGenerator
from m_dev import Model
import router_common as R
import v4_flow as V

NOLAW = (3, 4)
# name -> (ring physics share in stage 1, Flow-gain share, rows: 'ev20' = 20 per event | 'c150' = 150 per class)
CONFIGS = {f'fg_r{int(r*100):02d}_s{int(s*100):02d}_{n}': (r, s, n) for r in (.10, .25) for s in (.25, .50) for n in ('ev20', 'c150')}
EQUIV = {r: f'phys_r{int(r*100):02d}' for r in (.10, .25)}     # same stage-1 ring share, no Flow rows (photocopy-equivalent)


def assignment(cfg):
    return {1: 'physics', 2: 'physics', 3: 'flow', 4: 'flow'}


def mix_multi(base, rows, betas):
    """Per-class synthetic share betas[c]; scale fixed from the real base (one class mass)."""
    x, y, w = base
    scale = len(x) / (1 + len([c for c in np.unique(y) if c > 0]))
    w2 = w.copy(); xs, ys, ws = [x], [y], [w2]
    for c, a in rows.items():
        if not len(a):
            continue
        b = betas[c]
        if (y == c).any():
            w2[y == c] *= (1 - b); mass = b * scale
        else:
            mass = scale
        xs.append(a); ys.append(np.full(len(a), c, int)); ws.append(np.full(len(a), mass / len(a)))
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(ws)


class FlowGain:
    """Flow (Truong's S3 network) learns (fault - own healthy) 24-band residuals of one class from REAL events of other
    machines, warped to the target's characteristic frequency; sampled residuals are applied to the target healthy windows."""

    def __init__(self, ds, target, seed, c, keys, nmax=150):
        h = R.target_healthy(ds, target, seed); self.tfeat = R.target_feat(ds, target, seed)
        sr = SpectralResidual(); res = []
        for k in keys:
            rec = R.record(ds, k); src_h, _ = R.source_healthy(ds, k, seed)
            r = sr.describe(rec['donor_w']) - sr.describe(src_h).mean(0)
            f_t = R.char_order(c, h['orders']) * h['fr']; f_s = R.char_order(c, rec['orders']) * rec['fr']
            res.append(np.stack([np.interp(sr.centers / (f_t / f_s), sr.centers, v) for v in r]))
        res = np.concatenate(res); scale = np.maximum(res.std(0), .05)
        gen = ResidualGenerator('flow', seed).fit((res / scale).astype(np.float32), np.zeros((len(res), 1), np.float32), np.ones(len(res), np.float32))
        z = gen.sample(np.zeros((nmax, 1), np.float32), seed + 29) * scale
        sr.lo, sr.hi = np.full(sr.bands, -np.log(2)), np.full(sr.bands, np.log(2))
        rng = np.random.default_rng([seed, c, 777, 5])
        anchors = h['healthy_w'][rng.integers(len(h['healthy_w']), size=nmax)]
        w, _ = sr.apply(anchors, z, 1., np.full(nmax, 8.))
        self.feats = self.tfeat(w)            # nmax rows; smaller budgets take a prefix (same draws)


def two_stage_cfg(base, t1_rows, betas, inj_f, seed, test):
    b1 = mix_multi(base, t1_rows, betas) if t1_rows else base
    xb, yb, wb = b1; ring = np.isin(yb, (1, 2))
    m1 = Model('et500', seed).fit(xb, np.where(ring, 1, yb), np.where(ring, wb * .5, wb))
    x2, y2, w2 = R.mix_or_add(base, inj_f, .25); keep = np.isin(y2, (1, 2))     # stage 2 = locked
    m2 = Model('et500', seed).fit(x2[keep], y2[keep], w2[keep])
    p1, p2 = m1.predict_proba(test), m2.predict_proba(test)
    p = p1.copy(); p[:, 1], p[:, 2] = p1[:, 1] * p2[:, 1], p1[:, 1] * p2[:, 2]
    return fault_labels(causal_average(p)).tolist()


def predict(arm, ds, target, seed, lib, base, inj, test, cache):
    """arm: 'hier' | phys_rXX (ring physics only) | fg_* (CONFIGS)."""
    inj_f = inj[0]
    if arm == 'hier':
        return two_stage_cfg(base, {}, {}, inj_f, seed, test)
    if arm.startswith('phys_r'):
        r = int(arm[6:]) / 100
        return two_stage_cfg(base, {1: inj_f[1], 2: inj_f[2]}, {1: r, 2: r}, inj_f, seed, test)
    r, s, n = CONFIGS[arm]; V.assert_exclusive(assignment(arm))
    rows = {1: inj_f[1], 2: inj_f[2]}; betas = {1: r, 2: r}
    for c in NOLAW:
        keys = lib.get(c, [])
        if not keys:
            continue
        if ('fg', c) not in cache:
            cache[('fg', c)] = FlowGain(ds, target, seed, c, keys)
        k = 20 * len(keys) if n == 'ev20' else 150
        rows[c] = cache[('fg', c)].feats[:k]; betas[c] = s
    return two_stage_cfg(base, rows, betas, inj_f, seed, test)


ARMS = ('hier', 'phys_r10', 'phys_r25') + tuple(CONFIGS)
