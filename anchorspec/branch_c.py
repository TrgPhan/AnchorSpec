"""PLAN.md WP3: generators for a fault class WITHOUT a physics rule, from real events of that class on OTHER machines.
Every generator returns 20 feature rows per source event; all enter stage 1 through router_common.mix_or_add (25%)."""
import importlib.util
from functools import lru_cache
import numpy as np
import funnel as Fu
from s3_spectral import SpectralResidual, ResidualGenerator
import measured_transport as MT
import router_common as R

PER_EVENT = 20
GENERATORS = ('c_none', 'c_copy', 'c_surr', 'c_trans', 'c_trans_flow', 'c_flowgain')


@lru_cache(maxsize=None)
def _surrogate():
    spec = importlib.util.spec_from_file_location('legacy_generators', R.P.ROOT.parent / 'generator_benchmark' / 'generators.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.constrained_surrogate


def _src_feats(rec, w, idx):
    """Features of windows w that live on the SOURCE machine (window idx -> its own speed)."""
    return np.concatenate([Fu.feats(w[i:i + 1, None, :], 4000, rec['donor_fr'][j], rec['feat_orders']) for i, j in enumerate(idx)])


def _ratio(ds, target, seed, c, rec):
    h = R.target_healthy(ds, target, seed)
    return R.char_order(c, h['orders']) * h['fr'], R.char_order(c, rec['orders']) * rec['fr']


def rows(kind, ds, target, seed, c, keys, flow=None):
    """kind in GENERATORS; keys: library events of class c. flow: (codec, gen) shared per task (for c_trans_flow)."""
    if kind == 'c_none' or not keys:
        return np.zeros((0, 45))
    h = R.target_healthy(ds, target, seed); tfeat = R.target_feat(ds, target, seed)
    rng = np.random.default_rng([seed, c, 777, R.GENERATORS_SALT.get(kind, 0)])
    out = []
    if kind == 'c_flowgain':
        return _flowgain(ds, target, seed, c, keys, rng)
    for k in keys:
        rec = R.record(ds, k); idx = np.arange(PER_EVENT) % len(rec['donor_w'])
        if kind == 'c_copy':
            out.append(rec['donor_f'][idx])
        elif kind == 'c_surr':
            sur = _surrogate()
            out.append(_src_feats(rec, np.stack([sur(rec['donor_w'][j], rng) for j in idx]), idx))
        elif kind in ('c_trans', 'c_trans_flow'):
            f_t, f_s = _ratio(ds, target, seed, c, rec)
            src_h, _ = R.source_healthy(ds, k, seed)
            n_tr = PER_EVENT if kind == 'c_trans' else PER_EVENT // 2
            arrays, _ = MT.generate(rec['donor_w'], src_h, h['healthy_w'], f_s, f_t, rng, count=n_tr)
            w = arrays['transport']
            if kind == 'c_trans_flow':
                codec, gen = flow
                w = np.concatenate([w, R.flow_variants(codec, gen, w, c, h['fr'], seed + 13)])
            out.append(tfeat(w))
    return np.concatenate(out)


def _flowgain(ds, target, seed, c, keys, rng):
    """Flow learns (fault - own healthy) 24-band log-amplitude residuals of the source machines, warped to the
    target's characteristic frequency, and applies sampled residuals as spectral gains on the TARGET healthy windows."""
    h = R.target_healthy(ds, target, seed); tfeat = R.target_feat(ds, target, seed)
    sr = SpectralResidual(); res = []
    for k in keys:
        rec = R.record(ds, k); src_h, _ = R.source_healthy(ds, k, seed)
        r = sr.describe(rec['donor_w']) - sr.describe(src_h).mean(0)
        f_t, f_s = _ratio(ds, target, seed, c, rec); kr = f_t / f_s
        res.append(np.stack([np.interp(sr.centers / kr, sr.centers, v) for v in r]))
    res = np.concatenate(res)
    scale = np.maximum(res.std(0), .05)
    gen = ResidualGenerator('flow', seed).fit((res / scale).astype(np.float32), np.zeros((len(res), 1), np.float32), np.ones(len(res), np.float32))
    n = PER_EVENT * len(keys)
    z = gen.sample(np.zeros((n, 1), np.float32), seed + 29) * scale
    sr.lo, sr.hi = np.full(sr.bands, -np.log(2)), np.full(sr.bands, np.log(2))
    anchors = h['healthy_w'][rng.integers(len(h['healthy_w']), size=n)]
    w, _ = sr.apply(anchors, z, 1., np.full(n, 8.))
    return tfeat(w)
