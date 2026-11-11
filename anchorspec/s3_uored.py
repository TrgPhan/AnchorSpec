"""S3-UORED (PROTOCOL_S3_UORED_EVENTS.md): event-budget curve on UORED, real vs S3 flow augmentation."""
import os
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
import json, time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path
import numpy as np
from s3_spectral import SpectralResidual, ResidualGenerator
from u_natural import training
from invariant_classifier import InvariantClassifier
from event_experts import causal_average
from t_readiness import selective
import funnel as Fu
import e8_uored as U

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results/s3_uored'
SEEDS = (11, 29, 47)
BUDGETS = (1, 2, 4)
OFFSETS = (20261111, 20261106, 1, 2, 3)
SYN, STRENGTH, ALPHA = 10, .5, .25
CODE = {'inner': 1, 'outer': 2, 'ball': 3, 'cage': 4}
NAMES = sorted(U.LAB)
SEN = U.SENSORS['1k']


@lru_cache(maxsize=None)
def item(i):
    U.ALLOW_FAULT['on'] = True
    base, hold, fr = U.machine(i, SEN)
    severe = U.windows50(U.sensed(i, 2, SEN), 4000)
    developing = U.windows50(U.sensed(i, 1, SEN), 4000)
    f = lambda w: Fu.feats(w, 4000, fr, U.ORDERS)
    donor = severe[::2][:10]
    return dict(fr=float(fr), label=CODE[U.LAB[i]], base=f(base), hold=f(hold), severe=f(severe), developing=f(developing),
                donor_w=donor[:, 0, :], donor=f(donor), rms=float(np.sqrt(np.mean(base[:, 0, :] ** 2))))


def chosen(target, seed, m):
    order = [int(n) for n in np.random.default_rng(seed).permutation(NAMES) if int(n) != target]
    return [n for c in (1, 2, 3, 4) for n in [k for k in order if CODE[U.LAB[k]] == c][:m]]


def predict(model, t, off):
    return {st: selective(causal_average(model.predict_proba(t[st] - off)), 0).tolist() for st in ('hold', 'severe', 'developing')}


def job(task):
    target, seed, m = task; start = time.perf_counter()
    t = item(target); donors = chosen(target, seed, m); counts = Counter(item(n)['label'] for n in donors)
    off = lambda n, rep: item(n)['base'].mean(0) if rep == 'delta' else 0.
    row = dict(target=target, seed=seed, budget=m, label=t['label'], donors=donors, scores={})
    base = {}
    for rep in ('raw', 'delta'):
        events = [(n, item(n)['label'], item(n)['donor'] - off(n, rep)) for n in donors]
        x, y, w = training(t['base'] - off(target, rep), events, {}, 'real'); base[rep] = (x, y, w)
        row['scores'][f'real_{rep}'] = predict(InvariantClassifier('rf', seed).fit(x, y, w), t, off(target, rep))
    waves = np.concatenate([item(n)['donor_w'] for n in donors]); groups = np.repeat(np.arange(len(donors)), 10)
    cond = np.concatenate([[np.r_[np.eye(4)[item(n)['label'] - 1], item(n)['fr'], np.log(item(n)['rms'])]] * 10 for n in donors])
    wts = np.concatenate([[1 / counts[item(n)['label']]] * 10 for n in donors])
    codec = SpectralResidual().fit(waves, groups, cond)
    gen = ResidualGenerator('flow', seed).fit(codec.z, codec.conditions[codec.pairs[:, 0]], wts[codec.pairs[:, 0]])
    anchor = np.arange(len(waves)); peak = np.repeat([np.abs(item(n)['donor_w']).max() for n in donors], 10)
    for o in OFFSETS:
        generated, _ = codec.apply(waves[anchor], gen.sample(codec.conditions[anchor], seed + o) * codec.scale, STRENGTH, peak)
        feats = {n: Fu.feats(generated[g * 10:(g + 1) * 10, None, :], 4000, item(n)['fr'], U.ORDERS) for g, n in enumerate(donors)}
        for rep in ('raw', 'delta'):
            x, y, w = base[rep]; xs, ys, ws = [x], [y], [w]; scale = len(x) / (1 + len(counts))
            for n in donors:
                xs.append(feats[n] - off(n, rep)); ys.append(np.full(SYN, item(n)['label'], int))
                ws.append(np.full(SYN, ALPHA * scale / (counts[item(n)['label']] * SYN)))
            mdl = InvariantClassifier('rf', seed).fit(np.concatenate(xs), np.concatenate(ys), np.concatenate(ws))
            row['scores'][f'flow_{rep}@{o}'] = predict(mdl, t, off(target, rep))
    row['generator'] = dict(pairs=int(len(codec.pairs)), training_seconds=gen.training_seconds)
    row['elapsed_seconds'] = time.perf_counter() - start
    return row


def per_bearing(rows, method, stage):
    keys = [method] if '@' in method or method.startswith('real') else [f'{method}@{o}' for o in OFFSETS]
    out = {}
    for r in rows:
        vals = [np.mean(np.asarray(r['scores'][k][stage]) == r['label']) for k in keys]
        out.setdefault(r['target'], []).append(np.mean(vals))
    return {n: float(np.mean(v)) for n, v in out.items()}


