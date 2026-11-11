"""S3-Delta (PROTOCOL_S3_DELTA.md): Flow residual augmentation combined with healthy-baseline delta features."""
import os
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
import json, time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from s3_spectral import SpectralResidual, ResidualGenerator
from u_natural import LABEL, ORDERS, bearing, training
from invariant_classifier import InvariantClassifier
from event_experts import causal_average
from t_readiness import selective
import funnel as Fu
import s3_curve as C

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results/s3_delta'
SEEDS = (11, 29, 47)
OFFSETS = (20261111, 20261106, 1, 2, 3)
SYN, STRENGTH, ALPHA = 10, .5, .25
REPS = ('raw', 'delta')


def predict(model, t, off):
    return {st: selective(causal_average(model.predict_proba((t[st + '_features'][5:] if st == 'healthy' else t[st + '_features']) - off)), 0).tolist()
            for st in ('healthy', 'terminal')}


def job(task):
    target, seed = task; start = time.perf_counter()
    t = bearing(target); donors = [n for n in LABEL if n != target]; counts = Counter(LABEL[n] for n in donors)
    mu = {n: bearing(n)['healthy_features'][:5].mean(0) for n in LABEL}
    off = lambda n, rep: mu[n] if rep == 'delta' else 0.
    row = dict(target=target, seed=seed, label=LABEL[target], scores={})
    base = {}
    for rep in REPS:
        events = [(n, LABEL[n], bearing(n)['terminal_features'] - off(n, rep)) for n in donors]
        x, y, w = training(t['healthy_features'][:5] - off(target, rep), events, {}, 'real'); base[rep] = (x, y, w)
        row['scores'][f'real_{rep}'] = predict(InvariantClassifier('rf', seed).fit(x, y, w), t, off(target, rep))
    waves, cond, wts, groups, limits = [], [], [], [], []
    for g, n in enumerate(donors):
        s = bearing(n); sel = s['terminal']
        c = np.r_[np.eye(3)[{1: 0, 2: 1, 4: 2}[LABEL[n]]], float(s['fr']), np.log(np.sqrt(np.mean(s['healthy'][:5] ** 2)))]
        waves.append(sel); cond.extend([c] * 10); wts.extend([1 / counts[LABEL[n]]] * 10); groups.extend([g] * 10); limits.append(np.abs(sel).max())
    waves = np.concatenate(waves)
    codec = SpectralResidual().fit(waves, np.asarray(groups), np.asarray(cond))
    gen = ResidualGenerator('flow', seed).fit(codec.z, codec.conditions[codec.pairs[:, 0]], np.asarray(wts)[codec.pairs[:, 0]])
    anchor = np.concatenate([g * 10 + np.arange(SYN) for g in range(len(donors))])
    peak = np.repeat(np.asarray(limits), SYN)
    for o in OFFSETS:
        res = gen.sample(codec.conditions[anchor], seed + o) * codec.scale
        generated, _ = codec.apply(waves[anchor], res, STRENGTH, peak)
        feats = {n: Fu.feats(generated[g * SYN:(g + 1) * SYN, None, :], 4000, float(bearing(n)['fr']), ORDERS) for g, n in enumerate(donors)}
        for rep in REPS:
            x, y, w = base[rep]; xs, ys, ws = [x], [y], [w]; scale = len(x) / (1 + len(counts))
            for n in donors:
                xs.append(feats[n] - off(n, rep)); ys.append(np.full(SYN, LABEL[n], int))
                ws.append(np.full(SYN, ALPHA * scale / (counts[LABEL[n]] * SYN)))
            m = InvariantClassifier('rf', seed).fit(np.concatenate(xs), np.concatenate(ys), np.concatenate(ws))
            row['scores'][f'flow_{rep}@{o}'] = predict(m, t, off(target, rep))
    row['elapsed_seconds'] = time.perf_counter() - start
    return row


def terminal(rows, method):
    """Macro recall of 3 fault classes at terminal stage: seed mean per bearing, then class mean (as 77.22%)."""
    per = {}
    for r in rows:
        p = np.asarray(r['scores'][method]['terminal']); per.setdefault((r['target'], r['label']), []).append(float((p == r['label']).mean()))
    b = {k: np.mean(v) for k, v in per.items()}
    cls = {c: np.mean([v for (n, l), v in b.items() if l == c]) for c in (1, 2, 4)}
    hf = np.mean([np.mean(np.asarray(r['scores'][method]['healthy']) > 0) for r in rows])
    return float(np.mean(list(cls.values()))), cls, float(hf), b


def methods_of(rows):
    keys = sorted(rows[0]['scores']); return [k for k in keys if '@' not in k], sorted({k.split('@')[0] for k in keys if '@' in k})


