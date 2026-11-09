"""Joint-axis generator ablation across declared sensor ranges."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import hashlib
import importlib.util
import json
import numpy as np
from cheap_sensor import CheapSensor,simulate
from joint_surrogate import generate
from tn2b_xjtu import cross_features
import u_natural as U

CACHE=U.DATA/'joint'
METHODS=('real','duplicate','surrogate','independent_phase','joint_phase')
RANGES=(8,16,64)


def features(x,fr):return np.column_stack((U.Fu.feats(x,4000,fr,U.ORDERS),cross_features(x)))


def hashes():
    result=U.hashes()
    for n in ('u_joint.py','joint_surrogate.py','PROTOCOL_U_JOINT.md','tn2b_xjtu.py'):
        result[n]=hashlib.sha256((U.ROOT/n).read_bytes()).hexdigest()
    return result


def prepare(task):
    name,limit=task;manifest=json.loads((U.DATA/'manifest.json').read_text());arrays={};fr={'1':35.,'2':37.5,'3':40.}[name[0]]
    sensor=CheapSensor(range_g=limit);meta=[]
    for stage in ('healthy','preterminal','terminal'):
        rows=sorted([r for r in manifest['members'] if r['bearing']==name and r['stage']==stage],key=lambda r:r['index']);pairs=[]
        if len(rows)!=10:raise ValueError('Missing snapshots')
        for r in rows:
            p=U.DATA/name/r['local_file']
            if hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Raw data changed')
            raw=np.loadtxt(p,delimiter=',',skiprows=1).T
            rng=np.random.default_rng([int(name[0]),int(name[-1]),r['index'],20261105])
            sensed=simulate(raw,25600,sensor,rng)[:,560:4560]
            pairs.append(sensed);meta.append(dict(stage=stage,index=r['index'],native_clipping=[float((np.abs(a)>=limit).mean()) for a in raw]))
        arrays[stage]=np.stack(pairs);arrays[stage+'_features']=features(arrays[stage],fr)
    np.savez_compressed(CACHE/f'{name}_{limit}.npz',fr=fr,**arrays)
    return f'{name}_{limit}',meta


@lru_cache(None)
def bearing(name,limit):
    with np.load(CACHE/f'{name}_{limit}.npz') as f:return {k:f[k] for k in f.files}


def prepare_aug(task):
    name,limit,seed=task;s=bearing(name,limit);sensor=CheapSensor(range_g=limit)
    waves,meta=generate(s['terminal'],np.random.default_rng([seed,int(name[0]),int(name[-1]),91]),sensor)
    spec=importlib.util.spec_from_file_location('legacy_generator',U.ROOT.parent/'generator_benchmark/generators.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rng=np.random.default_rng([seed,int(name[0]),int(name[-1]),92]);old=[]
    for index in meta['source_indices']:
        old.append(np.stack([module.constrained_surrogate(a,rng) for a in s['terminal'][index]]))
    waves['surrogate']=np.stack(old)
    np.savez_compressed(CACHE/f'{name}_{limit}_{seed}_aug.npz',**{m:features(x,float(s['fr'])) for m,x in waves.items()})
    return dict(bearing=name,seed=seed,**meta)


def job(task):
    target,limit,seed=task;t=bearing(target,limit);events=[];der={}
    for name in U.LABEL:
        if name==target:continue
        s=bearing(name,limit);events.append((name,U.LABEL[name],s['terminal_features']))
        with np.load(CACHE/f'{name}_{limit}_{seed}_aug.npz') as f:der[name]={m:f[m] for m in f.files}
    row=dict(target=target,seed=seed,label=U.LABEL[target],range_g=limit,budget=limit,control='clean',
        donors=[n for n,c,x in events],scores={})
    for family in ('rf','svm1','svm10'):
        reference={}
        for method in METHODS:
            # U.training dispatch only checks method names; build arrays here to
            # avoid mutating the frozen registry used by the primary experiment.
            from collections import Counter
            counts=Counter(c for n,c,x in events);groups=[(0,t['healthy_features'],1.)]
            for n,c,x in events:
                groups.append((c,x,(1. if method=='real' else .75)/counts[c]))
                if method!='real':groups.append((c,x.copy() if method=='duplicate' else der[n][method][:64//counts[c]],.25/counts[c]))
            x=np.concatenate([a for c,a,m in groups]);y=np.concatenate([np.full(len(a),c,int) for c,a,m in groups])
            w=np.concatenate([np.full(len(a),m/len(a)) for c,a,m in groups]);w*=130/w.sum()
            model=U.InvariantClassifier(family,seed).fit(x,y,w);key=f'{family}:{method}';row['scores'][key]={}
            for state,stage in (('early','preterminal'),('late','terminal')):
                p=model.predict_proba(t[stage+'_features']);pred=U.fault_labels(U.causal_average(p))
                if method=='real':reference[state]=p
                elif method=='duplicate':np.testing.assert_array_equal(reference[state],p)
                row['scores'][key][state]=dict(recall=float((pred==U.LABEL[target]).mean()),
                    prediction_counts={str(c):int((pred==c).sum()) for c in (-1,0,1,2,3,4)})
    return row


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));a=p.parse_args();CACHE.mkdir(exist_ok=True);frozen=hashes()
    if a.action=='prepare':
        with ProcessPoolExecutor(4) as pool:meta=dict(pool.map(prepare,[(n,r) for n in U.LABEL for r in RANGES]))
        (CACHE/'signal_metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
        aug=[]
        with ProcessPoolExecutor(4) as pool:
            for i,r in enumerate(pool.map(prepare_aug,[(n,r,s) for n in U.LABEL for r in RANGES for s in (11,29,47)]),1):
                aug.append(r)
                if i%15==0:print('Joint library',i,'/117',flush=True)
        (CACHE/'augmentation_metadata.json').write_text(json.dumps(aug),encoding='utf8')
        if hashes()!=frozen:raise ValueError('Source changed')
        (CACHE/'hashes.json').write_text(json.dumps(frozen),encoding='utf8');return
    if json.loads((CACHE/'hashes.json').read_text())!=frozen:raise ValueError('Source changed since prepare')
    rows=[];folder=U.OUT/'joint_tasks';folder.mkdir(exist_ok=True);todo=[]
    for t in [(n,r,s) for n in U.LABEL for r in RANGES for s in (11,29,47)]:
        path=folder/('_'.join(map(str,t))+'.json')
        if path.exists():
            record=json.loads(path.read_text())
            if record['code_sha256']!=frozen:raise ValueError('Checkpoint mismatch')
            rows.append(record['row'])
        else:todo.append(t)
    with ProcessPoolExecutor(4) as pool:
        for t,row in zip(todo,pool.map(job,todo)):
            rows.append(row);(folder/('_'.join(map(str,t))+'.json')).write_text(json.dumps(dict(row=row,code_sha256=frozen)),encoding='utf8')
            if len(rows)%10==0:print('Joint benchmark',len(rows),'/117',flush=True)
    summary={}
    for limit in RANGES:
        summary[str(limit)]={}
        for family in ('rf','svm1','svm10'):
            summary[str(limit)][family]={}
            for method in METHODS:
                summary[str(limit)][family][method]={}
                for state in ('early','late'):
                    vals=U.bearing_values(rows,f'{family}:{method}','recall',budget=limit,state=state)
                    summary[str(limit)][family][method][state]=dict(macro_recall=U.macro(vals),per_class={str(c):U.macro({k:v for k,v in vals.items() if k[1]==c}) for c in (1,2,4)},
                        differences={m:U.paired_delta(vals,U.bearing_values(rows,f'{family}:{m}','recall',budget=limit,state=state)) for m in ('real','surrogate','independent_phase')})
            print(limit,family,{m:round(v['late']['macro_recall'],4) for m,v in summary[str(limit)][family].items()},flush=True)
    main=summary['8']['rf']['joint_phase'];base=summary['8']['rf']['real']
    gate=dict(gain5pp_real=main['late']['differences']['real']['delta']>=.05,gain5pp_legacy=main['late']['differences']['surrogate']['delta']>=.05,
        positive_ci=main['late']['differences']['real']['ci95'][0]>0,no_class_loss5pp=min(main['late']['per_class'][c]-base['late']['per_class'][c] for c in ('1','2','4'))>=-.05,
        no_preterminal_loss2pp=main['early']['differences']['real']['delta']>=-.02)
    if hashes()!=frozen:raise ValueError('Source changed during run')
    (U.OUT/'joint.json').write_text(json.dumps(dict(rows=rows,summary=summary,code_sha256=frozen,primary_checks=gate,primary_passed=all(gate.values()),
        duplicate_predictions_identical=True,exploratory=True),indent=2),encoding='utf8')


if __name__=='__main__':main()
