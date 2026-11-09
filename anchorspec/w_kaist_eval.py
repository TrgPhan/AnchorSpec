"""Frozen cross-load and held-severity KAIST replay, no independent-bearing claim."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import importlib.util
import json
from pathlib import Path
import time
import numpy as np
from scipy.io import loadmat

from w_kaist import DATA, ROOT
from bearing import Bearing
from cheap_sensor import CheapSensor,simulate,windows
from event_experts import Event,EventExperts,causal_average
from diagnostic_experts import DiagnosticExperts,fault_labels
from source_select import SourceSelector,SOURCES
import funnel as Fu

CACHE=DATA/'features'
OUT=ROOT/'results'/'w'
S=CheapSensor()
ORDERS=Bearing(9,7.90,38.5,0).orders()
FR=3010/60
SEV=('03','10','30')
METHODS=SOURCES+('select','legacy_real','legacy_physics','legacy_surrogate','diagnostic_real_y')


def read_signal(path):
    signal=loadmat(path,simplify_cells=True)['Signal']
    timing=signal['x_values'];q=signal['y_values']['quantity']
    fs=1/float(timing['increment'])
    a=np.asarray(signal['y_values']['values'])
    if abs(fs-25600)>1e-3 or a.ndim!=2 or a.shape[1]!=4 or len(a)!=int(timing['number_of_values']):
        raise ValueError('Unexpected KAIST schema')
    if q['label']!='g' or 'MKS' not in q['info']:
        raise ValueError('Unexpected unit schema')
    factor=float(q['unit_transformation']['factor']);offset=float(q['unit_transformation']['offset'])
    if not np.isclose(factor,1/9.80665,rtol=1e-6) or offset!=0:
        raise ValueError('Unexpected unit conversion')
    x=a[:,0]*factor+offset
    return x,dict(input_storage='MKS',display_unit='g',factor=factor,offset=offset,fs=fs,
                  duration_seconds=len(x)/fs,clip8_fraction=float((np.abs(x)>=8).mean()))


def code_hashes():
    names=('w_kaist_eval.py','PROTOCOL_W_KAIST.md','source_select.py','diagnostic_experts.py',
           'kernel_experts.py','event_experts.py','adaptive_experts.py','features.py','funnel.py','cheap_sensor.py','injection.py')
    d={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}
    d['legacy_generator']=hashlib.sha256((ROOT.parent/'generator_benchmark'/'generators.py').read_bytes()).hexdigest()
    return d


def prepare_file(name):
    path=DATA/name
    x,meta=read_signal(path)
    seed=int(hashlib.sha256(name.encode()).hexdigest()[:8],16)
    sensed=simulate(x[:61*25600],25600,S,np.random.default_rng(seed))[4000:]
    w=windows(sensed,4000)[:,None,:]
    if 'Normal' in name:w=w[:30]
    f=Fu.feats(w,4000,FR,ORDERS)
    np.savez_compressed(CACHE/(path.stem+'.npz'),waveforms=w,features=f)
    return name,meta


def augment(task):
    name,seed=task
    with np.load(CACHE/f'{name}.npz') as data:w=data['waveforms']
    if 'Normal' in name:
        rng=np.random.default_rng([seed,int(name[0]),20261104])
        result={str(c):Fu.feats(Fu.injected(w,kind,150,FR,ORDERS,S,4000,rng),4000,FR,ORDERS) for c,kind in ((1,'inner'),(2,'outer'))}
    else:
        spec=importlib.util.spec_from_file_location('legacy_generator',ROOT.parent/'generator_benchmark'/'generators.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        rng=np.random.default_rng([seed,int(hashlib.sha256(name.encode()).hexdigest()[:8],16)])
        gen=np.stack([module.constrained_surrogate(w[int(rng.integers(len(w))),0],rng) for _ in range(150)])[:,None,:]
        result={'surrogate':Fu.feats(gen,4000,FR,ORDERS)}
    np.savez_compressed(CACHE/f'{name}_{seed}_aug.npz',**result)
    return name,seed


def split_files(source_load,target_load,severity):
    if source_load==target_load:raise ValueError('Loads must differ')
    train=[f'{source_load}Nm_{kind}_{s}' for kind in ('BPFI','BPFO') for s in SEV if s!=severity]
    test=[f'{target_load}Nm_{kind}_{severity}' for kind in ('BPFI','BPFO')]
    assert not {n.split('Nm_')[1] for n in train}&{n.split('Nm_')[1] for n in test}
    return train,test


def job(task):
    source_load,target_load,severity,seed=task
    train,test=split_files(source_load,target_load,severity)
    refs={};healthy={}
    for load in (source_load,target_load):
        with np.load(CACHE/f'{load}Nm_Normal.npz') as f:a=f['features']
        refs[str(load)]=dict(mu=a.mean(0),sd=a.std(0)+1e-9)
        healthy[str(load)]=(a-a.mean(0))/(a.std(0)+1e-9)
    events=[];der={};refmap={'target':refs[str(target_load)]}
    ref=refs[str(source_load)]
    for name in train:
        with np.load(CACHE/f'{name}.npz') as f:a=(f['features']-ref['mu'])/ref['sd']
        label=1 if 'BPFI' in name else 2
        events.append(Event(name,name,label,a));refmap[name]=ref
        with np.load(CACHE/f'{name}_{seed}_aug.npz') as f:der[name]=(f['surrogate']-ref['mu'])/ref['sd']
    ref=refs[str(target_load)]
    with np.load(CACHE/f'{target_load}Nm_Normal_{seed}_aug.npz') as f:
        phy={c:(f[str(c)]-ref['mu'])/ref['sd'] for c in (1,2)}
    model=SourceSelector(seed).fit(events,der,phy,target_id='target',references=refmap)
    previous=DiagnosticExperts(seed,real_only=True).fit(healthy[str(target_load)],phy,events,target_id='target',references=refmap)
    legacy={}
    sur={c:np.concatenate([der[e.event_id][:75] for e in events if e.label==c]) for c in (1,2)}
    for name,kind,syn in (('legacy_real','real',phy),('legacy_physics','hybrid',phy),('legacy_surrogate','hybrid',sur)):
        legacy[name]=EventExperts(kind,seed).fit(healthy[str(target_load)],syn,events,target_id='target')
    row=dict(source_load=source_load,target_load=target_load,severity=severity,seed=seed,train=train,test=test,
             choices=model.choices_,validation=model.validation_,previous_choice=previous.selection_,scores={})
    for name in test:
        with np.load(CACHE/f'{name}.npz') as f:z=(f['features']-ref['mu'])/ref['sd']
        truth=1 if 'BPFI' in name else 2
        for method in METHODS:
            if method in SOURCES+('select',):pred=model.predict(z,method)
            elif method=='diagnostic_real_y':pred=previous.diagnose(z,abnormal_event=True)
            else:pred=fault_labels(causal_average(legacy[method].predict_proba(z)))
            row['scores'].setdefault(method,{})[str(truth)]=dict(recall=float((pred==truth).mean()),
                event_correct=int(np.bincount(pred.clip(0),minlength=5).argmax()==truth),counts=np.bincount(pred.clip(0),minlength=5).tolist())
    return row


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));args=p.parse_args()
    CACHE.mkdir(exist_ok=True)
    if args.action=='prepare':
        manifest=json.loads((DATA/'manifest.json').read_text())
        if len(manifest['members'])!=21:raise ValueError('Incomplete download')
        files=[m['local_file'] for m in manifest['members']]
        metadata={}
        with ProcessPoolExecutor(3) as pool:
            for name,meta in pool.map(prepare_file,files):
                metadata[name]=meta;print('features',name,flush=True)
        (CACHE/'metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf8')
        tasks=[(Path(n).stem,s) for n in files for s in (11,29,47)]
        with ProcessPoolExecutor(4) as pool:
            for i,result in enumerate(pool.map(augment,tasks),1):print('augment',i,'/',len(tasks),flush=True)
        (CACHE/'hashes.json').write_text(json.dumps(code_hashes(),indent=2),encoding='utf8')
    else:
        frozen=code_hashes()
        if json.loads((CACHE/'hashes.json').read_text())!=frozen:raise ValueError('Source changed')
        tasks=[(s,t,v,seed) for s in (0,2,4) for t in (0,2,4) if s!=t for v in SEV for seed in (11,29,47)]
        rows=[]
        with ProcessPoolExecutor(4) as pool:
            for i,r in enumerate(pool.map(job,tasks),1):rows.append(r);print('KAIST test',i,'/',len(tasks),flush=True)
        if code_hashes()!=frozen:raise ValueError('Source changed during run')
        summary={}
        for method in METHODS:
            values=[np.mean([r['scores'][method][c]['recall'] for c in ('1','2')]) for r in rows]
            summary[method]=dict(macro_recall=float(np.mean(values)),
                per_class={c:float(np.mean([r['scores'][method][c]['recall'] for r in rows])) for c in ('1','2')},
                per_target_load={str(t):float(np.mean([np.mean([r['scores'][method][c]['recall'] for c in ('1','2')]) for r in rows if r['target_load']==t])) for t in (0,2,4)})
        (OUT/'kaist.json').write_text(json.dumps(dict(code_sha256=frozen,rows=rows,summary=summary,
            fresh_dataset=True,independent_bearing_claim=False,conditional_on_abnormal=True),indent=2),encoding='utf8')
        print({k:round(v['macro_recall'],4) for k,v in summary.items()},flush=True)


if __name__=='__main__':main()
