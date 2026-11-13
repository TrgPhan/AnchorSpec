"""PLAN.md WP0/WP1 shared pieces: uniform dataset access, library choice, mix_or_add, two-stage predictor, Flow utils.
Locked modules are only imported, never modified."""
import os
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
from functools import lru_cache
from math import cos, radians
import numpy as np
from u_natural import training
from s3_spectral import SpectralResidual, ResidualGenerator
from bearing import PADERBORN_6203, Bearing
import funnel as Fu
import pb_common as P
import m_hier as MH
import m_dev as MD
import s3_uored as UO
import e8_uored as E
from x_core import GEO
from m_dev import Model

SEEDS = (11, 29, 47, 101, 202, 303, 404, 505)
SENSOR = MD.SENSOR
NAMES = {0: 'khỏe', 1: 'trong', 2: 'ngoài', 3: 'bi', 4: 'cách'}


def orders_full(b):
    """Orders of shaft speed incl. BSF (ball spin)."""
    r = b.d / b.D * cos(radians(b.phi_deg))
    return b.orders() | {'bsf': b.D / (2 * b.d) * (1 - r * r)}


def char_order(c, orders):
    return {1: orders['bpfi'], 2: orders['bpfo'], 3: 2 * orders['bsf'], 4: orders['ftf']}[c]


# ---------------- datasets: uniform records ----------------
@lru_cache(maxsize=None)
def uored(i):
    it = UO.item(int(i)); hw, fr, _ = MD.healthy_waves('uored', int(i))
    return dict(id=int(i), label=it['label'], fr=float(fr), orders=orders_full(E.BEARING), feat_orders=E.ORDERS,
                healthy_w=hw[:, 0, :], healthy_f=it['base'], test_f=it['severe'], dev_f=it['developing'],
                donor_w=it['donor_w'], donor_f=it['donor'], donor_fr=np.full(len(it['donor_w']), float(fr)))


@lru_cache(maxsize=None)
def hust(cls, size):
    t = MH.hust_item(cls, size); bear = Bearing(GEO[size][3], GEO[size][2], (GEO[size][0] + GEO[size][1]) / 2, 0.)
    rec = dict(id=f'{cls}{size}', size=size, label=t['label'], orders=orders_full(bear), feat_orders=t['orders'], test_f=t['test'])
    if cls == 'N':
        rec.update(healthy_w=t['base_w'][:, 0, :], healthy_f=t['base'], fr=float(t['fr0']))
    else:
        w, frs = __import__('fusion').hust_donor_w(cls, size)
        rec.update(donor_w=w, donor_f=t['donor'], donor_fr=np.asarray(frs, float), fr=float(np.mean(frs)))
    return rec


@lru_cache(maxsize=None)
def pb(code):
    it = P.item(code)
    return dict(id=code, label=it['label'], fr=P.FR, orders=orders_full(PADERBORN_6203), feat_orders=P.ORDERS,
                healthy_w=it['donor_w'], healthy_f=it['base'], test_f=it['test'], donor_w=it['donor_w'], donor_f=it['donor'],
                donor_fr=np.full(len(it['donor_w']), P.FR))


UORED_IDS = {1: [1, 2, 3, 4, 5], 2: [6, 7, 8, 9, 10], 3: [11, 12, 13, 14, 15], 4: [16, 17, 18, 19, 20]}
HUST_IDS = {1: [('I', s) for s in (4, 5, 6, 7, 8)], 2: [('O', s) for s in (4, 5, 6, 7, 8)], 3: [('B', s) for s in (5, 6, 7, 8)]}
PB_IDS = {1: list(P.INNER_REAL), 2: list(P.OUTER_REAL)}
PBA_IDS = {1: list(P.INNER_ART), 2: list(P.OUTER_ART)}   # artificial damages: development only


@lru_cache(maxsize=None)
def xjtu(n):
    import s3_dose as D
    from u_natural import LABEL as XL
    it = D.item('xjtu', n); hw, fr, _ = MD.healthy_waves('xjtu', n)
    return dict(id=n, label=XL[n], fr=float(fr), orders=orders_full(Bearing(8, 7.92, 34.55, 0.)), feat_orders=it['orders'],
                healthy_w=hw[:, 0, :], healthy_f=it['base'], test_f=it['severe'], donor_w=it['donor_w'], donor_f=it['donor'],
                donor_fr=np.full(len(it['donor_w']), float(fr)))


