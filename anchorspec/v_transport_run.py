"""Freeze matched real-only classifiers, then test measured-fault generators."""
import argparse
from collections import Counter,defaultdict
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import time

os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
from measured_transport import generate
from source_select import FaultModel
from event_experts import validate_events,causal_average
from diagnostic_experts import fault_labels
from y_run import ROOT,load_store,donors
from y_metrics import bearing_values,macro,paired_delta
import e8_uored as U
import funnel as Fu

CACHE=ROOT.parent/'data'/'v_transport'
OUT=ROOT/'results'/'v'
METHODS=('real','duplicate','surrogate','severity','transport','transport_mix')
FAMILIES=('rf','svm1','svm10')
REPS=('z','delta','raw')


def frozen_hashes():
    return {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in
        ('v_transport_run.py','measured_transport.py','PROTOCOL_V_TRANSPORT.md','source_select.py','features.py','cheap_sensor.py','e8_uored.py','event_experts.py','y_run.py')}


@lru_cache(None)
def store():return load_store()


@lru_cache(None)
def waveforms():
    out={};U.ALLOW_FAULT['on']=True
    for n in store():
        h,_,_=U.machine(int(n),U.SENSORS['1k'])
        f=U.windows50(U.sensed(int(n),2,U.SENSORS['1k']),4000)
        out[n]=dict(healthy=h[:,0],fault=f[:,0])
    return out


@lru_cache(maxsize=60)
def generated(target,seed):
    with np.load(CACHE/f'{target}_{seed}.npz') as f:return {k:f[k] for k in f.files}


def prepare_job(task):
    target,seed=task;data=store();raw=waveforms();out={};metadata=[]
    for source in sorted(data,key=int):
        if source==target:continue
        arrays,meta=generate(raw[source]['fault'],raw[source]['healthy'],raw[target]['healthy'],
            data[source]['fr'],data[target]['fr'],np.random.default_rng([seed,int(target),int(source),20261104]))
        meta.update(source_bearing=source,target_healthy_bearing=target,source_state=2)
        metadata.append(meta)
        for method,x in arrays.items():
            fr=data[source]['fr'] if method=='severity' else data[target]['fr']
            out[f'{source}_{method}']=Fu.feats(x[:,None,:],4000,fr,U.ORDERS)
        with np.load(ROOT.parent/'data'/'w_cache'/f'surrogate_{source}_{seed}.npz') as f:
            out[f'{source}_surrogate']=f['features']*data[source]['sd']+data[source]['mu']
        if target=='1' and source=='2' and seed==11:
            np.savez_compressed(CACHE/'example_waveforms.npz',source_fault=raw[source]['fault'],
                source_healthy=raw[source]['healthy'],target_healthy=raw[target]['healthy'],**arrays)
    np.savez_compressed(CACHE/f'{target}_{seed}.npz',**out)
    (CACHE/f'{target}_{seed}_lineage.json').write_text(json.dumps(metadata),encoding='utf8')
    return target,seed


def represent(z,reference,rep):
    if rep=='z':return z
    a=z*reference['sd']
    return a if rep=='delta' else a+reference['mu']


