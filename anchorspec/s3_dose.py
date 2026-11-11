"""S3-Dose (PROTOCOL_S3_DOSE.md): how much S3 flow data to generate per fault class when real events are imbalanced.

UORED 15 bearings (inner, outer, cage) under five event inventories, plus XJTU natural inventory.
Arms vary number of generated rows per class, synthetic weight (added on top or mixed at constant class mass),
duplicate controls, unweighted count-based training, and a nested installation-time dose selector that uses
only the machine's own confirmed events. Run from anchorspec/:
    python s3_dose.py --workers 12
    python s3_dose.py --report
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
from s3_spectral import SpectralResidual, ResidualGenerator
from u_natural import LABEL as XLABEL, ORDERS as XORDERS, bearing, training
from invariant_classifier import InvariantClassifier
from event_experts import causal_average
from t_readiness import selective
import funnel as Fu
import s3_uored as UO

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results/s3_dose'
SEEDS = (11, 29, 47)
OFFSETS = (20261106, 1, 2)
NS = (10, 30, 90)
NMAX = max(NS)
STRENGTH = .5
CLASSES = (1, 2, 4)                       # inner, outer, cage
CNAME = {1: 'Vòng trong', 2: 'Vòng ngoài', 4: 'Vòng cách'}
PROFILES = {'5-2-1': {1: 5, 4: 2, 2: 1}, '1-2-5': {1: 1, 4: 2, 2: 5}, '2-2-2': {1: 2, 4: 2, 2: 2},
            '1-1-1': {1: 1, 4: 1, 2: 1}, '4-4-4': {1: 4, 4: 4, 2: 4}}
UNAMES = [n for n in UO.NAMES if UO.CODE[UO.U.LAB[n]] in CLASSES]
FIXED = ('real', 'dup_add_0.25', 'dup_add_1', 'uw_real')
FLOW = tuple(f'flow_add_{a}_{n}' for a in ('0.25', '1') for n in NS) + tuple(f'flow_mix_{b}_{n}' for b in ('0.25', '0.5') for n in NS) \
    + ('flow_prop', 'uw_topup')
CANDIDATES = ('real', 'dup_add_0.25', 'flow_add_0.25_10', 'flow_add_0.25_30', 'flow_add_0.25_90',
              'flow_mix_0.5_10', 'flow_mix_0.5_30', 'flow_mix_0.5_90')
STAGES = ('hold', 'severe', 'developing')


@lru_cache(maxsize=None)
def item(ds, n):
    if ds == 'uored':
        it = UO.item(int(n))
        return dict(it, orders=UO.U.ORDERS)
    b = bearing(n)
    return dict(fr=float(b['fr']), label=XLABEL[n], base=b['healthy_features'][:5], hold=b['healthy_features'][5:],
                severe=b['terminal_features'], developing=b['preterminal_features'], donor=b['terminal_features'],
                donor_w=b['terminal'], rms=float(np.sqrt(np.mean(b['healthy'][:5] ** 2))), orders=XORDERS)


def donors_for(ds, target, seed, profile):
    if ds == 'xjtu':
        return [n for n in XLABEL if n != target]
    out = []
    for c in (1, 4, 2):
        pool = sorted(n for n in UNAMES if UO.CODE[UO.U.LAB[n]] == c and n != target)
        perm = np.random.default_rng([seed, c, 20261112]).permutation(pool)
        out += [int(x) for x in perm[:PROFILES[profile][c]]]
    return out


def feats_rows(waves, frs, orders):
    out = None
    for f in np.unique(frs):
        m = frs == f
        v = Fu.feats(waves[m][:, None, :], 4000, float(f), orders)
        if out is None:
            out = np.zeros((len(waves), v.shape[1]))
        out[m] = v
    return out


def generate(ds, donors, seed, offsets, prop=True):
    """Train one S3 flow on the donors' windows; return per offset {class: NMAX rows}, and per-event prop rows."""
    its = [item(ds, n) for n in donors]
    counts = Counter(i['label'] for i in its)
    k = [len(i['donor_w']) for i in its]
    waves = np.concatenate([i['donor_w'] for i in its])
    groups = np.repeat(np.arange(len(its)), k)
    lab = np.repeat([i['label'] for i in its], k)
    fr = np.repeat([i['fr'] for i in its], k)
    peak = np.repeat([np.abs(i['donor_w']).max() for i in its], k)
    onehot = {1: 0, 2: 1, 4: 2}
    cond = np.concatenate([[np.r_[np.eye(3)[onehot[i['label']]], i['fr'], np.log(i['rms'])]] * n for i, n in zip(its, k)])
    wts = np.repeat([1 / counts[i['label']] for i in its], k)
    codec = SpectralResidual().fit(waves, groups, cond)
    gen = ResidualGenerator('flow', seed).fit(codec.z, codec.conditions[codec.pairs[:, 0]], wts[codec.pairs[:, 0]])
    rng = np.random.default_rng([seed, 20261112, len(donors)])
    anchors = {c: np.resize(rng.permutation(np.flatnonzero(lab == c)), NMAX) for c in sorted(counts)}
    idx = np.concatenate([anchors[c] for c in sorted(counts)])
    if prop:
        idx = np.concatenate([idx, np.arange(len(waves))])
    out = []
    for o in offsets:
        res = gen.sample(codec.conditions[idx], seed + o) * codec.scale
        g, _ = codec.apply(waves[idx], res, STRENGTH, peak[idx])
        f = feats_rows(g, fr[idx], its[0]['orders'])
        pools, start = {}, 0
        for c in sorted(counts):
            pools[c] = f[start:start + NMAX]; start += NMAX
        propf = {c: f[start:][lab == c] for c in sorted(counts)} if prop else None
        out.append((pools, propf))
    return out, dict(pairs=int(len(codec.pairs)), training_seconds=gen.training_seconds)