def summary():
    rows = [json.loads(p.read_text())['row'] for p in sorted((OUT / 'tasks').glob('*.json'))]
    assert len(rows) == 39, len(rows)
    lab = {r['target']: r['label'] for r in rows}
    reals, flows = methods_of(rows)
    table = {}
    def stats(method_keys):
        mac, cage, hf, c4 = [], [], [], []
        for k in method_keys:
            m, cls, h, _ = terminal(rows, k); mt = C.metrics(rows, k)
            mac.append(m); cage.append(cls[4]); hf.append(h); c4.append((mt['avg_precision'], mt['avg_recall'], mt['accuracy']))
        return dict(terminal_macro=float(np.mean(mac)), terminal_min=float(np.min(mac)), terminal_max=float(np.max(mac)),
                    cage=float(np.mean(cage)), healthy_fault=float(np.mean(hf)), p4=float(np.mean([c[0] for c in c4])),
                    r4=float(np.mean([c[1] for c in c4])), acc4=float(np.mean([c[2] for c in c4])))
    for k in reals: table[k] = stats([k])
    for f in flows: table[f] = stats([f'{f}@{o}' for o in OFFSETS])
    # paired bootstrap on terminal macro, flow averaged over offsets at bearing level
    def bearing_scores(name):
        keys = [name] if name in reals else [f'{name}@{o}' for o in OFFSETS]
        return {n: np.mean([terminal(rows, k)[3][(n, lab[n])] for k in keys]) for n in lab}
    rng = np.random.default_rng(20261111); groups = {c: [n for n in lab if lab[n] == c] for c in (1, 2, 4)}
    def delta(a, b):
        A, B = bearing_scores(a), bearing_scores(b)
        f = lambda ns: np.mean([np.mean([A[n] - B[n] for n in ns if lab[n] == c]) for c in (1, 2, 4)])
        pt = f(list(lab)); bs = [f([x for g in groups.values() for x in rng.choice(g, len(g))]) for _ in range(5000)]
        return dict(delta=float(pt), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
    comps = {f'{a} - {b}': delta(a, b) for a, b in (('flow_delta', 'real_raw'), ('flow_delta', 'real_delta'), ('real_delta', 'real_raw'),
                                                     ('flow_raw', 'real_raw'), ('flow_delta', 'flow_raw'))}
    out = dict(protocol='PROTOCOL_S3_DELTA.md', table=table, comparisons=comps, offsets=OFFSETS, confirmatory=False, independent_bearings=13)
    (OUT / 'summary.json').write_text(json.dumps(out, indent=2))
    names = {'real_raw': 'Chỉ mẫu thật, raw', 'flow_raw': 'Flow, raw', 'real_delta': 'Chỉ mẫu thật, delta', 'flow_delta': 'Flow + delta'}
    L = ['# S3-Delta: kết quả (XJTU 13 ổ, 3 seed; Flow trung bình 5 hạt giống lấy mẫu)', '',
         '| Nhánh | Macro recall cuối đời | Khoảng theo hạt giống | Vòng cách | Gán lỗi trên khỏe | P / R / Acc 4 lớp |', '|---|---:|---|---:|---:|---|']
    for k in ('real_raw', 'flow_raw', 'real_delta', 'flow_delta'):
        s = table[k]
        L.append(f"| {names[k]} | {s['terminal_macro']*100:.2f} | {s['terminal_min']*100:.2f}–{s['terminal_max']*100:.2f} | {s['cage']*100:.2f} | {s['healthy_fault']*100:.2f} | "
                 f"{s['p4']*100:.1f} / {s['r4']*100:.1f} / {s['acc4']*100:.1f} |")
    L += ['', '| So sánh (macro recall cuối đời) | Chênh | CI 95% |', '|---|---:|---|']
    for k, v in comps.items(): L.append(f"| {k} | {v['delta']*100:+.2f} | [{v['ci95'][0]*100:+.2f}; {v['ci95'][1]*100:+.2f}] |")
    (OUT / 'summary.md').write_text('\n'.join(L), encoding='utf-8'); print('\n'.join(L))


def main():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--workers', type=int, default=6); ap.add_argument('--report', action='store_true'); a = ap.parse_args()
    (OUT / 'tasks').mkdir(parents=True, exist_ok=True)
    if not a.report:
        todo = [(t, s) for t in LABEL for s in SEEDS if not (OUT / 'tasks' / f'{t}_{s}.json').exists()]
        with ProcessPoolExecutor(a.workers) as pool:
            for i, (task, row) in enumerate(zip(todo, pool.map(job, todo)), 1):
                (OUT / 'tasks' / f'{task[0]}_{task[1]}.json').write_text(json.dumps(dict(row=row)))
                print('delta', i, '/', len(todo), task, round(row['elapsed_seconds'], 1), 's', flush=True)
    summary()


if __name__ == '__main__': main()
