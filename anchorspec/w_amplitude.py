"""Add measurable amplitude context to the real-event Y classifier, no augmentation."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import hashlib
import json
import numpy as np
from diagnostic_experts import DiagnosticExperts
from event_experts import CLASSES
from y_run import ROOT,load_store,donors
import e8_uored as U

CACHE=ROOT.parent/'data'/'w_amplitude'
OUT=ROOT/'results'/'w'
VIEWS=('original','amplitude','spectral_amplitude')


def signature():
    return {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in
        ('w_amplitude.py','PROTOCOL_W_AMPLITUDE.md','diagnostic_experts.py','adaptive_experts.py','kernel_experts.py','e8_uored.py','features.py','cheap_sensor.py')}


def prepare(name):
    U.ALLOW_FAULT['on']=True
    b,h,_=U.machine(int(name),U.SENSORS['1k'])
    states=dict(base=b,hold=h,early=U.windows50(U.sensed(int(name),1,U.SENSORS['1k']),4000),late=U.windows50(U.sensed(int(name),2,U.SENSORS['1k']),4000))
    features={}
    for state,w in states.items():
        x=w[:,0];features[state]=np.column_stack((np.log(np.sqrt((x*x).mean(1))+1e-15),np.log(np.abs(x).max(1)+1e-15)))
    np.savez_compressed(CACHE/f'{name}.npz',**features)
    return name


def job(task):
    target,seed,budget=task;store=load_store();amp={};spec={}
    for n in store:
        with np.load(CACHE/f'{n}.npz') as f:amp[n]={k:f[k] for k in f.files}
        with np.load(ROOT.parent/'data'/'w_spectral'/f'{n}.npz') as f:spec[n]={k:f[k] for k in f.files}
    stream=donors(store,target,seed)
    events=[e for c in range(1,5) for e in [v for v in stream if v.label==c][:budget]]
    out=dict(target=target,seed=seed,budget=budget,label=CLASSES.index(store[target]['lab']),control='clean',donor_events=[e.event_id for e in events],choices={},scores={})
    for view in VIEWS:
        data={};refs={}
        for n,item in store.items():
            if view=='original':
                data[n]={k:item[k] for k in ('base','hold','early','late')};refs[n]=dict(mu=item['mu'],sd=item['sd']);continue
            ext={k:amp[n][k] if view=='amplitude' else np.column_stack((spec[n][k],amp[n][k])) for k in ('base','hold','early','late')}
            mu=ext['base'].mean(0);sd=ext['base'].std(0)+1e-9
            data[n]={k:np.column_stack((item[k],(ext[k]-mu)/sd)) for k in ext}
            refs[n]=dict(mu=np.r_[item['mu'],mu],sd=np.r_[item['sd'],sd])
        ev=[replace(e,features=data[e.bearing_id]['late']) for e in events]
        model=DiagnosticExperts(seed,real_only=True).fit(data[target]['base'],{},ev,target_id=target,references=refs)
        out['choices'][view]=model.selection_;out['scores'][view]={}
        for state in ('early','late'):
            pred=model.diagnose(data[target][state],abnormal_event=True)
            out['scores'][view][state]=dict(recall=float((pred==out['label']).mean()),pred_counts=np.bincount(pred.clip(0),minlength=5).tolist())
    chosen=max(VIEWS,key=lambda v:(out['choices'][v]['score'],-VIEWS.index(v)))
    out['choices']['select']=dict(view=chosen,**out['choices'][chosen]);out['scores']['select']=out['scores'][chosen]
    return out


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));args=p.parse_args();CACHE.mkdir(exist_ok=True)
    if args.action=='prepare':
        with ProcessPoolExecutor(4) as pool:
            for n in pool.map(prepare,[str(i) for i in range(1,21)]):print('amplitude',n,flush=True)
        (CACHE/'hashes.json').write_text(json.dumps(signature()),encoding='utf8')
    else:
        frozen=signature()
        if json.loads((CACHE/'hashes.json').read_text())!=frozen:raise ValueError('Source changed')
        rows=[];tasks=[(str(i),s,b) for i in range(1,21) for s in (11,29,47) for b in (2,4)]
        with ProcessPoolExecutor(4) as pool:
            for i,r in enumerate(pool.map(job,tasks),1):
                rows.append(r)
                if i%20==0:print('amplitude test',i,'/120',flush=True)
        if frozen!=signature():raise ValueError('Source changed during run')
        old=json.loads((ROOT/'results'/'y'/'diagnostic_balanced.json').read_text())
        lookup={(r['target'],r['seed'],r['budget']):r for r in old['rows'] if r['control']=='clean'}
        for r in rows:
            y=lookup[(r['target'],r['seed'],r['budget'])]
            assert r['donor_events']==y['donor_events']
            for state in ('early','late'):
                expected=y['scores']['diagnostic_real'][state]['prediction_counts']
                actual=r['scores']['original'][state]['pred_counts']
                assert all(actual[c]==expected[str(c)] for c in range(1,5))
        (OUT/'amplitude.json').write_text(json.dumps(dict(code_sha256=frozen,original_Y_prediction_counts_reproduced=True,exploratory=True,rows=rows),indent=2),encoding='utf8')
        for b in (2,4):print(b,{m:round(float(np.mean([r['scores'][m]['late']['recall'] for r in rows if r['budget']==b])),4) for m in (*VIEWS,'select')},flush=True)


if __name__=='__main__':main()
