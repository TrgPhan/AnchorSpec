"""Shared Paderborn access for the overnight PB-* experiments (cheap-sensor simulation as in TN2).

Condition N15_M07_F10, 20 recordings x 4 s at 64 kHz per bearing (data/paderborn/cache). Units assumed m/s^2
and divided by 9.81 as in TN2; nominal speed 25 Hz. Sensor noise uses a fixed seed per bearing code, so the data
do not change with the experiment seed. Windows are 1 s, non-overlapping: 4 per recording, 80 per bearing.
"""
import os
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
from collections import Counter
from functools import lru_cache
from pathlib import Path
import numpy as np
from bearing import PADERBORN_6203
from cheap_sensor import CheapSensor, simulate, windows
from s3_spectral import SpectralResidual, ResidualGenerator
import funnel as Fu

ROOT = Path(__file__).resolve().parent
CACHE = ROOT.parent / 'data' / 'paderborn' / 'cache'
UNIT_TO_G = 1 / 9.81
FR = 1500. / 60
ORDERS = PADERBORN_6203.orders()
HEALTHY = ('K001', 'K002', 'K003', 'K004', 'K005', 'K006')
INNER_REAL = ('KI04', 'KI14', 'KI16', 'KI17', 'KI18', 'KI21')
OUTER_REAL = ('KA04', 'KA15', 'KA16', 'KA22', 'KA30')
INNER_ART = ('KI01', 'KI03', 'KI05', 'KI07', 'KI08')
OUTER_ART = ('KA01', 'KA03', 'KA05', 'KA06', 'KA07', 'KA08', 'KA09')
REAL = INNER_REAL + OUTER_REAL
SENSORS = {'1k': CheapSensor(), '2k': CheapSensor(fs_out=8000, bw_hz=2000.), '6k': CheapSensor(fs_out=16000, bw_hz=6000.)}
STRENGTH, NMAX = .5, 90


def label_of(code):
    return 0 if code.startswith('K0') else 1 if code.startswith('KI') else 2


@lru_cache(maxsize=None)
def item(code, sensor='1k'):
    sen = SENSORS[sensor]; fs = sen.fs_out
    a = np.load(CACHE / f'{code}.npz')
    rng = np.random.default_rng([int.from_bytes(code.encode(), 'big') % 2**31, 7])
    w = np.stack([windows(simulate(v.astype(float) * UNIT_TO_G, 64000, sen, rng), fs)[:4] for v in a['vib']])  # (20, 4, fs)
    f = lambda x: Fu.feats(x[:, None, :], fs, FR, ORDERS, sen.bw_hz)
    first, later, allw = w[:10, 0], w[10:].reshape(-1, fs), w.reshape(-1, fs)
    return dict(code=code, label=label_of(code), fr=FR, fs=fs, donor_w=first, donor=f(first), base=f(first),
                hold=f(later), test=f(allw), rms=float(np.sqrt(np.mean(first ** 2))))


@lru_cache(maxsize=None)
def rig_rms(sensor='1k'):
    return float(np.mean([item(h, sensor)['rms'] for h in HEALTHY]))


def healthy_for(target, seed):
    return HEALTHY[(sorted(REAL + INNER_ART + OUTER_ART).index(target) + seed) % len(HEALTHY)]


def pick(pool, target, seed, label, m):
    pool = sorted(c for c in pool if c != target)
    return [str(x) for x in np.random.default_rng([seed, label, 20261112]).permutation(pool)[:m]]


def generate(donors, seed, offsets, sensor='1k'):
    """S3 flow trained on the donors' windows only; returns per offset {class: NMAX feature rows}."""
    its = [item(n, sensor) for n in donors]
    counts = Counter(i['label'] for i in its)
    k = [len(i['donor_w']) for i in its]
    waves = np.concatenate([i['donor_w'] for i in its])
    groups = np.repeat(np.arange(len(its)), k)
    lab = np.repeat([i['label'] for i in its], k)
    peak = np.repeat([np.abs(i['donor_w']).max() for i in its], k)
    onehot = {1: 0, 2: 1, 4: 2}
    cond = np.concatenate([[np.r_[np.eye(3)[onehot[i['label']]], i['fr'], np.log(rig_rms(sensor))]] * n for i, n in zip(its, k)])
    wts = np.repeat([1 / counts[i['label']] for i in its], k)
    codec = SpectralResidual().fit(waves, groups, cond)
    gen = ResidualGenerator('flow', seed).fit(codec.z, codec.conditions[codec.pairs[:, 0]], wts[codec.pairs[:, 0]])
    rng = np.random.default_rng([seed, 20261112, len(donors)])
    anchors = {c: np.resize(rng.permutation(np.flatnonzero(lab == c)), NMAX) for c in sorted(counts)}
    idx = np.concatenate([anchors[c] for c in sorted(counts)])
    out = []
    for o in offsets:
        res = gen.sample(codec.conditions[idx], seed + o) * codec.scale
        g, _ = codec.apply(waves[idx], res, STRENGTH, peak[idx])
        f = Fu.feats(g[:, None, :], its[0]['fs'], FR, ORDERS, SENSORS[sensor].bw_hz)
        out.append({c: f[i * NMAX:(i + 1) * NMAX] for i, c in enumerate(sorted(counts))})
    return out


def bootstrap(A, B, labels, rng, n=5000, classes=(1, 2)):
    """Paired class-stratified bearing bootstrap of macro(A) - macro(B). A, B: {bearing: score}."""
    groups = {c: [k for k in A if labels[k] == c] for c in classes}
    f = lambda ks: np.mean([np.mean([A[k] - B[k] for k in ks if labels[k] == c]) for c in classes])
    pt = f(list(A))
    bs = [f([x for g in groups.values() for x in [g[i] for i in rng.integers(len(g), size=len(g))]]) for _ in range(n)]
    return dict(delta=float(pt), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])


def macro(per, labels, classes=(1, 2)):
    return float(np.mean([np.mean([v for k, v in per.items() if labels[k] == c]) for c in classes]))
