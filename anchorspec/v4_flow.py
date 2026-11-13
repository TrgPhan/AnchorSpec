"""PLAN_V4.md: one generator per fault class. Inner/outer -> physics only; ball/cage -> Flow only (Truong's S3 model,
s3_spectral), learned from REAL fault windows of that class. Optional source-balanced stage 1 (variant B)."""
import numpy as np
from event_experts import causal_average
from diagnostic_experts import fault_labels
from s3_spectral import SpectralResidual, ResidualGenerator
from m_dev import Model
import router_common as R
import branch_c as BC

NOLAW = (3, 4)      # classes without a validated physics rule
SHARE, ADD = .25, .25

# arm -> (stage-1 ring rows, no-law generator, weighting, rows per event)
ARMS = {
    'hier':          (None,   None,               None,    0),
    'copy':          (None,   'copy',             'share', 20),
    'flow_within_05': (None,  ('within', .5),     'share', 20),
    'flow_within_10': (None,  ('within', 1.),     'share', 20),
    'flow_class_05': (None,   ('class', .5),      'share', 20),
    'flow_class_10': (None,   ('class', 1.),      'share', 20),
    'flow_truong':   (None,   ('within', .5),     'add',   10),   # Truong's recipe: 1 per real window, +0.25 additive
    'copy_add':      (None,   'copy',             'add',   10),   # its photocopy control
    'bal_phys':      ('phys', None,               None,    0),
    'bal_copy':      ('phys', 'copy',             'share', 20),
    'bal_flowgain':  ('phys', 'flowgain',         'share', 20),
}
CONTROL = {'flow_within_05': 'copy', 'flow_within_10': 'copy', 'flow_class_05': 'copy', 'flow_class_10': 'copy',
           'flow_truong': 'copy_add', 'bal_flowgain': 'bal_copy'}
FLOW_SRC = ('flow_within_05', 'flow_within_10', 'flow_class_05', 'flow_class_10', 'flow_truong')


def assignment(arm):
    ring, gen, _, _ = ARMS[arm]
    method = None if gen is None else 'copy' if gen == 'copy' else 'flow'
    return {1: 'physics', 2: 'physics', 3: method, 4: method}


def assert_exclusive(assign):
    """Each class has exactly one generator (or none); physics only for classes with a validated rule."""
    for c, m in assign.items():
        if isinstance(m, (list, tuple, set)) and len(m) > 1:
            raise ValueError(f'class {c} has {len(m)} generators')
        if m == 'physics' and c not in (1, 2):
            raise ValueError(f'class {c} has no validated physics rule')
        if m == 'flow' and c in (1, 2):
            raise ValueError(f'class {c} is physics-only')
    return True


class ClassFlow:
    """Truong's S3 flow, fitted on the real fault windows of ONE class. pairs='within' (same event) or 'class' (any two
    windows of the class, across machines; falls back to within when only one event)."""

    def __init__(self, ds, keys, pairs, seed):
        self.recs = [R.record(ds, k) for k in keys]; self.seed = seed
        waves = np.concatenate([r['donor_w'] for r in self.recs]); n = [len(r['donor_w']) for r in self.recs]
        self.off = np.r_[0, np.cumsum(n)[:-1]]
        groups = np.repeat(np.arange(len(n)), n) if pairs == 'within' or len(n) == 1 else np.zeros(sum(n), int)
        cond = np.concatenate([r['donor_fr'] for r in self.recs])[:, None]
        self.waves = waves; self.codec = SpectralResidual().fit(waves, groups, cond)
        self.gen = ResidualGenerator('flow', seed).fit(self.codec.z, self.codec.conditions[self.codec.pairs[:, 0]], np.ones(len(self.codec.pairs)))
        self._res = {}

    def rows(self, per_event, strength):
        out = []
        for e, rec in enumerate(self.recs):
            idx = np.arange(per_event) % len(rec['donor_w']); g = self.off[e] + idx
            key = (e, per_event)
            if key not in self._res:   # same residual draws for both strengths
                self._res[key] = self.gen.sample(self.codec.conditions[g], self.seed + 1000 + e) * self.codec.scale
            w, _ = self.codec.apply(self.waves[g], self._res[key], strength, np.full(len(g), np.abs(rec['donor_w']).max()))
            out.append(BC._src_feats(rec, w, idx))
        return np.concatenate(out)


def add_rows(base, rows, alpha=ADD):
    """Truong's additive weighting: real weights untouched, synthetic rows of class c add alpha x one class mass."""
    x, y, w = base
    scale = len(x) / (1 + len([c for c in np.unique(y) if c > 0]))
    xs, ys, ws = [x], [y], [w]
    for c, a in rows.items():
        if len(a):
            xs.append(a); ys.append(np.full(len(a), c, int)); ws.append(np.full(len(a), alpha * scale / len(a)))
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(ws)


def predict_arm(arm, ds, target, seed, lib, base, inj, test, cache):
    """cache: per-task dict (flows, flowgain rows). Returns per-window labels (only-fault-type scoring)."""
    ring, gen, weighting, per = ARMS[arm]; assert_exclusive(assignment(arm))
    nolaw_rows = {}
    for c in NOLAW:
        keys = lib.get(c, [])
        if gen is None or not keys:
            continue
        if gen == 'copy':
            nolaw_rows[c] = np.concatenate([R.record(ds, k)['donor_f'][np.arange(per) % len(R.record(ds, k)['donor_f'])] for k in keys])
        elif gen == 'flowgain':
            if ('fg', c) not in cache:
                cache[('fg', c)] = BC.rows('c_flowgain', ds, target, seed, c, keys)
            nolaw_rows[c] = cache[('fg', c)]
        else:
            pairs, strength = gen
            if ('flow', c, pairs) not in cache:
                cache[('flow', c, pairs)] = ClassFlow(ds, keys, pairs, seed)
            nolaw_rows[c] = cache[('flow', c, pairs)].rows(per, strength)
    inj_f = inj[0]
    share = dict(nolaw_rows) if weighting == 'share' else {}
    if ring == 'phys':
        share.update({1: inj_f[1], 2: inj_f[2]})
    b1 = R.mix_or_add(base, share, SHARE) if share else base
    if weighting == 'add':
        b1 = add_rows(b1, nolaw_rows)
    # stage 1 on b1, stage 2 = locked (real + physics inner/outer)
    xb, yb, wb = b1[:3]; ringm = np.isin(yb, (1, 2))
    m1 = Model('et500', seed).fit(xb, np.where(ringm, 1, yb), np.where(ringm, wb * .5, wb))
    x2, y2, w2 = R.mix_or_add(base, inj_f, SHARE); keep = np.isin(y2, (1, 2))
    m2 = Model('et500', seed).fit(x2[keep], y2[keep], w2[keep])
    p1, p2 = m1.predict_proba(test), m2.predict_proba(test)
    p = p1.copy(); p[:, 1], p[:, 2] = p1[:, 1] * p2[:, 1], p1[:, 1] * p2[:, 2]
    return fault_labels(causal_average(p)).tolist()
