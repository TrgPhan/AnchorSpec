"""Frozen bearing-held-out natural-fault generator benchmark on XJTU-SY."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
from bearing import Bearing
from cheap_sensor import CheapSensor,simulate
from invariant_classifier import InvariantClassifier
from event_experts import causal_average
from diagnostic_experts import fault_labels
from measured_transport import generate as transport
from envelope_surrogate import generate as envelope
from y_metrics import bearing_values,macro,paired_delta
from u_download import ROOT,DATA,LABEL
import funnel as Fu

CACHE=DATA/'prepared'
OUT=ROOT/'results/u'
ORDERS=Bearing(8,7.92,34.55,0).orders()
FAMILIES=('svm1','svm10','rf')
METHODS=('real','duplicate','surrogate','envelope','severity','transport','transport_mix')


def hashes():
    paths=[ROOT/n for n in ('u_natural.py','PROTOCOL_U_NATURAL.md','invariant_classifier.py','u_download.py',
        'measured_transport.py','envelope_surrogate.py','cheap_sensor.py','features.py','funnel.py','bearing.py',
        'event_experts.py','diagnostic_experts.py','y_metrics.py')]
    paths.append(ROOT.parent/'generator_benchmark/generators.py')
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def prepare_bearing(name):
    manifest=json.loads((DATA/'manifest.json').read_text())
    members=sorted([r for r in manifest['members'] if r['bearing']==name],key=lambda r:r['index'])
    if len(members)!=30:raise ValueError('Incomplete acquisition')
    arrays={};metadata=[];fr={'1':35.,'2':37.5,'3':40.}[name[0]]
    for stage in ('healthy','preterminal','terminal'):
        waves=[]
        for row in [r for r in members if r['stage']==stage]:
            path=DATA/name/row['local_file']
            if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Local raw checksum changed')
            x=np.loadtxt(path,delimiter=',',skiprows=1)
            if x.shape!=(32768,2) or not np.isfinite(x).all():raise ValueError('Unexpected XJTU waveform')
            rng=np.random.default_rng([int(name[0]),int(name[-1]),row['index'],20261105])
            sensed=simulate(x[:,0],25600,CheapSensor(),rng)
            w=sensed[560:4560];w=w-w.mean();waves.append(w)
            metadata.append(dict(index=row['index'],stage=stage,horizontal_clip8_fraction=float((np.abs(x[:,0])>=8).mean()),
                vertical_clip8_fraction=float((np.abs(x[:,1])>=8).mean()),horizontal_peak_g=float(np.abs(x[:,0]).max())))
        if len(waves)!=10:raise ValueError('Unexpected stage size')
        arrays[stage]=np.stack(waves);arrays[stage+'_features']=Fu.feats(arrays[stage][:,None,:],4000,fr,ORDERS)
    np.savez_compressed(CACHE/f'{name}.npz',fr=fr,**arrays)
    return name,metadata


@lru_cache(None)
def bearing(name):
    with np.load(CACHE/f'{name}.npz') as f:return {k:f[k] for k in f.files}


def prepare_surrogate(task):
    name,seed=task;data=bearing(name);rng=np.random.default_rng([seed,int(name[0]),int(name[-1]),8])
    spec=importlib.util.spec_from_file_location('legacy_generator',ROOT.parent/'generator_benchmark/generators.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    old=np.stack([module.constrained_surrogate(data['terminal'][int(rng.integers(10))],rng) for _ in range(64)])
    new,meta=envelope(data['terminal'],np.random.default_rng([seed,int(name[0]),int(name[-1]),9]))
    np.savez_compressed(CACHE/f'{name}_{seed}_aug.npz',
        surrogate=Fu.feats(old[:,None,:],4000,float(data['fr']),ORDERS),
        envelope=Fu.feats(new[:,None,:],4000,float(data['fr']),ORDERS))
    return dict(bearing=name,seed=seed,envelope_clipping=meta['clipping_fraction'])


def training(healthy,events,derivatives,method,mass=.25):
    if method not in METHODS:raise ValueError('Unknown method')
    counts=Counter(c for name,c,x in events);groups=[(0,healthy,1.)]
    for name,c,x in events:
        portion=1. if method=='real' else 1-mass
        groups.append((c,x,portion/counts[c]))
        if method!='real':
            generated=x.copy() if method=='duplicate' else derivatives[name][method][:64//counts[c]]
            groups.append((c,generated,mass/counts[c]))
    x=np.concatenate([a for c,a,m in groups]);y=np.concatenate([np.full(len(a),c,int) for c,a,m in groups])
    w=np.concatenate([np.full(len(a),m/len(a)) for c,a,m in groups]);w*=(len(healthy)+sum(len(a) for n,c,a in events))/w.sum()
    return x,y,w


def job(task):
    target,seed=task;start=time.perf_counter();t=bearing(target);events=[];der={};lineage=[]
    sources=[n for n in LABEL if n!=target]
    for name in sources:
        s=bearing(name);events.append((name,LABEL[name],s['terminal_features']))
        rng=np.random.default_rng([seed,int(target[0]),int(target[-1]),int(name[0]),int(name[-1]),10])
        wave,meta=transport(s['terminal'],s['healthy'],t['healthy'],float(s['fr']),float(t['fr']),rng)
        der[name]={m:Fu.feats(x[:,None,:],4000,float(s['fr']) if m=='severity' else float(t['fr']),ORDERS) for m,x in wave.items()}
        with np.load(CACHE/f'{name}_{seed}_aug.npz') as f:
            der[name].update({m:f[m] for m in ('surrogate','envelope')})
        lineage.append(dict(donor=name,donor_stage='terminal',target_healthy=target,clipping=meta['clipping']))
    assert target not in {n for n,c,x in events}
    row=dict(target=target,seed=seed,label=LABEL[target],budget=0,control='clean',donors=sources,
        lineage=lineage,scores={},unique_training_rows={},generation_and_features_seconds=time.perf_counter()-start)
    for family in FAMILIES:
        reference={}
        for method in METHODS:
            model=InvariantClassifier(family,seed).fit(*training(t['healthy_features'],events,der,method))
            key=f'{family}:{method}';row['scores'][key]={};row['unique_training_rows'][key]=model.unique_rows_
            for state,stage in (('late','terminal'),('early','preterminal')):
                p=model.predict_proba(t[stage+'_features']);pred=fault_labels(causal_average(p))
                if method=='real':reference[state]=p
                elif method=='duplicate':np.testing.assert_array_equal(reference[state],p,err_msg='Duplicate changed classifier')
                row['scores'][key][state]=dict(recall=float((pred==LABEL[target]).mean()),
                    prediction_counts={str(c):int((pred==c).sum()) for c in (-1,0,1,2,3,4)})
    row['elapsed_seconds']=time.perf_counter()-start
    return row


def report(rows):
    summary={}
    for family in FAMILIES:
        summary[family]={}
        for method in METHODS:
            summary[family][method]={}
            for state in ('early','late'):
                vals=bearing_values(rows,f'{family}:{method}','recall',budget=0,state=state)
                summary[family][method][state]=dict(macro_recall=macro(vals),
                    per_class={str(c):macro({k:v for k,v in vals.items() if k[1]==c}) for c in (1,2,4)},
                    differences={base:paired_delta(vals,bearing_values(rows,f'{family}:{base}','recall',budget=0,state=state)) for base in ('real','surrogate')})
        print(family,{m:round(v['late']['macro_recall'],4) for m,v in summary[family].items()},flush=True)
    primary=summary['svm1']['transport'];real=summary['svm1']['real']
    checks=dict(terminal_gain5pp_over_real=primary['late']['differences']['real']['delta']>=.05,
        terminal_gain5pp_over_surrogate=primary['late']['differences']['surrogate']['delta']>=.05,
        no_class_loss5pp=min(primary['late']['per_class'][c]-real['late']['per_class'][c] for c in ('1','2','4'))>=-.05,
        positive_exploratory_ci=primary['late']['differences']['real']['ci95'][0]>0,
        no_preterminal_loss2pp=primary['early']['differences']['real']['delta']>=-.02)
    return summary,dict(checks=checks,passed=all(checks.values()))


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));p.add_argument('--workers',type=int,default=4);a=p.parse_args()
    CACHE.mkdir(exist_ok=True);OUT.mkdir(parents=True,exist_ok=True);frozen=hashes()
    if a.action=='prepare':
        with ProcessPoolExecutor(a.workers) as pool:meta=dict(pool.map(prepare_bearing,LABEL))
        (CACHE/'signal_metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
        with ProcessPoolExecutor(a.workers) as pool:
            augmentation=list(pool.map(prepare_surrogate,[(n,s) for n in LABEL for s in (11,29,47)]))
        (CACHE/'augmentation_metadata.json').write_text(json.dumps(augmentation,indent=2),encoding='utf8')
        if hashes()!=frozen:raise ValueError('Source changed during preparation')
        (CACHE/'hashes.json').write_text(json.dumps(frozen,indent=2),encoding='utf8');print('XJTU prepared',flush=True);return
    if json.loads((CACHE/'hashes.json').read_text())!=frozen:raise ValueError('Source changed since prepare')
    folder=OUT/'tasks';folder.mkdir(exist_ok=True);rows=[];todo=[]
    for t in [(n,s) for n in LABEL for s in (11,29,47)]:
        path=folder/f'{t[0]}_{t[1]}.json'
        if path.exists():
            previous=json.loads(path.read_text())
            if previous['code_sha256']!=frozen:raise ValueError('Checkpoint mismatch')
            rows.append(previous['row'])
        else:todo.append(t)
    with ProcessPoolExecutor(a.workers) as pool:
        for t,row in zip(todo,pool.map(job,todo)):
            rows.append(row);(folder/f'{t[0]}_{t[1]}.json').write_text(json.dumps(dict(row=row,code_sha256=frozen)),encoding='utf8')
            print('Natural benchmark',len(rows),'/39',t,flush=True)
    summary,gate=report(rows)
    if hashes()!=frozen:raise ValueError('Source changed during run')
    result=dict(rows=rows,summary=summary,primary_gate=gate,duplicate_predictions_identical=True,code_sha256=frozen,
        conditional_diagnosis=True,healthy_reference_assumed=True,primary_stage='terminal',primary_classifier='svm1',primary_generator='transport')
    (OUT/'natural.json').write_text(json.dumps(result,indent=2),encoding='utf8')


if __name__=='__main__':main()
