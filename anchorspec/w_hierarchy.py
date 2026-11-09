"""Fixed real-event hierarchy separating ring and rolling-element/cage experts."""
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import hashlib
import json
import numpy as np
from diagnostic_experts import DiagnosticExperts
from event_experts import CLASSES,causal_average
from y_run import ROOT,load_store,donors

OUT=ROOT/'results'/'w'


def normalize_fault(p):
    a=np.asarray(p)[:,1:3]
    den=a.sum(1,keepdims=True)
    return np.divide(a,den,out=np.full_like(a,.5),where=den>0)


def combine(group,ring,other):
    g,r,o=[normalize_fault(p) for p in (group,ring,other)]
    out=np.zeros((len(g),5));out[:,1:3]=g[:,0,None]*r;out[:,3:5]=g[:,1,None]*o
    return out


def job(task):
    target,seed=task;store=load_store();extended={};refs={};original_refs={}
    for n,item in store.items():
        with np.load(ROOT.parent/'data'/'w_amplitude'/f'{n}.npz') as a,np.load(ROOT.parent/'data'/'w_spectral'/f'{n}.npz') as s:
            ext={k:np.column_stack((s[k],a[k])) for k in ('base','early','late')}
        mu=ext['base'].mean(0);sd=ext['base'].std(0)+1e-9
        extended[n]={k:np.column_stack((item[k],(ext[k]-mu)/sd)) for k in ext}
        refs[n]=dict(mu=np.r_[item['mu'],mu],sd=np.r_[item['sd'],sd])
        original_refs[n]=dict(mu=item['mu'],sd=item['sd'])
    stream=donors(store,target,seed)
    events=[e for c in range(1,5) for e in [v for v in stream if v.label==c][:4]]
    group_ev=[replace(e,label=1 if e.label in (1,2) else 2,features=extended[e.bearing_id]['late']) for e in events]
    other_ev=[replace(e,label=e.label-2,features=extended[e.bearing_id]['late']) for e in events if e.label in (3,4)]
    ring_ev=[e for e in events if e.label in (1,2)]
    group=DiagnosticExperts(seed,True).fit(extended[target]['base'],{},group_ev,target_id=target,references=refs)
    ring=DiagnosticExperts(seed,True).fit(store[target]['base'],{},ring_ev,target_id=target,references=original_refs)
    other=DiagnosticExperts(seed,True).fit(extended[target]['base'],{},other_ev,target_id=target,references=refs)
    label=CLASSES.index(store[target]['lab'])
    result=dict(target=target,seed=seed,budget=4,label=label,control='clean',donor_events=[e.event_id for e in events],
                selection=dict(group=group.selection_,ring=ring.selection_,other=other.selection_),scores={'hierarchy':{}})
    for state in ('early','late'):
        p=combine(group.predict_proba(extended[target][state]),ring.predict_proba(store[target][state]),other.predict_proba(extended[target][state]))
        pred=causal_average(p).argmax(1)
        result['scores']['hierarchy'][state]=dict(recall=float((pred==label).mean()),pred_counts=np.bincount(pred,minlength=5).tolist())
    return result


def main():
    names=('w_hierarchy.py','PROTOCOL_W_HIERARCHY.md','diagnostic_experts.py','adaptive_experts.py','kernel_experts.py')
    signature=lambda:{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}
    frozen=signature();rows=[]
    with ProcessPoolExecutor(4) as pool:
        for i,r in enumerate(pool.map(job,[(str(n),seed) for n in range(1,21) for seed in (11,29,47)]),1):
            rows.append(r)
            if i%10==0:print('hierarchy',i,'/60',flush=True)
    if frozen!=signature():raise ValueError('Code changed during run')
    (OUT/'hierarchy.json').write_text(json.dumps(dict(code_sha256=frozen,exploratory=True,rows=rows),indent=2),encoding='utf8')
    print({state:float(np.mean([r['scores']['hierarchy'][state]['recall'] for r in rows])) for state in ('early','late')},flush=True)


if __name__=='__main__':main()