def with_synthetic(base, counts, rows, mass, real_factor=1.):
    x, y, w = base
    scale = len(x) / (1 + len(counts))
    w2 = w.copy()
    if real_factor != 1.:
        for c in counts:
            w2[y == c] *= real_factor
    xs, ys, ws = [x], [y], [w2]
    for c, a in rows.items():
        xs.append(a); ys.append(np.full(len(a), c, int)); ws.append(np.full(len(a), mass * scale / len(a)))
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(ws)


def fixed_arms(base, counts):
    x, y, w = base
    real_rows = {c: x[y == c] for c in counts}
    return {'real': base, 'dup_add_0.25': with_synthetic(base, counts, real_rows, .25),
            'dup_add_1': with_synthetic(base, counts, real_rows, 1.), 'uw_real': (x, y, np.ones(len(y)))}


def flow_arms(base, counts, pools, propf, names):
    x, y, w = base
    out = {}
    for name in names:
        if name.startswith('flow_add_'):
            _, _, a, n = name.split('_'); out[name] = with_synthetic(base, counts, {c: pools[c][:int(n)] for c in counts}, float(a))
        elif name.startswith('flow_mix_'):
            _, _, b, n = name.split('_'); b = float(b)
            out[name] = with_synthetic(base, counts, {c: pools[c][:int(n)] for c in counts}, b, 1 - b)
        elif name == 'flow_prop':
            out[name] = with_synthetic(base, counts, propf, .25)
        elif name == 'uw_topup':
            n_real = {c: int((y == c).sum()) for c in counts}; top = max(n_real.values())
            add = {c: pools[c][:top - n_real[c]] for c in counts if top > n_real[c]}
            xs = [x] + list(add.values()); ys = [y] + [np.full(len(a), c, int) for c, a in add.items()]
            xx, yy = np.concatenate(xs), np.concatenate(ys); out[name] = (xx, yy, np.ones(len(yy)))
    return out


def fit_predict(xyw, seed, inputs):
    m = InvariantClassifier('rf', seed).fit(*xyw)
    return {k: selective(causal_average(m.predict_proba(v)), 0).tolist() for k, v in inputs.items()}


def select(ds, target, seed, donors):
    """Installation-time dose choice using only the machine's confirmed events (leave one event out)."""
    t = item(ds, target)
    counts = Counter(item(ds, n)['label'] for n in donors)
    held = [n for n in donors if counts[item(ds, n)['label']] >= 2]
    if not held:
        return dict(choice='real', reason='no_class_with_two_events', validation={}, held=[])
    rec = {a: {} for a in CANDIDATES}
    for h in held:
        rem = [n for n in donors if n != h]
        rc = Counter(item(ds, n)['label'] for n in rem)
        events = [(n, item(ds, n)['label'], item(ds, n)['donor']) for n in rem]
        base = training(t['base'], events, {}, 'real')
        ((pools, _),), _ = generate(ds, rem, seed, (OFFSETS[0],), prop=False)
        arms = {**{k: v for k, v in fixed_arms(base, rc).items() if k in CANDIDATES},
                **flow_arms(base, rc, pools, None, [a for a in CANDIDATES if a.startswith('flow_')])}
        c = item(ds, h)['label']
        for a in CANDIDATES:
            p = np.asarray(fit_predict(arms[a], seed, {'v': item(ds, h)['donor']})['v'])
            rec[a].setdefault(c, []).append(float((p == c).mean()))
    score = {a: float(np.mean([np.mean(v) for v in rec[a].values()])) for a in CANDIDATES}
    best = max(CANDIDATES, key=lambda a: (round(score[a], 10), -CANDIDATES.index(a)))
    return dict(choice=best, validation=score, held=[str(h) for h in held])


