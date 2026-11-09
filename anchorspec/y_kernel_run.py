"""Run the fixed kernel protocol using exactly the saved adaptive donor sets."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import hashlib
import json
import pickle
import time

from kernel_experts import KernelExperts
from y_run import load_store, synthetic, donors, score, OUT, ROOT, hashes


def job(old):
    target, seed = old['target'], old['seed']
    store = load_store()
    item = store[target]
    syn = synthetic(target, seed, item)
    available = {e.event_id: e for e in donors(store, target, seed)}
    events = [replace(available[key], label=label) for key, label in zip(old['donor_events'], old['donor_labels'])]
    refs = {n: {'mu': store[n]['mu'], 'sd': store[n]['sd']} for n in {target} | {e.bearing_id for e in events}}
    healthy = {e.bearing_id: store[e.bearing_id]['hold'] for e in events}
    row = {k: old[k] for k in ('target','seed','budget','label','control','mode','donor_events','donor_labels')}
    row |= {'scores': {}, 'costs': {}, 'selection': {}}
    for name, real in (('kernel', False), ('kernel_real', True)):
        start = time.perf_counter()
        model = KernelExperts(seed, real).fit(item['base'], syn, events, target_id=target, references=refs, donor_healthy=healthy)
        row['costs'][name] = {'fit_ms': 1000*(time.perf_counter()-start), 'pickle_bytes': len(pickle.dumps(model))}
        row['selection'][name] = {'representation': model.representation_, 'synthetic_mass': model.synthetic_mass_, 'C': model.C_,
                                 'validation': model.validation_, 'inner_folds': model.inner_folds_}
        row['scores'][name] = score(model, item)
    return row


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--mode', choices=('balanced','stream'), default='balanced')
    args = p.parse_args()
    previous = json.loads((OUT/f'adaptive_{args.mode}.json').read_text())['rows']
    frozen = hashes() | {n: hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in
                        ('kernel_experts.py','y_kernel_run.py','adaptive_experts.py','PROTOCOL_Y_KERNEL.md')}
    rows = []
    with ProcessPoolExecutor(4) as pool:
        for index, row in enumerate(pool.map(job, previous), 1):
            rows.append(row)
            if index % 20 == 0:
                print(f'kernel {args.mode}: {index}/{len(previous)}', flush=True)
    if any(hashlib.sha256((ROOT/n).read_bytes()).hexdigest() != h for n,h in frozen.items()):
        raise RuntimeError('Source changed during experiment')
    (OUT/f'kernel_{args.mode}.json').write_text(json.dumps({'code_sha256': frozen, 'rows': rows},indent=2),encoding='utf8')


if __name__ == '__main__':
    main()
