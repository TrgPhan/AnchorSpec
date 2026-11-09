"""Local Y1/Y4/Y8 exploration. Run prepare, then run, then report. No cloud calls."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import pickle
import platform
import time

os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')

import numpy as np

import e8_uored as U
import funnel as Fu
from event_experts import CLASSES, Event, EventExperts, causal_average
import x_core as X
from y_metrics import bearing_values, macro, paired_delta

ROOT = Path(__file__).resolve().parent
CACHE = ROOT.parent / 'data' / 'y_cache'
OUT = ROOT / 'results' / 'y'
SEEDS = (11, 29, 47)
METHODS = ('injection', 'real', 'hybrid', 'protected')


def hashes():
    names = ('y_run.py', 'event_experts.py', 'y_metrics.py', 'PROTOCOL_Y_LOCAL.md',
             'x_core.py', 'e8_uored.py', 'features.py', 'injection.py', 'funnel.py', 'cheap_sensor.py')
    return {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in names}


def prepare_item(name):
    key, value = X.store_item(('uored', name))
    np.savez_compressed(CACHE / f'bearing_{key}.npz', **value)
    return key


def load_store():
    store = {}
    for name in X.names('uored'):
        with np.load(CACHE / f'bearing_{name}.npz', allow_pickle=False) as f:
            store[name] = {k: f[k] for k in f.files}
        store[name]['lab'] = str(store[name]['lab'])
        store[name]['fr'] = float(store[name]['fr'])
    return store


def synthetic(name, seed, item):
    path = CACHE / f'synthetic_{name}_{seed}.npz'
    signature = hashlib.sha256(json.dumps({k: v for k, v in hashes().items()
        if k in ('features.py', 'injection.py', 'funnel.py', 'cheap_sensor.py', 'x_core.py', 'e8_uored.py')}, sort_keys=True).encode()).hexdigest()
    if path.exists():
        with np.load(path, allow_pickle=False) as f:
            if str(f['signature']) == signature:
                return {c: f[f'c{c}'] for c in (1, 2)}
    base, orders = X.raw_base('uored', name)
    rng = np.random.default_rng([seed, sum(map(ord, name)), 7])
    result = {}
    for c in (1, 2):
        raw = Fu.injected(base, CLASSES[c], 150, item['fr'], orders, X.S, 4000, rng)
        result[c] = (Fu.feats(raw, 4000, item['fr'], orders) - item['mu']) / item['sd']
    np.savez_compressed(path, signature=signature, **{f'c{c}': a for c, a in result.items()})
    return result


def donors(store, target, seed):
    # One common stream per seed. Remove the target without inspecting its class.
    order = np.random.default_rng(seed).permutation(sorted(store, key=int))
    return [Event(f'UORED:{n}:2', str(n), CLASSES.index(store[n]['lab']), store[n]['late'])
            for n in order if n != target]


def representation(z, item, kind):
    if kind == 'z':
        return z
    delta = z * item['sd']
    raw = delta + item['mu']
    if kind == 'delta':
        return delta
    if kind == 'raw':
        return raw
    if kind == 'both':
        return np.column_stack((raw, delta))
    raise ValueError(kind)


def score(model, item):
    correct = CLASSES.index(item['lab'])
    output = {}
    for state in ('early', 'late', 'hold'):
        x = item[state]
        p = model.predict_proba(x)
        # Historical healthy control is unsmoothed; fault sequences use causal averaging.
        p = p if state == 'hold' else causal_average(p)
        pred = p.argmax(1)
        truth = 0 if state == 'hold' else correct
        output[state] = {'recall': float(np.mean(pred == truth)),
            'event_correct': int(np.bincount(pred, minlength=5).argmax() == truth),
            'pred_counts': np.bincount(pred, minlength=5).tolist(), 'n_windows': len(pred),
            'copied_wrong': float(np.mean(pred == (correct % 4 + 1))) if truth else None}
    return output


def job(args):
    name, seed, mode, rep = args
    store = load_store()
    item = store[name]
    syn = synthetic(name, seed, item)
    syn = {c: representation(x, item, rep) for c, x in syn.items()}
    for value in store.values():
        for state in ('base', 'hold', 'early', 'late'):
            value[state] = representation(value[state], value, rep)
    stream = donors(store, name, seed)
    rows = []
    budgets = (1, 2, 4) if mode == 'balanced' else (0, 2, 4, 8, 12)
    for budget in budgets:
        if mode == 'balanced':
            chosen = [e for c in range(1, 5) for e in [v for v in stream if v.label == c][:budget]]
        else:
            chosen = stream[:budget]
        controls = ('clean', 'wrong_labels') if mode == 'balanced' and budget == 1 else ('clean',)
        for control in controls:
            events = chosen if control == 'clean' else [replace(e, label=e.label % 4 + 1) for e in chosen]
            row = {'target': name, 'label': CLASSES.index(item['lab']), 'seed': seed,
                   'budget': budget, 'mode': mode, 'representation': rep, 'control': control,
                   'donor_events': [e.event_id for e in events],
                   'donor_labels': [e.label for e in events], 'scores': {}, 'costs': {}}
            for method in METHODS:
                t0 = time.perf_counter()
                model = EventExperts(method, seed).fit(item['base'], syn, events, target_id=name)
                fit_ms = (time.perf_counter() - t0) * 1000
                t0 = time.perf_counter()
                model.predict_proba(item['late'][:1])
                infer_ms = (time.perf_counter() - t0) * 1000
                row['scores'][method] = score(model, item)
                row['costs'][method] = {'fit_ms': fit_ms, 'feature_input_infer_ms': infer_ms,
                                        'pickle_bytes': len(pickle.dumps(model))}
            rows.append(row)
    return rows


def report(mode, rep='z'):
    stem = mode if rep == 'z' else f'{mode}_{rep}'
    document = json.loads((OUT / f'{stem}.json').read_text(encoding='utf8'))
    rows = document['rows']
    summary = {'mode': mode, 'representation': rep, 'exploratory_reused_dataset': True, 'data': 'UORED v5', 'budgets': {}}
    for budget in sorted({r['budget'] for r in rows}):
        entry = {'methods': {}}
        for method in METHODS:
            entry['methods'][method] = {}
            for state in ('early', 'late', 'hold'):
                v = bearing_values(rows, method, 'recall', budget=budget, state=state)
                entry['methods'][method][state] = {'macro_recall': macro(v),
                    'per_class': {CLASSES[c]: macro({k: a for k, a in v.items() if k[1] == c}) for c in range(1, 5)}}
            entry['methods'][method]['event_accuracy_late'] = macro(bearing_values(rows, method, 'event_correct', budget=budget))
        for baseline in ('injection', 'real', 'hybrid'):
            for state in ('early', 'late'):
                entry[f'protected_minus_{baseline}_{state}'] = paired_delta(
                    bearing_values(rows, 'protected', 'recall', budget=budget, state=state),
                    bearing_values(rows, baseline, 'recall', budget=budget, state=state))
        a = bearing_values(rows, 'protected', 'recall', budget=budget, labels=(1, 2))
        b = bearing_values(rows, 'hybrid', 'recall', budget=budget, labels=(1, 2))
        entry['ring_delta'] = paired_delta(a, b)
        protected_fpr = 1 - entry['methods']['protected']['hold']['macro_recall']
        hybrid_fpr = 1 - entry['methods']['hybrid']['hold']['macro_recall']
        gain = entry['protected_minus_hybrid_late']
        entry['screen'] = {'gain_at_least_10pp': gain['delta'] >= .1,
                           'paired_ci_positive': gain['ci95'][0] > 0,
                           'ring_loss_at_most_5pp': entry['ring_delta']['delta'] >= -.05,
                           'healthy_fpr_increase_at_most_2pp': protected_fpr - hybrid_fpr <= .02,
                           'healthy_fpr_protected': protected_fpr, 'healthy_fpr_hybrid': hybrid_fpr}
        summary['budgets'][str(budget)] = entry
    if mode == 'balanced':
        summary['wrong_label_control'] = {m: {control: {
            'recall': macro(bearing_values(rows, m, 'recall', budget=1, control=control)),
            'copied_wrong': macro(bearing_values(rows, m, 'copied_wrong', budget=1, control=control))}
            for control in ('clean', 'wrong_labels')} for m in METHODS}
    (OUT / f'{stem}_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf8')
    for budget, entry in summary['budgets'].items():
        print(mode, budget, {m: round(e['late']['macro_recall'], 4) for m, e in entry['methods'].items()}, entry['screen'], flush=True)
    if 'wrong_label_control' in summary:
        print('wrong labels', summary['wrong_label_control'], flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=('prepare', 'run', 'report'))
    p.add_argument('--mode', choices=('balanced', 'stream'), default='balanced')
    p.add_argument('--workers', type=int, default=4)
    p.add_argument('--representation', choices=('z', 'delta', 'raw', 'both'), default='z')
    a = p.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    if a.action == 'prepare':
        with ProcessPoolExecutor(a.workers) as pool:
            for name in pool.map(prepare_item, X.names('uored')):
                print('prepared', name, flush=True)
        (CACHE / 'prepare_hashes.json').write_text(json.dumps(hashes(), indent=2), encoding='utf8')
    elif a.action == 'run':
        expected = json.loads((CACHE / 'prepare_hashes.json').read_text())
        for name in ('x_core.py', 'e8_uored.py', 'features.py', 'cheap_sensor.py'):
            if expected[name] != hashes()[name]:
                raise ValueError('Feature cache stale; rerun prepare')
        frozen = hashes()
        rows = []
        tasks = [(n, seed, a.mode, a.representation) for n in X.names('uored') for seed in SEEDS]
        with ProcessPoolExecutor(a.workers) as pool:
            for number, result in enumerate(pool.map(job, tasks), 1):
                rows.extend(result)
                print(f'{a.mode}: {number}/{len(tasks)} bearing-seed jobs', flush=True)
        if frozen != hashes():
            raise RuntimeError('Source changed during experiment')
        result = {'code_sha256': frozen, 'seeds': SEEDS, 'platform': platform.platform(),
                  'python': platform.python_version(), 'rows': rows}
        stem = a.mode if a.representation == 'z' else f'{a.mode}_{a.representation}'
        (OUT / f'{stem}.json').write_text(json.dumps(result, indent=2), encoding='utf8')
        report(a.mode, a.representation)
    else:
        report(a.mode, a.representation)


if __name__ == '__main__':
    main()