def job(task):
    ds, target, seed, profile = task
    start = time.perf_counter()
    t = item(ds, target)
    donors = donors_for(ds, target, seed, profile)
    counts = Counter(item(ds, n)['label'] for n in donors)
    events = [(n, item(ds, n)['label'], item(ds, n)['donor']) for n in donors]
    base = training(t['base'], events, {}, 'real')
    inputs = {st: t[st] for st in STAGES}
    scores = {name: fit_predict(xyw, seed, inputs) for name, xyw in fixed_arms(base, counts).items()}
    gens, info = generate(ds, donors, seed, OFFSETS)
    for o, (pools, propf) in zip(OFFSETS, gens):
        for name, xyw in flow_arms(base, counts, pools, propf, FLOW).items():
            scores[f'{name}@{o}'] = fit_predict(xyw, seed, inputs)
    sel = select(ds, target, seed, donors)
    return dict(ds=ds, target=str(target), seed=seed, profile=profile, label=t['label'], donors=[str(d) for d in donors],
                events={str(c): counts[c] for c in CLASSES}, scores=scores, selection=sel, generator=info,
                elapsed_seconds=time.perf_counter() - start)


def tasks():
    out = [('uored', n, s, p) for p in PROFILES for n in UNAMES for s in SEEDS]
    out += [('xjtu', n, s, 'natural') for n in XLABEL for s in SEEDS]
    return out


def task_path(task):
    ds, n, s, p = task
    return OUT / 'tasks' / f'{ds}_{p}_{n}_{s}.json'


# ---------------- reporting ----------------

def keys_of(arm):
    return [arm] if arm in FIXED else [f'{arm}@{o}' for o in OFFSETS]


def row_recall(r, arm, stage, label=None):
    if arm == 'selector':
        arm = r['selection']['choice']
    lab = r['label'] if label is None else label
    return float(np.mean([np.mean(np.asarray(r['scores'][k][stage]) == lab) for k in keys_of(arm)]))


def bearing_scores(rows, arm, stage='severe'):
    per = {}
    for r in rows:
        per.setdefault((r['target'], r['label']), []).append(row_recall(r, arm, stage))
    return {k: float(np.mean(v)) for k, v in per.items()}


def macro(b):
    return float(np.mean([np.mean([v for (n, l), v in b.items() if l == c]) for c in CLASSES]))


def classes_of(b):
    return {c: float(np.mean([v for (n, l), v in b.items() if l == c])) for c in CLASSES}


def healthy_fault(rows, arm):
    vals = []
    for r in rows:
        a = r['selection']['choice'] if arm == 'selector' else arm
        vals += [float(np.mean(np.asarray(r['scores'][k]['hold']) > 0)) for k in keys_of(a)]
    return float(np.mean(vals))


def seed_range(rows, arm):
    v = [macro(bearing_scores([r for r in rows if r['seed'] == s], arm)) for s in SEEDS]
    return min(v), max(v)


def offset_range(rows, arm):
    if arm in FIXED or arm == 'selector':
        return None
    v = []
    for o in OFFSETS:
        per = {}
        for r in rows:
            per.setdefault((r['target'], r['label']), []).append(float(np.mean(np.asarray(r['scores'][f'{arm}@{o}']['severe']) == r['label'])))
        v.append(macro({k: float(np.mean(x)) for k, x in per.items()}))
    return min(v), max(v)


def paired(rows, a, b, rng):
    A, B = bearing_scores(rows, a), bearing_scores(rows, b)
    groups = {c: [k for k in A if k[1] == c] for c in CLASSES}
    f = lambda ks: np.mean([np.mean([A[k] - B[k] for k in ks if k[1] == c]) for c in CLASSES])
    pt = f(list(A))
    bs = [f([x for g in groups.values() for x in [g[i] for i in rng.integers(len(g), size=len(g))]]) for _ in range(5000)]
    return dict(delta=float(pt), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])


