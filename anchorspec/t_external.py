"""Separate the benefit of external measured events from synthetic augmentation."""
import os
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import hashlib
import json
import numpy as np
from u_natural import ROOT,CACHE,LABEL,bearing,training
from t_readiness import OUT,SEEDS,selective,measurements
from t_nested import derivatives,frozen
from invariant_classifier import InvariantClassifier
from event_experts import causal_average
from y_run import load_store
from measured_transport import generate
from y_metrics import macro,paired_delta
import e8_uored as U
import funnel as Fu

DATA=ROOT.parent/'data/t_external';METHODS=('real','duplicate','surrogate','severity')
EXTERNAL=tuple(list(range(1,11))+list(range(16,21)))


def hashes():
    stamp=frozen()
    paths=[ROOT/n for n in ('t_external.py','PROTOCOL_T_EXTERNAL.md','y_run.py','e8_uored.py','x_core.py','w_compare.py')]
    paths += [U.MAT/f'H_{i}_0.mat' for i in EXTERNAL]
    paths += [U.MAT/f'{U.LET[U.LAB[i]]}_{i}_2.mat' for i in EXTERNAL]
    paths += [ROOT.parent/'data/y_cache'/f'bearing_{i}.npz' for i in EXTERNAL]
    paths += [ROOT.parent/'data/w_cache'/f'surrogate_{i}_{s}.npz' for i in EXTERNAL for s in SEEDS]
    paths += [ROOT.parent/'data/t_nested'/f'{n}_{s}.npz' for n in LABEL for s in SEEDS]
    for p in paths:stamp[str(p.relative_to(ROOT.parent)).replace('\\','/')]=hashlib.sha256(p.read_bytes()).hexdigest()
    return stamp


def prepare(i):
    U.ALLOW_FAULT['on']=True;store=load_store();item=store[str(i)]
    healthy,_,fr=U.machine(i,U.SENSORS['1k']);fault=U.windows50(U.sensed(i,2,U.SENSORS['1k']),4000)
    arrays=dict(healthy_features=item['base']*item['sd']+item['mu'],
        terminal_features=item['late']*item['sd']+item['mu'],mu=item['mu'])
    for seed in SEEDS:
        waves,_=generate(fault[:,0,:],healthy[:,0,:],healthy[:,0,:],fr,fr,np.random.default_rng([i,seed,20261105]))
        arrays[f'severity_{seed}']=Fu.feats(waves['severity'][:,None,:],4000,fr,U.ORDERS)
        path=ROOT.parent/'data/w_cache'/f'surrogate_{i}_{seed}.npz'
        with np.load(path) as f:
            # W stores standardized features relative to this donor's healthy reference.
            if str(f['source_event'])!=f'UORED:{i}:2':raise ValueError('Incorrect surrogate donor')
            if str(f['waveform_sha256'])!=hashlib.sha256(fault[:,0,:].tobytes()).hexdigest():raise ValueError('Source waveform changed')
            arrays[f'surrogate_{seed}']=f['features'][:64]*item['sd']+item['mu']
    np.savez_compressed(DATA/f'{i}.npz',**arrays)
    return i


@lru_cache(15)
def external(i):
    with np.load(DATA/f'{i}.npz') as f:return {k:f[k] for k in f.files}