def xjtu_ids():
    from u_natural import LABEL as XL
    return {c: [n for n in XL if XL[n] == c] for c in (1, 2, 4)}


def record(ds, key):
    if ds == 'xjtu':
        return xjtu(key)
    return uored(key) if ds == 'uored' else hust(*key) if ds == 'hust' else pb(key)   # 'pb' and 'pba'


def target_healthy(ds, key, seed):
    """Healthy background used for the target machine (same convention as the locked runs)."""
    if ds in ('uored', 'xjtu'):
        return record(ds, key)
    if ds == 'hust':
        return hust('N', key[1])
    return pb(P.healthy_for(key, seed))


def source_healthy(ds, key, seed):
    if ds in ('uored', 'xjtu'):
        return record(ds, key)['healthy_w'], record(ds, key)['fr']
    if ds == 'hust':
        h = hust('N', key[1]); return h['healthy_w'], h['fr']
    h = pb(P.healthy_for(key, seed)); return h['healthy_w'], h['fr']


def library(ds, target, seed, m, classes):
    """{class: [keys]} m events per class from other bearings (same rng convention as PB-HIER / HUST HIER / s3_dose)."""
    if ds == 'xjtu':   # natural inventory: every other bearing (m is ignored)
        return {c: [k for k in v if k != target] for c, v in xjtu_ids().items() if c in classes}
    ids = {'uored': UORED_IDS, 'hust': HUST_IDS, 'pb': PB_IDS, 'pba': PBA_IDS}[ds]; out = {}
    for c in classes:
        pool = sorted(k for k in ids[c] if k != target)
        perm = np.random.default_rng([seed, c, 20261112]).permutation(len(pool))
        out[c] = [pool[i] for i in perm[:m]]
    return out


def injected(ds, target, seed, kinds=((1, 'inner'), (2, 'outer'))):
    """A0 pool on the target healthy, exactly as the locked runs. Returns ({c: feats}, {c: waves})."""
    if ds in ('uored', 'xjtu'):
        key = int(target) if ds == 'uored' else target
        base, fr, orders = MD.healthy_waves(ds, key); rng = np.random.default_rng([seed, sum(map(ord, str(target))), 31])
        ff = lambda w: Fu.feats(w, 4000, fr, orders)
    elif ds == 'hust':
        H = MH.hust_item('N', target[1]); base, fr, orders = H['base_w'], H['fr0'], H['orders']
        rng = np.random.default_rng([seed, target[1], 31]); ff = lambda w: Fu.feats(w, 4000, fr, orders)
    else:
        H = P.item(P.healthy_for(target, seed)); base, fr, orders = H['donor_w'][:, None, :], P.FR, P.ORDERS
        rng = np.random.default_rng([seed, sum(map(ord, H['code'])), 31]); ff = lambda w: Fu.feats(w, 4000, P.FR, P.ORDERS)
    f, w = {}, {}
    for c, kind in kinds:
        x = Fu.injected(base, kind, 150, fr, orders, SENSOR, 4000, rng); f[c] = ff(x); w[c] = x[:, 0, :]
    return f, w


def target_feat(ds, target, seed):
    """Feature function for synthetic windows living on the target machine."""
    h = target_healthy(ds, target, seed)
    return lambda w: Fu.feats(np.asarray(w)[:, None, :], 4000, h['fr'], h['feat_orders'])


