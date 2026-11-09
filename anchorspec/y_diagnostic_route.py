"""Separate conditional diagnosis from end-to-end classification.

Reconstruct exactly the saved fitted configurations and first assert their old
scores reproduce. Then restrict the decision to fault classes for a hypothetical
correct upstream abnormal-event gate. This is NOT an end-to-end accuracy estimate.
"""
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import hashlib
import json
import numpy as np

from adaptive_experts import fit_weighted, transform
from event_experts import EventExperts, causal_average, _prob
from kernel_experts import KernelModel
from y_run import load_store, synthetic, donors, OUT, ROOT
from y_report import merge
from y_metrics import macro, paired_delta


def diagnosis(probabilities, abnormal_event):
    """An upstream gate enables fault hypotheses; score is not confidence."""
    if not abnormal_event:
        return np.zeros(len(probabilities), int)
    p = np.asarray(probabilities)[:, 1:]
    labels = p.argmax(1) + 1
    labels[p.sum(1) <= 0] = -1  # no learned/simulated fault support
    return labels


def job(row):
    target, seed = row['target'], row['seed']
    store = load_store()
    item = store[target]
    syn = synthetic(target, seed, item)
    available = {e.event_id: e for e in donors(store, target, seed)}
    events = [replace(available[key], label=label) for key,label in zip(row['donor_events'],row['donor_labels'])]
    output = {k: row[k] for k in ('target','seed','budget','label','mode','control')}
    output['scores'] = {}
    for method in row['scores']:
        if method in ('injection','real','hybrid','protected'):
            model = EventExperts(method,seed).fit(item['base'],syn,events,target_id=target)
            predict = model.predict_proba
        else:
            s = row['selection'][method]
            rep, mass = s['representation'], s['synthetic_mass']
            h = transform(item['base'],item,rep)
            sy = {c: transform(x,item,rep) for c,x in syn.items()}
            ev = [replace(e,features=transform(e.features,store[e.bearing_id],rep)) for e in events]
            if method.startswith('kernel'):
                model = KernelModel(s['C']).fit(h,sy,ev,mass)
                predict = lambda x: model.predict_proba(transform(x,item,rep))
            else:
                model = fit_weighted(h,sy,ev,mass,seed)
                predict = lambda x: _prob(model,transform(x,item,rep),5)
        output['scores'][method] = {}
        for state in ('early','late','hold'):
            p = predict(item[state])
            p = p if state == 'hold' else causal_average(p)
            old = np.bincount(p.argmax(1),minlength=5).tolist()
            if old != row['scores'][method][state]['pred_counts']:
                raise AssertionError(f'Replay mismatch {target} {seed} {method} {state}')
            pred = diagnosis(p, True)
            output['scores'][method][state] = {
                'conditional_recall': float((pred == row['label']).mean()) if state != 'hold' else None,
                'coverage': float((pred > 0).mean()),
                'n_windows': len(pred), 'prediction_counts': {str(k): int((pred == k).sum()) for k in (-1,1,2,3,4)}}
    return output


def values(rows,method,budget,state='late',labels=None):
    from collections import defaultdict
    groups=defaultdict(list)
    for r in rows:
        if r['budget']==budget and (labels is None or r['label'] in labels):
            groups[(r['target'],r['label'])].append(r['scores'][method][state]['conditional_recall'])
    return {k: float(np.mean(v)) for k,v in groups.items()}


def main():
    rows=[]
    for mode in ('balanced','stream'):
        base=merge(mode)
        extra=json.loads((OUT/f'kernel_{mode}.json').read_text())['rows']
        key=lambda r:(r['target'],r['seed'],r['budget'],r['control'])
        lookup={key(r):r for r in extra}
        for r in base:
            if r['control']!='clean':
                continue
            e=lookup[key(r)]
            assert r['donor_events']==e['donor_events']
            rows.append(r | {'scores':r['scores']|e['scores'],'selection':r['selection']|e['selection']})
    frozen={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob('*.py')}
    output=[]
    with ProcessPoolExecutor(4) as pool:
        for i,r in enumerate(pool.map(job,rows),1):
            output.append(r)
            if i%60==0: print('replay and conditional diagnosis',i,'/',len(rows),flush=True)
    summary={}
    for mode in ('balanced','stream'):
        subset=[r for r in output if r['mode']==mode]
        summary[mode]={}
        for budget in sorted({r['budget'] for r in subset}):
            methods={m:macro(values(subset,m,budget)) for m in subset[0]['scores']}
            summary[mode][str(budget)]={'macro_recall':methods,'kernel_minus_hybrid':paired_delta(values(subset,'kernel',budget),values(subset,'hybrid',budget))}
            print(mode,budget,methods,flush=True)
    result={'upstream_fault_gate':'assumed correct on known faults; not measured',
            'not_end_to_end':True,'saved_model_predictions_reproduced':True,'code_sha256':frozen,'summary':summary,'rows':output}
    (OUT/'conditional_diagnosis.json').write_text(json.dumps(result,indent=2),encoding='utf8')


if __name__=='__main__':
    main()
