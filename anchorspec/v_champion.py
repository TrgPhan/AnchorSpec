"""Augmentation around the frozen strong Y model; no new outer-test selection."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import hashlib
import json
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from event_experts import _prob,validate_events
import envelope_surrogate as ES
import v_transport_run as V
from y_metrics import bearing_values,macro,paired_delta

CACHE=V.ROOT.parent/'data/v_envelope'
METHODS=V.METHODS+('envelope',)


class ChampionModel(V.FaultModel):
    def fit(self,x,y,w):
        if self.family!='rf':return super().fit(x,y,w)
        self.model_=RandomForestClassifier(random_state=self.seed,**dict(V.Fu.SMALL,class_weight=None)).fit(x,y,sample_weight=w)
        return self

    def predict_proba(self,x):
        return _prob(self.model_,x,5) if self.family=='rf' else super().predict_proba(x)


def training(target,events,method,rep,mass,seed,family):
    validate_events(events,target);data=V.store();ref=data[target]
    counts=Counter(e.label for e in events)
    h=V.represent(ref['base'],ref,rep)
    groups=[(0,h,1.,1)]
    for e in events:
        origin=data[e.bearing_id];x=V.represent(e.features,origin,rep)
        groups.append((e.label,x,1. if method=='real' else 1-mass,counts[e.label]))
        if method=='real':continue
        if method=='duplicate':a=x.copy()
        else:
            raw=envelope(e.bearing_id,seed) if method=='envelope' else V.generated(target,seed)[f'{e.bearing_id}_{method}']
            origin=ref if method in ('transport','transport_mix') else origin
            a=V.represent((raw-origin['mu'])/origin['sd'],origin,rep)[:64//counts[e.label]]
        groups.append((e.label,a,mass,counts[e.label]))
    x=np.concatenate([a for c,a,m,n in groups]);y=np.concatenate([np.full(len(a),c,int) for c,a,m,n in groups])
    w=np.concatenate([np.full(len(a),m/(n*len(a))) for c,a,m,n in groups])
    true_count=len(h)+sum(len(e.features) for e in events)
    w*=true_count if family=='rf' else true_count/w.sum()
    return x,y,w


def hashes():
    out=V.frozen_hashes()
    for n in ('v_champion.py','envelope_surrogate.py','PROTOCOL_V_ENVELOPE.md'):
        out[n]=hashlib.sha256((V.ROOT/n).read_bytes()).hexdigest()
    out['Y_selection']=hashlib.sha256((V.ROOT/'results/y/diagnostic_balanced.json').read_bytes()).hexdigest()
    return out


def prepare_job(task):
    name,seed=task;item=V.store()[name]
    x,meta=ES.generate(V.waveforms()[name]['fault'],np.random.default_rng([seed,int(name),49]))
    f=V.Fu.feats(x[:,None,:],4000,item['fr'],V.U.ORDERS)
    np.savez_compressed(CACHE/f'{name}_{seed}.npz',features=f)
    return dict(donor=name,seed=seed,**meta)


@lru_cache(None)
def envelope(name,seed):
    with np.load(CACHE/f'{name}_{seed}.npz') as f:return f['features']


def job(old):
    target,seed,budget=old['target'],old['seed'],old['budget'];data=V.store()
    stream=V.donors(data,target,seed);byid={e.event_id:e for e in stream}
    events=[byid[n] for n in old['donor_events']]
    choice=old['selection']['diagnostic_real']['chosen'];family,rep=choice['family'],choice['representation']
    row=dict(target=target,seed=seed,budget=budget,label=old['label'],control='clean',donor_events=old['donor_events'],classifier=choice,scores={})
    for mass in (.25,.5):
        for method in METHODS:
            if method=='real' and mass==.5:continue
            x,y,w=training(target,events,method,rep,mass,seed,family)
            model=ChampionModel(family,seed).fit(x,y,w)
            key='real' if method=='real' else f'{method}_{mass}'
            row['scores'][key]={}
            for state in ('early','late'):
                pred=V.predict(model,target,state,rep)
                counts={str(c):int((pred==c).sum()) for c in (-1,1,2,3,4)}
                if method=='real' and counts!=old['scores']['diagnostic_real'][state]['prediction_counts']:
                    raise ValueError(f'Y baseline mismatch: {target}, {seed}, {budget}, {state}, {family}')
                row['scores'][key][state]=dict(recall=float((pred==old['label']).mean()),prediction_counts=counts)
            row['scores'][key]['both']={'recall':float(np.mean([row['scores'][key][s]['recall'] for s in ('early','late')]))}
    return row


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));a=p.parse_args();CACHE.mkdir(exist_ok=True)
    frozen=hashes()
    if a.action=='prepare':
        with ProcessPoolExecutor(4) as pool:meta=list(pool.map(prepare_job,[(str(n),s) for n in range(1,21) for s in (11,29,47)]))
        (CACHE/'metadata.json').write_text(json.dumps(meta),encoding='utf8');(CACHE/'hashes.json').write_text(json.dumps(frozen),encoding='utf8');print('Envelope cache ready',flush=True);return
    if json.loads((CACHE/'hashes.json').read_text())!=frozen:raise ValueError('Source changed after prepare')
    old=json.loads((V.ROOT/'results/y/diagnostic_balanced.json').read_text())
    tasks=[r for r in old['rows'] if r['control']=='clean'];rows=[]
    with ProcessPoolExecutor(4) as pool:
        for i,r in enumerate(pool.map(job,tasks),1):rows.append(r);print('Y matched augmentation',i,'/',len(tasks),flush=True)
    summary={}
    for budget in (1,2,4):
        summary[str(budget)]={}
        for method in rows[0]['scores']:
            summary[str(budget)][method]={}
            for state in ('early','late','both'):
                vals=bearing_values(rows,method,'recall',budget=budget,state=state)
                base=bearing_values(rows,'real','recall',budget=budget,state=state)
                summary[str(budget)][method][state]=dict(macro_recall=macro(vals),per_class={str(c):macro({k:v for k,v in vals.items() if k[1]==c}) for c in range(1,5)},minus_real=paired_delta(vals,base))
        print(budget,{m:round(v['both']['macro_recall'],4) for m,v in summary[str(budget)].items()},flush=True)
    if hashes()!=frozen:raise ValueError('Source changed during run')
    (V.OUT/'champion_augmentation.json').write_text(json.dumps(dict(rows=rows,summary=summary,code_sha256=frozen,Y_prediction_counts_reproduced=True),indent=2),encoding='utf8')


if __name__=='__main__':main()
