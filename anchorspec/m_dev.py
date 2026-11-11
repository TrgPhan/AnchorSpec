"""M-Dev (PROTOCOL_M_DEV.md): physics injection + real events, and other classifiers, on the development sets.
    python m_dev.py --workers 12
    python m_dev.py --report
"""
import os
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
import json
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path
import numpy as np
from scipy.special import softmax
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from invariant_classifier import canonicalize
from u_natural import LABEL as XLABEL, ORDERS as XORDERS, bearing, training
from cheap_sensor import CheapSensor
from event_experts import causal_average
from diagnostic_experts import fault_labels
import funnel as Fu
import s3_dose as D
import s3_uored as UO

OUT = Path(__file__).resolve().parent / 'results' / 'm_dev'
SENSOR = CheapSensor()
CLASSES = (1, 2, 4)
TREE = dict(max_depth=8, min_samples_leaf=1, min_weight_fraction_leaf=.01, max_features='sqrt', bootstrap=False, n_jobs=1)
ARMS = ('real', 'flow_mix_0.25_30', 'inj_mix_0.25', 'inj_mix_0.5', 'inj_only', 'et500', 'hgb', 'lr', 'svm1',
        'et500+inj_mix_0.25', 'et500+inj_mix_0.5', 'lr+inj_mix_0.25', 'lr+inj_mix_0.5')
CLASSIFIER_ONLY = ('et500', 'hgb', 'lr', 'svm1')


class Model:
    """Same canonicalization and weighted scaling as InvariantClassifier; five-column scores."""

    def __init__(self, kind, seed):
        self.kind, self.seed = kind, seed

    def fit(self, x, y, w):
        x, y, w = canonicalize(x, y, w)
        self.classes_ = np.unique(y)
        self.scaler_ = StandardScaler().fit(x, sample_weight=w)
        z = self.scaler_.transform(x)
        k = self.kind
        if k == 'rf500':
            m = RandomForestClassifier(n_estimators=500, random_state=self.seed, **TREE)
        elif k == 'et500':
            m = ExtraTreesClassifier(n_estimators=500, random_state=self.seed, **TREE)
        elif k == 'hgb':
            m = HistGradientBoostingClassifier(max_iter=200, learning_rate=.1, max_depth=3, min_samples_leaf=5, random_state=self.seed)
        elif k == 'lr':
            m = LogisticRegression(C=1., max_iter=5000)
        elif k == 'svm1':
            m = SVC(C=1, gamma=1 / x.shape[1], decision_function_shape='ovr')
        self.model_ = m.fit(z, y, sample_weight=w)
        return self

    def predict_proba(self, x):
        z = self.scaler_.transform(x)
        if self.kind == 'svm1':
            s = self.model_.decision_function(z)
            if len(self.classes_) == 2:
                s = np.column_stack((-s, s))
            p = softmax(s, axis=1)
        else:
            p = self.model_.predict_proba(z)
        out = np.zeros((len(z), 5)); out[:, self.classes_] = p
        return out


@lru_cache(maxsize=None)
def healthy_waves(ds, n):
    if ds == 'xjtu':
        b = bearing(n)
        return b['healthy'][:5][:, None, :], float(b['fr']), XORDERS
    UO.U.ALLOW_FAULT['on'] = True
    base, hold, fr = UO.U.machine(int(n), UO.SEN)
    return base, float(fr), UO.U.ORDERS


def injected_pool(ds, target, seed, n=150):
    base, fr, orders = healthy_waves(ds, target)
    rng = np.random.default_rng([seed, sum(map(ord, str(target))), 31])
    return {c: Fu.feats(Fu.injected(base, kind, n, fr, orders, SENSOR, 4000, rng), 4000, fr, orders) for c, kind in ((1, 'inner'), (2, 'outer'))}


