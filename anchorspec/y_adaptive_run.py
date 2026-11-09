"""Nested event-level adaptive experiment; target files are scored only after fit."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import hashlib
import json
import pickle
import time

from adaptive_experts import AdaptiveExperts
from event_experts import CLASSES
from y_run import load_store, synthetic, donors, score, OUT, ROOT, SEEDS, hashes


def job(args):
    target, seed, mode = args
    store = load_store()
    item = store[target]
    syn = synthetic(target, seed, item)
    stream = donors(store, target, seed)
    rows = []
    for budget in ((1, 2, 4) if mode == 'balanced' else (0, 2, 4, 8, 12)):
        chosen = ([e for c in range(1, 5) for e in [v for v in stream if v.label == c][:budget]]
                  if mode == 'balanced' else stream[:budget])
        for control in (('clean', 'wrong_labels') if mode == 'balanced' and budget == 1 else ('clean',)):
            events = chosen if control == 'clean' else [replace(e, label=e.label % 4 + 1) for e in chosen]
            row = {'target': target, 'label': CLASSES.index(item['lab']), 'seed': seed,
                   'mode': mode, 'budget': budget, 'control': control,
                   'donor_events': [e.event_id for e in events], 'donor_labels': [e.label for e in events],
                   'scores': {}, 'costs': {}, 'selection': {}}
            # Only normalization statistics and selected donors' healthy calibration
            # features cross the fitting API. No target test features or labels.
            refs = {n: {'mu': store[n]['mu'], 'sd': store[n]['sd']} for n in {target} | {e.bearing_id for e in events}}
            healthy = {e.bearing_id: store[e.bearing_id]['hold'] for e in events}
            for method, real_only in (('adaptive', False), ('adaptive_real', True)):
                start = time.perf_counter()
                model = AdaptiveExperts(seed, real_only).fit(item['base'], syn, events,
                    target_id=target, references=refs, donor_healthy=healthy)
                row['costs'][method] = {'fit_ms': (time.perf_counter() - start) * 1000,
                                       'pickle_bytes': len(pickle.dumps(model))}
                row['selection'][method] = {'representation': model.representation_,
                    'synthetic_mass': model.synthetic_mass_, 'validation': model.validation_,
                    'inner_folds': model.inner_folds_}
                row['scores'][method] = score(model, item)
            rows.append(row)
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--mode', choices=('balanced', 'stream'), default='balanced')
    p.add_argument('--workers', type=int, default=4)
    args = p.parse_args()
    frozen = hashes() | {n: hashlib.sha256((ROOT/n).read_bytes()).hexdigest()
        for n in ('adaptive_experts.py', 'y_adaptive_run.py', 'PROTOCOL_Y_ADAPTIVE.md')}
    tasks = [(str(n), seed, args.mode) for n in range(1, 21) for seed in SEEDS]
    rows = []
    with ProcessPoolExecutor(args.workers) as pool:
        for index, output in enumerate(pool.map(job, tasks), 1):
            rows.extend(output)
            print(f'adaptive {args.mode}: {index}/60', flush=True)
    if any(hashlib.sha256((ROOT/n).read_bytes()).hexdigest() != h for n, h in frozen.items()):
        raise RuntimeError('Source changed during experiment')
    (OUT / f'adaptive_{args.mode}.json').write_text(json.dumps({'code_sha256': frozen, 'rows': rows}, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