def report():
    rows = [json.loads(p.read_text()) for p in sorted((OUT / 'tasks').glob('*.json'))]
    rng = np.random.default_rng(20261112)
    arms = ('real',) + FIXED[1:] + FLOW + ('selector',)
    groups = [('uored', p) for p in PROFILES] + [('xjtu', 'natural')]
    res, comps, choice = {}, {}, {}
    for ds, p in groups:
        sub = [r for r in rows if r['ds'] == ds and r['profile'] == p]
        if not sub:
            continue
        key = f'{ds}:{p}'
        ev = Counter()
        for r in sub:
            for c, v in r['events'].items():
                ev[c] += v
        res[key] = dict(n_rows=len(sub), mean_events={c: ev[c] / len(sub) for c in ev}, arms={})
        for a in arms:
            b = bearing_scores(sub, a)
            res[key]['arms'][a] = dict(severe=macro(b), classes=classes_of(b), developing=macro(bearing_scores(sub, a, 'developing')),
                                      healthy_fault=healthy_fault(sub, a), seed_range=seed_range(sub, a), offset_range=offset_range(sub, a))
        c = {}
        for a in arms:
            if a != 'real':
                c[f'{a} - real'] = paired(sub, a, 'real', rng)
        for a in ('0.25', '1'):
            for n in NS:
                c[f'flow_add_{a}_{n} - dup_add_{a}'] = paired(sub, f'flow_add_{a}_{n}', f'dup_add_{a}', rng)
        c['flow_prop - dup_add_0.25'] = paired(sub, 'flow_prop', 'dup_add_0.25', rng)
        c['uw_topup - uw_real'] = paired(sub, 'uw_topup', 'uw_real', rng)
        comps[key] = c
        choice[key] = dict(Counter(r['selection']['choice'] for r in sub))
    # Declared answer rules
    flow_arms_only = [a for a in FLOW if a.startswith('flow_')]
    universal = {}
    for a in flow_arms_only:
        ok = True
        for key, v in res.items():
            best = max(x['severe'] for x in v['arms'].values())
            s = v['arms'][a]
            ok &= s['severe'] >= best - .02 and s['severe'] >= v['arms']['real']['severe'] and s['healthy_fault'] <= .05
        universal[a] = bool(ok)
    value = {}
    for key, c in comps.items():
        hits = [k for k, v in c.items() if v['ci95'][0] > 0 and (k.startswith('flow_mix') and k.endswith('- real') or
                                                                 (k.startswith('flow_add') and '- dup_add' in k) or k.startswith('flow_prop - dup'))]
        value[key] = hits
    n_profiles_with_value = sum(bool(v) for v in value.values())
    sel_ok = all(v['arms']['selector']['severe'] >= v['arms']['real']['severe'] - .01 for v in res.values())
    sel_mean = float(np.mean([v['arms']['selector']['severe'] - v['arms']['real']['severe'] for v in res.values()]))
    rules = dict(universal_dose_rule=any(universal.values()), universal_detail=universal,
                 synthetic_value=n_profiles_with_value >= 2, synthetic_value_detail=value,
                 selector_usable=bool(sel_ok and sel_mean > 0), selector_mean_gain=sel_mean)
    (OUT / 'summary.json').write_text(json.dumps(dict(protocol='PROTOCOL_S3_DOSE.md', results=res, comparisons=comps, selector_choices=choice,
                                                     rules=rules, confirmatory=False), indent=2, ensure_ascii=False), encoding='utf-8')
    markdown(res, comps, choice, rules)
    figure(res)


def pct(x):
    return f'{x * 100:.1f}'


