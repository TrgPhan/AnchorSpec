"""Fair source benchmark on reused UORED; prepare -> run -> report."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pickle
import time

os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import numpy as np

from source_select import SourceSelector, SOURCES
from event_experts import EventExperts, causal_average
from diagnostic_experts import fault_labels
from y_run import load_store, donors, synthetic, ROOT, hashes
from y_metrics import bearing_values, macro, paired_delta
import e8_uored as U
import funnel as Fu

CACHE = ROOT.parent / 'data' / 'w_cache'
OUT = ROOT / 'results' / 'w'
LEGACY = ROOT.parent / 'generator_benchmark' / 'generators.py'
METHODS = ('legacy_real', 'legacy_physics', 'legacy_surrogate') + SOURCES + ('select',)


def source_hashes():
    paths = [ROOT/n for n in ('w_compare.py', 'source_select.py', 'PROTOCOL_W_COMPARE.md',
        'event_experts.py', 'adaptive_experts.py', 'diagnostic_experts.py', 'y_metrics.py')]
    return hashes() | {str(p.relative_to(ROOT.parent)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[LEGACY]}


def prepare_job(task):
    name, seed = task
    signature = hashlib.sha256(json.dumps(source_hashes(), sort_keys=True).encode()).hexdigest()
    path = CACHE / f'surrogate_{name}_{seed}.npz'
    if path.exists():
        with np.load(path) as f:
            if str(f['signature']) == signature:
                return name, seed
    spec = importlib.util.spec_from_file_location('legacy_generator', LEGACY)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    U.ALLOW_FAULT['on'] = True
    windows = U.windows50(U.sensed(int(name), 2, U.SENSORS['1k']), 4000)[:, 0]
    item = load_store()[name]
    rng = np.random.default_rng([seed, int(name), 20261104])
    anchors = rng.integers(len(windows), size=150)
    generated = np.stack([module.constrained_surrogate(windows[j], rng) for j in anchors])[:, None]
    features = (Fu.feats(generated, 4000, item['fr'], U.ORDERS)-item['mu'])/item['sd']
    np.savez_compressed(path, features=features, signature=signature, source_event=f'UORED:{name}:2',
                        anchor_indices=anchors, waveform_sha256=hashlib.sha256(windows.tobytes()).hexdigest())
    return name, seed


def row_job(task):
    name, seed, budget = task
    store = load_store(); item = store[name]
    stream = donors(store, name, seed)
    events = [e for c in range(1, 5) for e in [v for v in stream if v.label == c][:budget]]
    derivatives = {}
    for event in events:
        with np.load(CACHE/f'surrogate_{event.bearing_id}_{seed}.npz') as f:
            if str(f['source_event']) != event.event_id:
                raise ValueError('Derivative lineage mismatch')
            derivatives[event.event_id] = f['features']
    refs = {n: {'mu':v['mu'], 'sd':v['sd']} for n,v in store.items()}
    phy = synthetic(name, seed, item)
    start = time.perf_counter()
    model = SourceSelector(seed).fit(events, derivatives, phy, target_id=name, references=refs)
    fit_ms = 1000*(time.perf_counter()-start)
    row = dict(target=name, seed=seed, budget=budget, control='clean', label=int(next(e.label for e in donors(store, 'none', seed) if e.bearing_id == name)),
        donor_events=[e.event_id for e in events], choices=model.choices_, validation=model.validation_,
        inner_folds=model.inner_folds_, scores={}, fit_all_candidates_ms=fit_ms, costs={})
    for method in SOURCES+('select',):
        row['scores'][method] = {}
        for state in ('early', 'late'):
            pred = model.predict(item[state], method)
            row['scores'][method][state] = dict(recall=float((pred==row['label']).mean()),
                event_correct=int(np.bincount(pred, minlength=5).argmax()==row['label']),
                pred_counts=np.bincount(pred, minlength=5).tolist())
        start = time.perf_counter()
        for _ in range(10):
            model.predict(item['late'][:1], method)
        row['costs'][method] = dict(feature_input_infer_ms=100*(time.perf_counter()-start),
                                   pickle_bytes=len(pickle.dumps(model.models_[method])))
    # Historical RF design on exactly the same donors and conditional decisions.
    ring = {c:np.concatenate([derivatives[e.event_id][:150//budget] for e in events if e.label==c]) for c in (1,2)}
    for method, mode, s in (('legacy_real','real',phy),('legacy_physics','hybrid',phy),('legacy_surrogate','hybrid',ring)):
        old = EventExperts(mode, seed).fit(item['base'],s,events,target_id=name)
        row['scores'][method] = {}
        for state in ('early','late'):
            pred = fault_labels(causal_average(old.predict_proba(item[state])))
            row['scores'][method][state] = dict(recall=float((pred==row['label']).mean()),
                event_correct=int(np.bincount(pred.clip(0),minlength=5).argmax()==row['label']),
                pred_counts=np.bincount(pred.clip(0),minlength=5).tolist())
    return row


def report():
    doc = json.loads((OUT/'comparison.json').read_text(encoding='utf8'))
    rows = doc['rows']; summary = {}
    for budget in (1,2,4):
        result = {'methods':{},'select_minus':{}}
        for method in METHODS:
            result['methods'][method] = {}
            for state in ('early','late'):
                vals = bearing_values(rows,method,'recall',budget=budget,state=state)
                result['methods'][method][state] = dict(macro_recall=macro(vals),per_class={str(c):macro({k:v for k,v in vals.items() if k[1]==c}) for c in range(1,5)})
            result['methods'][method]['event_accuracy_late'] = macro(bearing_values(rows,method,'event_correct',budget=budget))
        select = bearing_values(rows,'select','recall',budget=budget)
        for other in METHODS[:-1]:
            result['select_minus'][other] = paired_delta(select,bearing_values(rows,other,'recall',budget=budget))
        result['selected_sources'] = {s:sum(r['choices']['select']['source']==s for r in rows if r['budget']==budget) for s in SOURCES}
        summary[str(budget)] = result
        print('budget',budget,{m:round(v['late']['macro_recall'],4) for m,v in result['methods'].items()},flush=True)
    (OUT/'summary.json').write_text(json.dumps(dict(exploratory_reused_dataset=True,conditional_on_correct_abnormal_gate=True,
        independent_validation=False,budgets=summary),indent=2),encoding='utf8')


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run','report'))
    p.add_argument('--workers',type=int,default=4); a=p.parse_args()
    CACHE.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    if a.action=='prepare':
        tasks=[(str(n),s) for n in range(1,21) for s in (11,29,47)]
        with ProcessPoolExecutor(a.workers) as pool:
            for i,r in enumerate(pool.map(prepare_job,tasks),1):
                print('surrogate',i,'/',len(tasks),r,flush=True)
        (CACHE/'hashes.json').write_text(json.dumps(source_hashes(),indent=2),encoding='utf8')
    elif a.action=='run':
        frozen=source_hashes()
        if json.loads((CACHE/'hashes.json').read_text())!=frozen:
            raise ValueError('Code changed after prepare')
        tasks=[(str(n),s,b) for n in range(1,21) for s in (11,29,47) for b in (1,2,4)]
        checkpoint=OUT/'tasks';checkpoint.mkdir(exist_ok=True)
        rows=[];todo=[]
        for t in tasks:
            path=checkpoint/('_'.join(map(str,t))+'.json')
            if path.exists():
                saved=json.loads(path.read_text());
                if saved['code_sha256']!=frozen: raise ValueError('Checkpoint source mismatch')
                rows.append(saved['row'])
            else:todo.append(t)
        with ProcessPoolExecutor(a.workers) as pool:
            for t,r in zip(todo,pool.map(row_job,todo)):
                rows.append(r)
                (checkpoint/('_'.join(map(str,t))+'.json')).write_text(json.dumps(dict(code_sha256=frozen,row=r)),encoding='utf8')
                print('comparison',len(rows),'/',len(tasks),t,flush=True)
        if source_hashes()!=frozen:raise RuntimeError('Source changed during run')
        (OUT/'comparison.json').write_text(json.dumps(dict(code_sha256=frozen,rows=rows),indent=2),encoding='utf8')
        report()
    else:report()


if __name__=='__main__':main()
