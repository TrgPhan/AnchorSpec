"""A fixed spectral-residual hypothesis after W, all negative controls retained."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import hashlib
import json
import numpy as np
from scipy import signal,stats
from adaptive_experts import event_folds
from event_experts import causal_average
from source_select import FaultModel,FAMILIES,training_arrays
from y_run import ROOT,load_store,donors
import e8_uored as U

CACHE=ROOT.parent/'data'/'w_spectral'
OUT=ROOT/'results'/'w'


def spectral(x):
    a=np.asarray(x,float);a=a-a.mean(1,keepdims=True)
    _,p=signal.welch(a,4000,nperseg=1024,axis=1)
    p=p[:,1:257].reshape(len(a),128,2).sum(2)
    p=np.log(p/(p.sum(1,keepdims=True)+1e-30)+1e-12)
    filtered=signal.sosfiltfilt(signal.butter(4,(300,1000),fs=4000,btype='bandpass',output='sos'),a,axis=1)
    env=np.abs(signal.hilbert(filtered,axis=1))
    _,q=signal.welch(env,4000,nperseg=1024,axis=1)
    q=q[:,1:129].reshape(len(a),64,2).sum(2)
    q=np.log(q/(q.sum(1,keepdims=True)+1e-30)+1e-12)
    rms=np.sqrt((a*a).mean(1))+1e-15
    return np.column_stack((p,q,np.abs(a).max(1)/rms,stats.kurtosis(a,axis=1),stats.skew(a,axis=1),rms/(np.abs(a).mean(1)+1e-15)))


def prepare(name):
    U.ALLOW_FAULT['on']=True;i=int(name)
    base,hold,fr=U.machine(i,U.SENSORS['1k'])
    early,late=[U.windows50(U.sensed(i,s,U.SENSORS['1k']),4000) for s in (1,2)]
    np.savez_compressed(CACHE/f'{name}.npz',**{k:spectral(v[:,0]) for k,v in dict(base=base,hold=hold,early=early,late=late).items()})
    return name


def signatures():
    return {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in
            ('w_spectral.py','PROTOCOL_W_SPECTRAL.md','source_select.py','y_run.py','e8_uored.py','cheap_sensor.py','features.py')}


def job(task):
    target,seed,budget=task
    store=load_store();spec={}
    for name in store:
        with np.load(CACHE/f'{name}.npz') as f:spec[name]={k:f[k] for k in f.files}
    stream=donors(store,target,seed)
    events=[e for c in range(1,5) for e in [v for v in stream if v.label==c][:budget]]
    folds=event_folds(events) if budget>1 else []
    configs=[];models={};transformed={}
    for view in ('original','spectral','combined'):
        for rep in ('raw','delta'):
            def convert(name,state):
                item=store[name];o=item[state]*item['sd']+item['mu'];s=spec[name][state]
                if rep=='delta':o=o-item['mu'];s=s-spec[name]['base'].mean(0)
                return o if view=='original' else s if view=='spectral' else np.column_stack((o,s))
            ev=[replace(e,features=convert(e.bearing_id,'late')) for e in events]
            transformed[(view,rep)]=(ev,{st:convert(target,st) for st in ('early','late')})
            for family in FAMILIES:
                scores=[]
                for fold in folds:
                    ids={e.event_id for e in fold}
                    train=[e for e in ev if e.event_id not in ids]
                    m=FaultModel(family,seed).fit(*training_arrays(train,{}, {},'real'))
                    for e in ev:
                        if e.event_id in ids:scores.append(float((causal_average(m.predict_proba(e.features)).argmax(1)==e.label).mean()))
                configs.append(dict(view=view,representation=rep,family=family,score=float(np.mean(scores)) if scores else None))
    def key(r):return(r['score'],-('original','spectral','combined').index(r['view']),-FAMILIES.index(r['family']),-('raw','delta').index(r['representation']))
    choices={}
    for view in ('original','spectral','combined'):
        choices[view]=max([r for r in configs if r['view']==view],key=key) if folds else dict(view=view,representation='raw',family='svm1',score=None)
    choices['select']=max(configs,key=key) if folds else choices['original']
    label=('healthy','inner','outer','ball','cage').index(store[target]['lab'])
    out=dict(target=target,seed=seed,budget=budget,label=label,control='clean',donor_events=[e.event_id for e in events],choices=choices,validation=configs,scores={})
    for name,choice in choices.items():
        ev,test=transformed[(choice['view'],choice['representation'])]
        m=FaultModel(choice['family'],seed).fit(*training_arrays(ev,{}, {},'real'))
        out['scores'][name]={}
        for state in ('early','late'):
            pred=causal_average(m.predict_proba(test[state])).argmax(1)
            out['scores'][name][state]=dict(recall=float((pred==label).mean()),pred_counts=np.bincount(pred,minlength=5).tolist())
    return out


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));a=p.parse_args()
    CACHE.mkdir(exist_ok=True)
    if a.action=='prepare':
        with ProcessPoolExecutor(4) as pool:
            for n in pool.map(prepare,[str(i) for i in range(1,21)]):print('spectral features',n,flush=True)
        (CACHE/'hashes.json').write_text(json.dumps(signatures()),encoding='utf8')
    else:
        frozen=signatures()
        if json.loads((CACHE/'hashes.json').read_text())!=frozen:raise ValueError('Code changed')
        rows=[];tasks=[(str(i),s,b) for i in range(1,21) for s in (11,29,47) for b in (1,2,4)]
        with ProcessPoolExecutor(4) as pool:
            for i,r in enumerate(pool.map(job,tasks),1):
                rows.append(r)
                if i%20==0:print('spectral',i,'/180',flush=True)
        if frozen!=signatures():raise ValueError('Code changed during run')
        (OUT/'spectral.json').write_text(json.dumps(dict(code_sha256=frozen,exploratory=True,rows=rows),indent=2),encoding='utf8')
        for b in (1,2,4):print(b,{m:round(float(np.mean([r['scores'][m]['late']['recall'] for r in rows if r['budget']==b])),4) for m in ('original','spectral','combined','select')},flush=True)


if __name__=='__main__':main()
