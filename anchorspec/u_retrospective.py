"""Re-evaluate existing UORED generators with exact duplication invariance."""
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import hashlib
import json
import numpy as np
import u_natural as U
import v_transport_run as V
from y_metrics import bearing_values,macro,paired_delta


@lru_cache(None)
def envelope(name,seed):
    with np.load(U.ROOT.parent/'data/v_envelope'/f'{name}_{seed}.npz') as f:return f['features']


def hashes():
    out=U.hashes()
    for n in ('u_retrospective.py','PROTOCOL_U_RETROSPECTIVE.md','v_transport_run.py','y_run.py'):
        out[n]=hashlib.sha256((U.ROOT/n).read_bytes()).hexdigest()
    return out


def job(task):
    target,seed,budget=task;data=V.store();t=data[target];stream=V.donors(data,target,seed)
    events=[e for c in (1,2,3,4) for e in [v for v in stream if v.label==c][:budget]]
    V.validate_events(events,target);real=[];der={};raw=V.generated(target,seed)
    for event in events:
        n=event.bearing_id;s=data[n]
        real.append((n,event.label,V.represent(event.features,s,'raw')))
        der[n]={m:raw[f'{n}_{m}'] for m in ('surrogate','severity','transport','transport_mix')}
        der[n]['envelope']=envelope(n,seed)
    row=dict(target=target,seed=seed,budget=budget,label=('healthy','inner','outer','ball','cage').index(t['lab']),
        control='clean',donor_events=[e.event_id for e in events],scores={})
    healthy=V.represent(t['base'],t,'raw')
    for family in U.FAMILIES:
        reference={}
        for method in U.METHODS:
            model=U.InvariantClassifier(family,seed).fit(*U.training(healthy,real,der,method))
            key=f'{family}:{method}';row['scores'][key]={}
            for state in ('early','late'):
                p=model.predict_proba(V.represent(t[state],t,'raw'));pred=U.fault_labels(U.causal_average(p))
                if method=='real':reference[state]=p
                elif method=='duplicate':np.testing.assert_array_equal(reference[state],p)
                row['scores'][key][state]=dict(recall=float((pred==row['label']).mean()),
                    prediction_counts={str(c):int((pred==c).sum()) for c in (-1,0,1,2,3,4)})
    return row


def main():
    U.OUT.mkdir(parents=True,exist_ok=True);folder=U.OUT/'retrospective_tasks';folder.mkdir(exist_ok=True);frozen=hashes();rows=[];todo=[]
    for t in [(str(i),s,b) for i in range(1,21) for s in (11,29,47) for b in (1,2,4)]:
        path=folder/('_'.join(map(str,t))+'.json')
        if path.exists():
            old=json.loads(path.read_text())
            if old['code_sha256']!=frozen:raise ValueError('Checkpoint source mismatch')
            rows.append(old['row'])
        else:todo.append(t)
    (U.OUT/'retrospective_frozen.json').write_text(json.dumps(frozen),encoding='utf8')
    with ProcessPoolExecutor(4) as pool:
        for t,row in zip(todo,pool.map(job,todo)):
            rows.append(row);(folder/('_'.join(map(str,t))+'.json')).write_text(json.dumps(dict(row=row,code_sha256=frozen)),encoding='utf8')
            if len(rows)%10==0:print('UORED invariant audit',len(rows),'/180',flush=True)
    summary={}
    for budget in (1,2,4):
        summary[str(budget)]={}
        for family in U.FAMILIES:
            summary[str(budget)][family]={}
            for method in U.METHODS:
                summary[str(budget)][family][method]={}
                for state in ('early','late'):
                    vals=bearing_values(rows,f'{family}:{method}','recall',budget=budget,state=state)
                    summary[str(budget)][family][method][state]=dict(macro_recall=macro(vals),
                        per_class={str(c):macro({k:v for k,v in vals.items() if k[1]==c}) for c in (1,2,3,4)},
                        minus_real=paired_delta(vals,bearing_values(rows,f'{family}:real','recall',budget=budget,state=state)))
            print(budget,family,{m:round(v['late']['macro_recall'],4) for m,v in summary[str(budget)][family].items()},flush=True)
    if hashes()!=frozen:raise ValueError('Source changed during run')
    (U.OUT/'retrospective.json').write_text(json.dumps(dict(rows=rows,summary=summary,code_sha256=frozen,
        duplicate_predictions_identical=True,retrospective=True,conditional_diagnosis=True),indent=2),encoding='utf8')


if __name__=='__main__':main()