def training(target,events,method,rep,mass,seed):
    validate_events(events,target)
    if method not in METHODS or not events:raise ValueError('Invalid training request')
    data=store();baseline=data[target];counts=Counter(e.label for e in events)
    groups=[(0,represent(baseline['base'],baseline,rep),1.)]
    gen=generated(target,seed) if method not in ('real','duplicate') else None
    for e in events:
        ref=data[e.bearing_id];x=represent(e.features,ref,rep)
        portion=1. if method=='real' else 1-mass
        groups.append((e.label,x,portion/counts[e.label]))
        if method=='real':continue
        if method=='duplicate':aug=x.copy()
        else:
            raw=gen[f'{e.bearing_id}_{method}'][:64//counts[e.label]]
            origin=baseline if method in ('transport','transport_mix') else ref
            aug=represent((raw-origin['mu'])/origin['sd'],origin,rep)
        groups.append((e.label,aug,mass/counts[e.label]))
    x=np.concatenate([a for _,a,_ in groups]);y=np.concatenate([np.full(len(a),c,int) for c,a,_ in groups])
    w=np.concatenate([np.full(len(a),portion/len(a)) for _,a,portion in groups])
    w*= (len(baseline['base'])+sum(len(e.features) for e in events))/w.sum()
    return x,y,w


def predict(model,target,state,rep,conditional=True):
    data=store()[target]
    p=model.predict_proba(represent(data[state],data,rep))
    if state!='hold':p=causal_average(p)
    return fault_labels(p) if conditional else p.argmax(1)


def validation(events,method,family,rep,mass,seed):
    values=defaultdict(list)
    for held in events:
        train=[e for e in events if e.bearing_id!=held.bearing_id]
        if held.label not in {e.label for e in train}:return None
        model=FaultModel(family,seed).fit(*training(held.bearing_id,train,method,rep,mass,seed))
        pred=predict(model,held.bearing_id,'late',rep)
        values[held.label].append(float((pred==held.label).mean()))
    return float(np.mean([np.mean(a) for a in values.values()]))


def job(task):
    target,seed,budget=task;data=store();stream=donors(data,target,seed)
    events=[e for c in range(1,5) for e in [v for v in stream if v.label==c][:budget]]
    configs=[]
    if budget>1:
        for family in FAMILIES:
            for rep in REPS:
                configs.append(dict(family=family,representation=rep,score=validation(events,'real',family,rep,0,seed)))
        chosen=max(configs,key=lambda r:(r['score'],-FAMILIES.index(r['family']),-REPS.index(r['representation'])))
    else:chosen=dict(family='svm1',representation='raw',score=None)
    family,rep=chosen['family'],chosen['representation']
    result=dict(target=target,seed=seed,budget=budget,label=('healthy','inner','outer','ball','cage').index(data[target]['lab']),
        control='clean',donor_events=[e.event_id for e in events],classifier=chosen,classifier_validation=configs,
        source_validation=[],chosen_masses={},scores={})
    for method in METHODS:
        choices=[dict(method=method,mass=0.,score=chosen['score'])] if method=='real' else [
            dict(method=method,mass=mass,score=validation(events,method,family,rep,mass,seed) if budget>1 else None)
            for mass in ((.25,.5) if budget>1 else (.5,))]
        result['source_validation'].extend(choices)
        pick=max(choices,key=lambda r:(r['score'] if r['score'] is not None else 0,-r['mass']))
        result['chosen_masses'][method]=pick['mass']
        model=FaultModel(family,seed).fit(*training(target,events,method,rep,pick['mass'],seed))
        result['scores'][method]={}
        for state in ('early','late','hold'):
            pred=predict(model,target,state,rep,conditional=state!='hold')
            truth=0 if state=='hold' else result['label']
            result['scores'][method][state]=dict(recall=float((pred==truth).mean()),
                prediction_counts={str(c):int((pred==c).sum()) for c in (-1,0,1,2,3,4)})
        result['scores'][method]['both']={'recall':float(np.mean([result['scores'][method][s]['recall'] for s in ('early','late')]))}
    adaptive=max(result['source_validation'],key=lambda r:(r['score'],-METHODS.index(r['method']),-r['mass'])) if budget>1 else dict(method='real',mass=0.,score=None)
    result['adaptive_choice']=adaptive;result['scores']['adaptive']=result['scores'][adaptive['method']]
    return result


def report():
    rows=json.loads((OUT/'transport.json').read_text())['rows'];result={}
    for budget in (1,2,4):
        b={'methods':{},'transport_mix_minus':{}}
        for method in (*METHODS,'adaptive'):
            b['methods'][method]={}
            for state in ('early','late','both','hold'):
                vals=bearing_values(rows,method,'recall',budget=budget,state=state)
                b['methods'][method][state]=dict(macro_recall=macro(vals),per_class={str(c):macro({k:v for k,v in vals.items() if k[1]==c}) for c in range(1,5)})
        for other in METHODS[:-1]:
            b['transport_mix_minus'][other]={st:paired_delta(bearing_values(rows,'transport_mix','recall',budget=budget,state=st),
                    bearing_values(rows,other,'recall',budget=budget,state=st)) for st in ('early','late','both')}
        result[str(budget)]=b
        print('budget',budget,{m:round(v['both']['macro_recall'],4) for m,v in b['methods'].items()},flush=True)
    (OUT/'transport_summary.json').write_text(json.dumps(dict(exploratory=True,conditional_diagnosis=True,budgets=result),indent=2),encoding='utf8')


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run','report'));p.add_argument('--workers',type=int,default=4);a=p.parse_args()
    CACHE.mkdir(exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    if a.action=='prepare':
        tasks=[(str(i),s) for i in range(1,21) for s in (11,29,47)]
        with ProcessPoolExecutor(a.workers) as pool:
            for i,r in enumerate(pool.map(prepare_job,tasks),1):print('transport library',i,'/60',r,flush=True)
        (CACHE/'hashes.json').write_text(json.dumps(frozen_hashes(),indent=2),encoding='utf8')
    elif a.action=='run':
        frozen=frozen_hashes()
        if json.loads((CACHE/'hashes.json').read_text())!=frozen:raise ValueError('Source changed after prepare')
        folder=OUT/'transport_tasks';folder.mkdir(exist_ok=True)
        todo=[];rows=[]
        for task in [(str(i),s,b) for i in range(1,21) for s in (11,29,47) for b in (1,2,4)]:
            path=folder/('_'.join(map(str,task))+'.json')
            if path.exists():
                record=json.loads(path.read_text())
                if record['code_sha256']!=frozen:raise ValueError('Checkpoint source mismatch')
                rows.append(record['row'])
            else:todo.append(task)
        with ProcessPoolExecutor(a.workers) as pool:
            for task,r in zip(todo,pool.map(job,todo)):
                rows.append(r);(folder/('_'.join(map(str,task))+'.json')).write_text(json.dumps(dict(code_sha256=frozen,row=r)),encoding='utf8')
                print('transport test',len(rows),'/180',task,flush=True)
        if frozen_hashes()!=frozen:raise ValueError('Source changed during run')
        (OUT/'transport.json').write_text(json.dumps(dict(code_sha256=frozen,rows=rows),indent=2),encoding='utf8');report()
    else:report()


if __name__=='__main__':main()