def mix(base, rows, beta):
    """Synthetic rows take share beta of their class mass; class totals unchanged (classes without rows untouched)."""
    x, y, w = base
    C = len([c for c in np.unique(y) if c > 0])
    scale = len(x) / (1 + C)
    w2 = w.copy(); xs, ys, ws = [x], [y], [w2]
    for c, a in rows.items():
        if not (y == c).any():
            continue
        w2[y == c] *= (1 - beta)
        xs.append(a); ys.append(np.full(len(a), c, int)); ws.append(np.full(len(a), beta * scale / len(a)))
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(ws)


def inj_only(healthy, rows):
    xs = [healthy] + [rows[c] for c in sorted(rows)]
    ys = [np.zeros(len(healthy), int)] + [np.full(len(rows[c]), c, int) for c in sorted(rows)]
    ws = [np.full(len(a), 1 / len(a)) for a in xs]
    w = np.concatenate(ws); w *= len(w) / w.sum()
    return np.concatenate(xs), np.concatenate(ys), w


def predict(model, x):
    return fault_labels(causal_average(model.predict_proba(x))).tolist()


def job(task):
    ds, target, seed, profile = task
    start = time.perf_counter()
    t = D.item(ds, target)
    donors = D.donors_for(ds, target, seed, profile)
    counts = Counter(D.item(ds, n)['label'] for n in donors)
    events = [(n, D.item(ds, n)['label'], D.item(ds, n)['donor']) for n in donors]
    base = training(t['base'], events, {}, 'real')
    inj = injected_pool(ds, target, seed)
    ((flow, _),), _ = D.generate(ds, donors, seed, (20261106,), prop=False)
    data = {'real': base, 'flow_mix_0.25_30': D.flow_arms(base, counts, flow, None, ['flow_mix_0.25_30'])['flow_mix_0.25_30'],
            'inj_mix_0.25': mix(base, inj, .25), 'inj_mix_0.5': mix(base, inj, .5), 'inj_only': inj_only(t['base'], inj)}
    plan = {a: ('rf500', a) for a in data}
    plan.update({k: (k, 'real') for k in CLASSIFIER_ONLY})
    plan.update({f'{k}+{g}': (k, g) for k in ('et500', 'lr') for g in ('inj_mix_0.25', 'inj_mix_0.5')})
    scores = {}
    for arm, (kind, d) in plan.items():
        m = Model(kind, seed).fit(*data[d])
        scores[arm] = dict(test=predict(m, t['severe']), developing=predict(m, t['developing']))
    return dict(ds=ds, target=str(target), seed=seed, profile=profile, label=t['label'], donors=[str(d) for d in donors],
                scores=scores, elapsed_seconds=time.perf_counter() - start)


def path(task):
    ds, n, s, p = task
    return OUT / 'tasks' / f'{ds}_{p}_{n}_{s}.json'