def macro(b):
    return float(np.mean([np.mean([v for n, v in b.items() if CODE[U.LAB[n]] == c]) for c in (1, 2, 3, 4)]))


def summary():
    rows = [json.loads(p.read_text())['row'] for p in sorted((OUT / 'tasks').glob('*.json'))]
    rng = np.random.default_rng(20261111); groups = {c: [n for n in U.LAB if CODE[U.LAB[n]] == c] for c in (1, 2, 3, 4)}
    res = {}; L = ['# S3-UORED: số sự cố lỗi thật mỗi loại, có và không có Flow (Flow trung bình 5 hạt giống)', '',
                   '| Sự cố/loại | Nhánh | Nặng, macro 4 lớp | Trong / Ngoài / Bi / Cách | Đang phát triển | Gán lỗi trên khỏe | Khoảng theo hạt giống (nặng) |',
                   '|---:|---|---:|---|---:|---:|---|']
    for m in BUDGETS:
        sub = [r for r in rows if r['budget'] == m]
        if len(sub) != 60: continue
        res[m] = {}
        for meth in ('real_raw', 'flow_raw', 'real_delta', 'flow_delta'):
            b = per_bearing(sub, meth, 'severe'); cls = {c: np.mean([b[n] for n in groups[c]]) for c in groups}
            dev = macro(per_bearing(sub, meth, 'developing'))
            keys = [meth] if meth.startswith('real') else [f'{meth}@{o}' for o in OFFSETS]
            hf = float(np.mean([np.mean(np.asarray(r['scores'][k]['hold']) > 0) for r in sub for k in keys]))
            spread = [macro(per_bearing(sub, k, 'severe')) for k in keys]
            res[m][meth] = dict(severe=macro(b), classes=cls, developing=dev, healthy_fault=hf, lo=min(spread), hi=max(spread), bearing=b)
            L.append(f"| {m} | {meth} | {macro(b)*100:.1f} | {' / '.join(f'{cls[c]*100:.0f}' for c in (1,2,3,4))} | {dev*100:.1f} | {hf*100:.1f} | {min(spread)*100:.1f}–{max(spread)*100:.1f} |")
    L += ['', '| Sự cố/loại | So sánh (nặng) | Chênh | CI 95% |', '|---:|---|---:|---|']
    comps = {}
    for m in res:
        for a, bname in (('flow_raw', 'real_raw'), ('flow_delta', 'real_delta'), ('real_delta', 'real_raw'), ('flow_delta', 'real_raw')):
            A, B = res[m][a]['bearing'], res[m][bname]['bearing']
            f = lambda ns: np.mean([np.mean([A[n] - B[n] for n in ns if CODE[U.LAB[n]] == c]) for c in (1, 2, 3, 4)])
            bs = [f([x for g in groups.values() for x in rng.choice(g, len(g))]) for _ in range(5000)]
            comps[f'{m}:{a}-{bname}'] = dict(delta=float(f(list(U.LAB))), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
            v = comps[f'{m}:{a}-{bname}']; L.append(f"| {m} | {a} − {bname} | {v['delta']*100:+.1f} | [{v['ci95'][0]*100:+.1f}; {v['ci95'][1]*100:+.1f}] |")
    gate = {m: (comps[f'{m}:flow_raw-real_raw']['delta'] >= .05 and comps[f'{m}:flow_raw-real_raw']['ci95'][0] > 0
                and res[m]['flow_raw']['healthy_fault'] - res[m]['real_raw']['healthy_fault'] <= .02) for m in (1, 2) if m in res}
    L += ['', f'Tiêu chí khai báo trước (m = 1 hoặc 2, raw): {"ĐẠT" if any(gate.values()) else "KHÔNG ĐẠT"} {gate}']
    for m in res:
        for meth in res[m]: res[m][meth].pop('bearing')
    (OUT / 'summary.json').write_text(json.dumps(dict(protocol='PROTOCOL_S3_UORED_EVENTS.md', results=res, comparisons=comps, gate=gate, confirmatory=False), indent=2))
    (OUT / 'summary.md').write_text('\n'.join(L), encoding='utf-8'); print('\n'.join(L))


def main():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--workers', type=int, default=6); ap.add_argument('--report', action='store_true'); a = ap.parse_args()
    (OUT / 'tasks').mkdir(parents=True, exist_ok=True)
    if not a.report:
        todo = [(t, s, m) for m in BUDGETS for t in NAMES for s in SEEDS if not (OUT / 'tasks' / f'{t}_{s}_m{m}.json').exists()]
        with ProcessPoolExecutor(a.workers) as pool:
            for i, (task, row) in enumerate(zip(todo, pool.map(job, todo)), 1):
                (OUT / 'tasks' / f'{task[0]}_{task[1]}_m{task[2]}.json').write_text(json.dumps(dict(row=row)))
                print('uored', i, '/', len(todo), task, round(row['elapsed_seconds'], 1), 's', flush=True)
    summary()


if __name__ == '__main__': main()