# ---------------- training sets ----------------
def mix_or_add(base, rows, beta, ids=None, row_ids=None):
    """As m_dev.mix (class keeps its total mass, synthetic share beta) but a class WITHOUT real rows is added
    with one class share of mass. ids/row_ids optionally carry a source id per row (for the open-set gate)."""
    x, y, w = base
    C = len(set(int(c) for c in np.unique(y) if c > 0) | set(rows))
    scale = len(x) / (1 + len([c for c in np.unique(y) if c > 0]))
    w2 = w.copy(); xs, ys, ws = [x], [y], [w2]; idl = [ids] if ids is not None else None
    for c, a in rows.items():
        if not len(a):
            continue
        if (y == c).any():
            w2[y == c] *= (1 - beta); mass = beta * scale
        else:
            mass = scale
        xs.append(a); ys.append(np.full(len(a), c, int)); ws.append(np.full(len(a), mass / len(a)))
        if idl is not None:
            idl.append(np.asarray(row_ids[c]))
    out = (np.concatenate(xs), np.concatenate(ys), np.concatenate(ws))
    return out + ((np.concatenate(idl),) if idl is not None else ())


def two_stage(base, tier1_rows, tier2_rows, seed, x, beta=.25, return_t1=False):
    """Locked two-stage architecture; tier1_rows {c: feats} enter stage 1 via mix_or_add; tier2_rows {1|2: feats} stage 2."""
    b1 = mix_or_add(base, tier1_rows, beta) if tier1_rows else base
    xb, yb, wb = b1[:3]
    ring = np.isin(yb, (1, 2))
    m1 = Model('et500', seed).fit(xb, np.where(ring, 1, yb), np.where(ring, wb * .5, wb))
    x2, y2, w2 = mix_or_add(base, tier2_rows, beta)
    keep = np.isin(y2, (1, 2))
    m2 = Model('et500', seed).fit(x2[keep], y2[keep], w2[keep])
    p1, p2 = m1.predict_proba(x), m2.predict_proba(x)
    p = p1.copy(); p[:, 1], p[:, 2] = p1[:, 1] * p2[:, 1], p1[:, 1] * p2[:, 2]
    return (p, m1, b1) if return_t1 else p


def real_base(ds, target, seed, lib):
    h = target_healthy(ds, target, seed)
    events = [(str(k), c, record(ds, k)['donor_f']) for c, keys in lib.items() for k in keys]
    return training(h['healthy_f'], events, {}, 'real'), events


# ---------------- Flow (S3 machinery, 4-class condition) ----------------
def fit_flow(ds, target, seed, lib):
    """S3 flow on the library's real fault windows (within-event residual pairs). Returns (codec, gen, cond_fn)."""
    keys = [(c, k) for c, ks in lib.items() for k in ks]
    h = target_healthy(ds, target, seed); rl = float(np.log(np.sqrt(np.mean(h['healthy_w'] ** 2))))
    waves, groups, cond, wts = [], [], [], []
    counts = {c: len(ks) for c, ks in lib.items()}
    for g, (c, k) in enumerate(keys):
        r = record(ds, k); n = len(r['donor_w'])
        waves.append(r['donor_w']); groups += [g] * n; wts += [1 / counts[c]] * n
        cond += [np.r_[np.eye(4)[c - 1], fr, rl] for fr in r['donor_fr']]
    waves = np.concatenate(waves); cond = np.asarray(cond); wts = np.asarray(wts)
    codec = SpectralResidual().fit(waves, np.asarray(groups), cond)
    gen = ResidualGenerator('flow', seed).fit(codec.z, codec.conditions[codec.pairs[:, 0]], wts[codec.pairs[:, 0]])
    codec._cond_fn = lambda c, fr: np.r_[np.eye(4)[c - 1], fr, rl]
    return codec, gen


def flow_variants(codec, gen, anchors, c, fr, seed, strength=.5):
    """One Flow variant around each anchor waveform (anchors on the target machine)."""
    anchors = np.asarray(anchors, float)
    q = codec.condition_scaler.transform(np.column_stack((codec.describe(anchors), np.repeat([codec_cond(c, fr, codec)], len(anchors), 0))))
    out, _ = codec.apply(anchors, gen.sample(q.astype(np.float32), seed) * codec.scale, strength, np.abs(anchors).max(1))
    return out


def codec_cond(c, fr, codec):
    return codec._cond_fn(c, fr)


GENERATORS_SALT = {'c_copy': 1, 'c_surr': 2, 'c_trans': 3, 'c_trans_flow': 4, 'c_flowgain': 5}
