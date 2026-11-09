"""Frozen external augmentation checks on KAIST and HUST load transfer."""
import argparse
from collections import Counter,defaultdict
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import hashlib
import importlib.util
import json
import os
from pathlib import Path
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
from scipy.io import loadmat
from bearing import Bearing
from cheap_sensor import CheapSensor,simulate,windows
from event_experts import causal_average
from diagnostic_experts import fault_labels
from source_select import FaultModel
from measured_transport import generate
import funnel as Fu
from w_kaist_eval import split_files,ORDERS as KO,FR as KF

ROOT=Path(__file__).resolve().parent
CACHE=ROOT.parent/'data'/'v_external'
OUT=ROOT/'results'/'v'
METHODS=('real','duplicate','surrogate','severity','transport','transport_mix')
FAMILIES=('svm1','svm10','rf')
GEO={5:(25,52,7.8,9),6:(30,62,9.,9),7:(35,72,11.,9),8:(40,80,12.,9)}


def hashes():
    paths=[ROOT/n for n in ('v_external.py','PROTOCOL_V_EXTERNAL.md','measured_transport.py','features.py','source_select.py','cheap_sensor.py','event_experts.py','diagnostic_experts.py','w_kaist_eval.py')]
    paths.append(ROOT.parent/'generator_benchmark'/'generators.py')
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


@lru_cache(None)
def signals(dataset,unit):
    out={};metadata={}
    if dataset=='kaist':
        directory=ROOT.parent/'data'/'kaist_w'/'features'
        for p in directory.glob('*.npz'):
            if '_aug' in p.stem:continue
            with np.load(p) as f:
                if 'waveforms' not in f.files:continue
                out[p.stem]=dict(w=f['waveforms'][:,0],f=f['features'],fr=KF,orders=KO)
    else:
        for p in sorted((ROOT.parent/'data'/'hust_v').glob('*.mat')):
            d=loadmat(p,simplify_cells=True);x=np.asarray(d['data'],float).ravel()
            if len(x)!=512000:raise ValueError('Unexpected stationary duration')
            x=x/(9.80665 if unit=='mks' else 1.)
            seed=int(hashlib.sha256(p.name.encode()).hexdigest()[:8],16)
            y=simulate(x,51200,CheapSensor(),np.random.default_rng(seed))
            # Healthy first6s, keeping seconds1..6; fault seconds1..10.
            y=y[4000:24000] if p.stem.startswith('N') else y[4000:]
            w=windows(y,4000);w=w-w.mean(1,keepdims=True)
            a,b,diam,n=GEO[int(p.stem[1])];orders=Bearing(n,diam,(a+b)/2,0).orders()
            out[p.stem]=dict(w=w,f=Fu.feats(w[:,None,:],4000,float(d['fs']),orders),fr=float(d['fs']),orders=orders)
            metadata[p.stem]=dict(native_clip8_fraction=float((np.abs(x)>=8).mean()),shaft_hz=float(d['fs']))
    return out,metadata


def healthy_name(dataset,name):
    return name.split('Nm_')[0]+'Nm_Normal' if dataset=='kaist' else 'N'+name[1:]


