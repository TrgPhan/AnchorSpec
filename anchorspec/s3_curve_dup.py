"""Post-hoc (12/11): add the duplicate control to the S3 data-efficiency curve.
dup = real + exact copies of the same anchor windows Flow used (10 per donor, cyclic over the k kept windows),
with the same weight as the Flow rows. Real and Flow predictions are read from results/s3_curve (RF 50) and
results/s3_curve_rf500 (RF 500). Output: results/s3_curve_dup/."""
import os
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from sklearn.ensemble import RandomForestClassifier as _RFC
import invariant_classifier as IC
import s3_curve as C

OUT = C.ROOT / 'results/s3_curve_dup'
SRC = {50: C.ROOT / 'results/s3_curve', 500: C.ROOT / 'results/s3_curve_rf500'}


def job(task):
    target, seed, k, trees = task
    IC.RandomForestClassifier = lambda **kw: _RFC(**{**kw, 'n_estimators': trees})
    t = C.bearing(target); donors = [n for n in C.LABEL if n != target]
    subsets = {n: C.kept(seed, n, k) for n in donors}
    events = [(n, C.LABEL[n], C.bearing(n)['terminal_features'][subsets[n]]) for n in donors]
    x, y, w = C.training(t['healthy_features'][:5], events, {}, 'real')
    counts = Counter(C.LABEL[n] for n in donors); scale = len(x) / (1 + len(counts))
    xs, ys, ws = [x], [y], [w]
    for n, c, f in events:
        d = f[np.arange(C.SYNTH_PER_DONOR) % k]
        xs.append(d); ys.append(np.full(len(d), c, int)); ws.append(np.full(len(d), C.ALPHA * scale / (counts[c] * C.SYNTH_PER_DONOR)))
    return C.predict(IC.InvariantClassifier('rf', seed).fit(np.concatenate(xs), np.concatenate(ys), np.concatenate(ws)), t)


def boot(rows, a, b, metric, rng, n=2000):
    tg = sorted({r['target'] for r in rows}); groups = {c: [x for x in tg if C.LABEL[x] == c] for c in (1, 2, 4)}
    by = {x: [r for r in rows if r['target'] == x] for x in tg}; out = []
    for _ in range(n):
        sub = [r for g in groups.values() for i in rng.integers(len(g), size=len(g)) for r in by[g[i]]]
        out.append(C.metrics(sub, a)[metric] - C.metrics(sub, b)[metric])
    d = C.metrics(rows, a)[metric] - C.metrics(rows, b)[metric]
    return d, np.percentile(out, 2.5), np.percentile(out, 97.5)


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    tasks = [(t, s, k, n) for n in (50, 500) for k in C.BUDGETS for t in C.LABEL for s in C.SEEDS]
    with ProcessPoolExecutor(14) as pool:
        dup = dict(zip(tasks, pool.map(job, tasks)))
    rng = np.random.default_rng(20261112); L = ['# Đường cong S3 có thêm đối chứng bản sao (hậu nghiệm, 12/11)', '',
        'Thật + bản sao: chép đúng các cửa sổ thật mà Flow dùng làm neo, cùng số dòng (10 mỗi ổ), cùng trọng số với mẫu Flow.', '',
        'Chấm như s3_curve: cửa sổ khỏe + cửa sổ cuối đời, 4 lớp, có lựa chọn khỏe. Ô: Avg Precision / Avg Recall / Accuracy.', '']
    for n in (50, 500):
        rows = []
        for k in C.BUDGETS:
            for t in C.LABEL:
                for s in C.SEEDS:
                    r = json.loads((SRC[n] / 'tasks' / f'{t}_{s}_k{k}.json').read_text())['row']; r['scores']['dup'] = dup[(t, s, k, n)]; rows.append(r)
        L += [f'## RF {n} cây', '', '| Cửa sổ thật/ổ | Chỉ thật | Thật + bản sao | Thật + Flow | Flow − thật (Recall, CI 95%) | Flow − bản sao (Recall, CI 95%) | Flow − bản sao (Precision, CI 95%) |', '|---:|---|---|---|---|---|---|']
        for k in C.BUDGETS:
            sub = [r for r in rows if r['budget'] == k]; m = {a: C.metrics(sub, a) for a in ('real', 'dup', 'flow')}
            cell = lambda a: f"{m[a]['avg_precision']*100:.1f} / {m[a]['avg_recall']*100:.1f} / {m[a]['accuracy']*100:.1f}"
            f = lambda tup: f'{tup[0]*100:+.1f} [{tup[1]*100:+.1f}; {tup[2]*100:+.1f}]'
            L.append(f"| {k} | {cell('real')} | {cell('dup')} | {cell('flow')} | {f(boot(sub, 'flow', 'real', 'avg_recall', rng))} | {f(boot(sub, 'flow', 'dup', 'avg_recall', rng))} | {f(boot(sub, 'flow', 'dup', 'avg_precision', rng))} |")
        L.append('')
        json.dump(rows, open(OUT / f'rows_rf{n}.json', 'w'))
    (OUT / 'summary.md').write_text('\n'.join(L), encoding='utf-8'); print('\n'.join(L))