def markdown(res, comps, choice, rules):
    L = ['# S3-Dose: sinh bao nhiêu mẫu cho mỗi loại lỗi', '',
         'Macro recall 3 lớp lỗi ở trạng thái nặng (UORED) hoặc cuối đời (XJTU); Flow trung bình 3 hạt giống lấy mẫu. Thăm dò, không phải xác nhận.', '']
    L += ['## Kết luận theo quy tắc khai báo trước', '',
          f"- Có quy tắc liều chung: **{'CÓ' if rules['universal_dose_rule'] else 'KHÔNG'}** "
          f"({', '.join(a for a, v in rules['universal_detail'].items() if v) or 'không nhánh nào đạt'})",
          f"- Mẫu sinh có giá trị riêng ở ≥ 2 bộ sự cố: **{'CÓ' if rules['synthetic_value'] else 'KHÔNG'}**",
          f"- Chọn liều được lúc lắp đặt: **{'CÓ' if rules['selector_usable'] else 'KHÔNG'}** (trung bình so với real {rules['selector_mean_gain']*100:+.2f} điểm)", '']
    for key, v in rules['synthetic_value_detail'].items():
        L.append(f'  - {key}: ' + (', '.join(v) if v else 'không có so sánh nào có CI dương'))
    for key, v in res.items():
        ev = ', '.join(f"{CNAME[int(c)]} {x:.1f}" for c, x in sorted(v['mean_events'].items()))
        L += ['', f'## {key} (số sự cố trung bình: {ev}; {v["n_rows"]} lượt)', '',
              '| Nhánh | Macro | Trong | Ngoài | Cách | Đang phát triển | Gán lỗi trên khỏe | Theo seed | Theo hạt giống | So với real (CI 95%) |',
              '|---|---:|---:|---:|---:|---:|---:|---|---|---|']
        for a, s in v['arms'].items():
            cmp = comps[key].get(f'{a} - real')
            cs = f"{cmp['delta']*100:+.1f} [{cmp['ci95'][0]*100:+.1f}; {cmp['ci95'][1]*100:+.1f}]" if cmp else ''
            orr = f"{pct(s['offset_range'][0])}–{pct(s['offset_range'][1])}" if s['offset_range'] else ''
            L.append(f"| {a} | {pct(s['severe'])} | {pct(s['classes'][1])} | {pct(s['classes'][2])} | {pct(s['classes'][4])} | {pct(s['developing'])} | "
                     f"{pct(s['healthy_fault'])} | {pct(s['seed_range'][0])}–{pct(s['seed_range'][1])} | {orr} | {cs} |")
        L += ['', '| Giá trị riêng của mẫu sinh (cùng khối lượng) | Chênh | CI 95% |', '|---|---:|---|']
        for k, c in comps[key].items():
            if '- dup_add' in k or k.startswith('flow_mix') or k.startswith('uw_topup'):
                L.append(f"| {k} | {c['delta']*100:+.1f} | [{c['ci95'][0]*100:+.1f}; {c['ci95'][1]*100:+.1f}] |")
        L += ['', 'Bộ chọn lúc lắp đặt đã chọn: ' + ', '.join(f'{a} {n}' for a, n in sorted(choice[key].items(), key=lambda x: -x[1]))]
    (OUT / 'summary.md').write_text('\n'.join(L), encoding='utf-8')
    print('\n'.join(L[:12]))


def figure(res):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    keys = list(res)
    fig, axs = plt.subplots(2, 3, figsize=(13, 7), dpi=150, sharey=True)
    for ax, key in zip(axs.flat, keys):
        v = res[key]['arms']
        for a, col, lab in (('flow_add_0.25', '#10B981', 'Flow thêm 0,25'), ('flow_add_1', '#047857', 'Flow thêm 1'),
                            ('flow_mix_0.25', '#3B82F6', 'Flow trộn 0,25'), ('flow_mix_0.5', '#1D4ED8', 'Flow trộn 0,5')):
            ax.plot(NS, [v[f'{a}_{n}']['severe'] * 100 for n in NS], 'o-', color=col, label=lab, lw=2)
        ax.axhline(v['real']['severe'] * 100, color='#64748B', lw=2, label='Chỉ mẫu thật')
        ax.axhline(v['dup_add_0.25']['severe'] * 100, color='#94A3B8', ls='--', label='Bản sao +0,25')
        ax.axhline(v['selector']['severe'] * 100, color='#F59E0B', ls=':', lw=2, label='Bộ chọn lắp đặt')
        ax.set_xscale('log'); ax.set_xticks(NS); ax.set_xticklabels(NS); ax.set_title(key); ax.grid(alpha=.3)
        ax.set_xlabel('Số mẫu sinh mỗi loại lỗi')
    axs[0, 0].set_ylabel('Macro recall (%)'); axs[1, 0].set_ylabel('Macro recall (%)')
    axs[0, 0].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(OUT / 'dose.png')


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=12)
    ap.add_argument('--report', action='store_true')
    ap.add_argument('--smoke', action='store_true')
    a = ap.parse_args()
    (OUT / 'tasks').mkdir(parents=True, exist_ok=True)
    if a.smoke:
        for t in (('uored', 1, 11, '5-2-1'), ('xjtu', '2_3', 11, 'natural')):
            r = job(t)
            print(t, 'arms', len(r['scores']), 'events', r['events'], 'held', len(r['selection']['held']), round(r['elapsed_seconds'], 1), 's')
        return
    if not a.report:
        todo = [t for t in tasks() if not task_path(t).exists()]
        with ProcessPoolExecutor(a.workers) as pool:
            for i, (t, row) in enumerate(zip(todo, pool.map(job, todo)), 1):
                task_path(t).write_text(json.dumps(row))
                print('dose', i, '/', len(todo), t, round(row['elapsed_seconds'], 1), 's', flush=True)
    report()


if __name__ == '__main__':
    main()