@lru_cache(None)
def surrogate(dataset,unit,name,seed):
    if dataset=='kaist':
        with np.load(ROOT.parent/'data'/'kaist_w'/'features'/f'{name}_{seed}_aug.npz') as f:return f['surrogate'][:64]
    path=CACHE/f'surrogate_{dataset}_{unit}_{name}_{seed}.npz'
    if path.exists():
        with np.load(path) as f:return f['features']
    spec=importlib.util.spec_from_file_location('legacy_generator',ROOT.parent/'generator_benchmark'/'generators.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    row=signals(dataset,unit)[0][name];rng=np.random.default_rng([seed,int(hashlib.sha256(name.encode()).hexdigest()[:8],16)])
    x=np.stack([module.constrained_surrogate(row['w'][int(rng.integers(len(row['w'])))],rng) for _ in range(64)])
    f=Fu.feats(x[:,None,:],4000,row['fr'],row['orders'])
    # Same file can be requested by concurrent transfers; atomic replace.
    temp=path.with_name(path.stem+f'.{os.getpid()}.npz');np.savez_compressed(temp,features=f);temp.replace(path)
    return f


def arrays(healthy,real,aug,method):
    counts=Counter(c for c,x in real);groups=[(0,healthy,1.)]
    for i,(c,x) in enumerate(real):
        groups.append((c,x,(1. if method=='real' else .5)/counts[c]))
        if method!='real':groups.append((c,x.copy() if method=='duplicate' else aug[i][method][:64//counts[c]],.5/counts[c]))
    x=np.concatenate([a for c,a,w in groups]);y=np.concatenate([np.full(len(a),c,int) for c,a,w in groups])
    w=np.concatenate([np.full(len(a),mass/len(a)) for c,a,mass in groups])
    w*=(len(healthy)+sum(len(a) for c,a in real))/w.sum()
    return x,y,w


def job(task):
    dataset,unit,geometry,source,target,severity,seed=task
    data,meta=signals(dataset,unit)
    if dataset=='kaist':
        train,test=split_files(source,target,severity);hn=f'{target}Nm_Normal'
        label=lambda n:1 if 'BPFI' in n else 2
    else:
        train=[f'{c}{geometry}0{source}' for c in 'IOB'];test=[f'{c}{geometry}0{target}' for c in 'IOB'];hn=f'N{geometry}0{target}'
        label=lambda n:'NIOB'.index(n[0])
    assert not set(train)&set(test)
    ht=data[hn];real=[];aug=[];lineage=[]
    for name in train:
        item=data[name];hs=data[healthy_name(dataset,name)]
        rng=np.random.default_rng([seed,int(hashlib.sha256((name+hn+unit).encode()).hexdigest()[:8],16)])
        waves,audit=generate(item['w'],hs['w'],ht['w'],item['fr'],ht['fr'],rng)
        features={m:Fu.feats(w[:,None,:],4000,item['fr'] if m=='severity' else ht['fr'],item['orders']) for m,w in waves.items()}
        features['surrogate']=surrogate(dataset,unit,name,seed)
        real.append((label(name),item['f']));aug.append(features)
        lineage.append(dict(donor=name,target_healthy=hn,clipping=audit['clipping']))
    row=dict(dataset=dataset,unit=unit,geometry=geometry,source=source,target=target,severity=severity,seed=seed,
             train=train,test=test,target_healthy=hn,lineage=lineage,scores={})
    # Target fault features evaluated with HEALTHY target speed metadata only.
    tests={name:Fu.feats(data[name]['w'][:,None,:],4000,ht['fr'],data[name]['orders']) for name in test}
    for family in FAMILIES:
        row['scores'][family]={}
        for method in METHODS:
            model=FaultModel(family,seed).fit(*arrays(ht['f'],real,aug,method))
            row['scores'][family][method]={}
            for name,x in tests.items():
                pred=fault_labels(causal_average(model.predict_proba(x)));c=label(name)
                row['scores'][family][method][str(c)]=dict(recall=float((pred==c).mean()),counts=np.bincount(pred.clip(0),minlength=5).tolist())
    return row


def main():
    p=argparse.ArgumentParser();p.add_argument('dataset',choices=('kaist','hust'));p.add_argument('--workers',type=int,default=2);a=p.parse_args()
    CACHE.mkdir(parents=True,exist_ok=True);OUT.mkdir(exist_ok=True)
    frozen=hashes();saved=CACHE/'hashes.json'
    if saved.exists() and json.loads(saved.read_text())!=frozen:raise ValueError('Source changed after freeze')
    saved.write_text(json.dumps(frozen,indent=2),encoding='utf8')
    if a.dataset=='kaist':tasks=[('kaist','metadata',None,s,t,v,seed) for s in (0,2,4) for t in (0,2,4) if s!=t for v in ('03','10','30') for seed in (11,29,47)]
    else:tasks=[('hust',u,g,s,t,None,seed) for u in ('g','mks') for g in (5,6,7,8) for s in (0,2,4) for t in (0,2,4) if s!=t for seed in (11,29,47)]
    folder=OUT/'external_tasks';folder.mkdir(exist_ok=True);rows=[];todo=[]
    def path(task):return folder/('_'.join(map(str,task))+'.json')
    for t in tasks:
        if path(t).exists():
            previous=json.loads(path(t).read_text())
            if previous['code_sha256']!=frozen:raise ValueError('Checkpoint source mismatch')
            rows.append(previous['row'])
        else:todo.append(t)
    with ProcessPoolExecutor(a.workers) as pool:
        for t,r in zip(todo,pool.map(job,todo)):
            rows.append(r);path(t).write_text(json.dumps(dict(code_sha256=frozen,row=r)),encoding='utf8')
            print(a.dataset,len(rows),'/',len(tasks),t[1:],flush=True)
    if hashes()!=frozen:raise ValueError('Source changed during run')
    summary={}
    for unit in sorted({r['unit'] for r in rows}):
        selected=[r for r in rows if r['unit']==unit];summary[unit]={}
        for family in FAMILIES:
            summary[unit][family]={}
            for method in METHODS:
                byclass=defaultdict(list)
                for r in selected:
                    for c,v in r['scores'][family][method].items():byclass[c].append(v['recall'])
                perclass={c:float(np.mean(v)) for c,v in byclass.items()}
                summary[unit][family][method]=dict(macro_recall=float(np.mean(list(perclass.values()))),per_class=perclass)
            print(unit,family,{m:round(v['macro_recall'],4) for m,v in summary[unit][family].items()},flush=True)
    metadata={u:signals(a.dataset,u)[1] for u in summary}
    (OUT/f'{a.dataset}_transport.json').write_text(json.dumps(dict(code_sha256=frozen,rows=rows,summary=summary,signal_metadata=metadata,
        primary_classifier='svm1',independent_bearing_claim=False,conditional_diagnosis=True),indent=2),encoding='utf8')


if __name__=='__main__':main()