def job(task):
    target,seed=task;t=bearing(target);row=dict(target=target,seed=seed,label=LABEL[target],settings={})
    for representation in ('raw','delta'):
        own=t['healthy_features'][:5].mean(0) if representation=='delta' else 0
        for library in ('xjtu','combined'):
            events=[];derived={};orig=derivatives(target,seed);donors=[]
            for name in LABEL:
                if name==target:continue
                s=bearing(name);mu=s['healthy_features'][:5].mean(0) if representation=='delta' else 0
                key='xjtu:'+name;events.append((key,LABEL[name],s['terminal_features']-mu))
                derived[key]={m:orig[name][m]-mu for m in ('surrogate','severity')};donors.append(key)
            if library=='combined':
                for i in EXTERNAL:
                    s=external(i);mu=s['mu'] if representation=='delta' else 0
                    key='uored:'+str(i);label=1 if i<=5 else 2 if i<=10 else 4
                    events.append((key,label,s['terminal_features']-mu));donors.append(key)
                    derived[key]={m:s[f'{m}_{seed}']-mu for m in ('surrogate','severity')}
            setting=dict(donors=donors,models={});row['settings'][f'{library}:{representation}']=setting;reference={}
            for method in METHODS:
                model=InvariantClassifier('rf',seed).fit(*training(t['healthy_features'][:5]-own,events,derived,method))
                record={};setting['models'][method]=record
                for stage,x in (('healthy',t['healthy_features'][5:]),('preterminal',t['preterminal_features']),('terminal',t['terminal_features'])):
                    p=model.predict_proba(x-own)
                    if method=='real':reference[stage]=p
                    if method=='duplicate':np.testing.assert_array_equal(p,reference[stage])
                    scores=causal_average(p);pred=selective(scores,0)
                    record[stage]=dict(raw_scores=p.tolist(),predictions=pred.tolist(),**measurements(pred,0 if stage=='healthy' else LABEL[target]))
    return row


def aggregate(rows):
    summary={}
    for setting in ('xjtu:raw','combined:raw','xjtu:delta','combined:delta'):
        summary[setting]={}
        for method in METHODS:
            summary[setting][method]={}
            for stage in ('healthy','preterminal','terminal'):
                groups={};false={}
                for r in rows:
                    key=(r['target'],r['label']);v=r['settings'][setting]['models'][method][stage]
                    groups.setdefault(key,[]).append(v['recall']);false.setdefault(key,[]).append(v['fault_claim'])
                vals={k:float(np.mean(v)) for k,v in groups.items()}
                result=dict(recall=float(np.mean(list(vals.values()))) if stage=='healthy' else macro(vals),
                    fault_claim=float(np.mean([np.mean(v) for v in false.values()])) if stage=='healthy' else macro({k:float(np.mean(v)) for k,v in false.items()}),
                    bearing_recalls={k[0]:v for k,v in vals.items()})
                if stage!='healthy':result['per_class']={str(c):macro({k:v for k,v in vals.items() if k[1]==c}) for c in (1,2,4)}
                summary[setting][method][stage]=result
    for setting,methods in summary.items():
        for method in METHODS:
            for stage in ('terminal','preterminal'):
                vals=lambda group,m:{(n,LABEL[n]):v for n,v in summary[group][m][stage]['bearing_recalls'].items()}
                methods[method][stage]['vs_same_library_real']=paired_delta(vals(setting,method),vals(setting,'real'))
                methods[method][stage]['vs_xjtu_real']=paired_delta(vals(setting,method),vals('xjtu:'+setting.split(':')[1],'real'))
    return summary


def main():
    DATA.mkdir(exist_ok=True);stamp=hashes();(OUT/'external_prerun.json').write_text(json.dumps(stamp,indent=2))
    with ProcessPoolExecutor(4) as pool:
        for i in pool.map(prepare,EXTERNAL):print('External prepared',i,flush=True)
    cache={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in DATA.glob('*.npz')}
    rows=[]
    with ProcessPoolExecutor(4) as pool:
        for r in pool.map(job,[(n,s) for n in LABEL for s in SEEDS]):
            rows.append(r);print('External benchmark',len(rows),'/39',flush=True)
    if hashes()!=stamp or cache!={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in DATA.glob('*.npz')}:
        raise ValueError('Inputs changed during run')
    result=dict(rows=rows,summary=aggregate(rows),sha256=stamp,cache_sha256=cache,confirmatory=False,duplicate_identical=True)
    (OUT/'external.json').write_text(json.dumps(result,indent=2));print('External done',flush=True)


if __name__=='__main__':main()