def report():
    rows = [json.loads(p.read_text()) for p in sorted((OUT / 'tasks').glob('*.json'))]
    rng = np.random.default_rng(20261112)
    settings = [('uored', p) for p in D.PROFILES] + [('xjtu', 'natural')]
    res, gains = {}, {a: [] for a in ARMS if a != 'real'}
    for ds, p in settings:
        sub = [r for r in rows if r['ds'] == ds and r['profile'] == p]
        lab = {r['target']: r['label'] for r in sub}
        per = {a: {} for a in ARMS}
        for r in sub:
            for a in ARMS:
                per[a].setdefault(r['target'], []).append(float(np.mean(np.asarray(r['scores'][a]['test']) == r['label'])))
        per = {a: {n: float(np.mean(v)) for n, v in d.items()} for a, d in per.items()}
        mac = lambda d, cls=CLASSES: float(np.mean([np.mean([v for n, v in d.items() if lab[n] == c]) for c in cls]))
        key = f'{ds}:{p}'
        res[key] = {}
        for a in ARMS:
            entry = dict(macro=mac(per[a]), inner_outer=mac(per[a], (1, 2)), classes={c: float(np.mean([v for n, v in per[a].items() if lab[n] == c])) for c in CLASSES})
            if a != 'real':
                groups = {c: [n for n in lab if lab[n] == c] for c in CLASSES}
                f = lambda ns: np.mean([np.mean([per[a][n] - per['real'][n] for n in ns if lab[n] == c]) for c in CLASSES])
                bs = [f([x for g in groups.values() for x in [g[i] for i in rng.integers(len(g), size=len(g))]]) for _ in range(3000)]
                entry['vs_real'] = dict(delta=float(f(list(lab))), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
                gains[a].append(entry['vs_real']['delta'])
            res[key][a] = entry
    summary = {a: dict(mean=float(np.mean(g)), min=float(np.min(g)), eligible=bool(np.mean(g) >= .02 and np.min(g) >= -.02)) for a, g in gains.items()}
    eligible = sorted([a for a, s in summary.items() if s['eligible']], key=lambda a: -summary[a]['mean'])
    locked = eligible[:1]
    cls_eligible = [a for a in eligible if a in CLASSIFIER_ONLY]
    if cls_eligible and cls_eligible[0] not in locked:
        locked.append(cls_eligible[0])
    exploratory = None if locked else max(summary, key=lambda a: summary[a]['mean'])
    out = dict(protocol='PROTOCOL_M_DEV.md', results=res, summary=summary, locked=locked, exploratory_if_none=exploratory)
    (OUT / 'summary.json').write_text(json.dumps(out, indent=2))
    keys = list(res)
    L = ['# M-Dev: chênh so với real (RF 500 cây), chỉ chọn loại lỗi, macro 3 lớp', '',
         '| Nhánh | ' + ' | '.join(keys) + ' | TB | Thấp nhất | Đủ điều kiện |', '|---|' + '---:|' * (len(keys) + 3)]
    L.append('| real (macro) | ' + ' | '.join(f"{res[k]['real']['macro']*100:.1f}" for k in keys) + ' | | | |')
    for a in ARMS:
        if a == 'real':
            continue
        L.append(f'| {a} | ' + ' | '.join(f"{res[k][a]['vs_real']['delta']*100:+.1f}" for k in keys) +
                 f" | {summary[a]['mean']*100:+.2f} | {summary[a]['min']*100:+.1f} | {'CÓ' if summary[a]['eligible'] else ''} |")
    L += ['', f'**Khóa cho Paderborn:** {locked if locked else "không nhánh nào đủ điều kiện; thăm dò " + str(exploratory)}', '',
          '## Vòng trong và ngoài (macro 2 lớp, tham khảo)', '', '| Nhánh | ' + ' | '.join(keys) + ' |', '|---|' + '---:|' * len(keys)]
    for a in ARMS:
        L.append(f'| {a} | ' + ' | '.join(f"{res[k][a]['inner_outer']*100:.1f}" for k in keys) + ' |')
    (OUT / 'summary.md').write_text('\n'.join(L), encoding='utf-8'); print('\n'.join(L))


def main():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--workers', type=int, default=12); ap.add_argument('--report', action='store_true')
    ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    (OUT / 'tasks').mkdir(parents=True, exist_ok=True)
    tasks = [('uored', n, s, p) for p in D.PROFILES for n in D.UNAMES for s in D.SEEDS] + [('xjtu', n, s, 'natural') for n in XLABEL for s in D.SEEDS]
    if a.smoke:
        for t in (('uored', 1, 11, '2-2-2'), ('xjtu', '2_1', 11, 'natural')):
            r = job(t); print(t, len(r['scores']), 'arms', round(r['elapsed_seconds'], 1), 's')
        return
    if not a.report:
        todo = [t for t in tasks if not path(t).exists()]
        with ProcessPoolExecutor(a.workers) as pool:
            for i, (t, row) in enumerate(zip(todo, pool.map(job, todo)), 1):
                path(t).write_text(json.dumps(row))
                print('mdev', i, '/', len(todo), t, round(row['elapsed_seconds'], 1), 's', flush=True)
    report()


if __name__ == '__main__':
    main()
