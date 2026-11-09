"""Keep every real row and its weight; append matched amounts of synthetic data."""
import os
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('MKL_NUM_THREADS','1')
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import pickle
import time
import numpy as np
import torch
from sklearn.preprocessing import StandardScaler
from u_natural import ROOT,CACHE,LABEL,ORDERS,bearing,training
from t_nested import derivatives
from invariant_classifier import InvariantClassifier
from event_experts import causal_average
from diagnostic_experts import fault_labels
from t_readiness import selective,measurements
from s_latent import WaveCodec,LatentGenerator
from y_metrics import macro,paired_delta
import funnel as Fu

OUT=ROOT/'results/s';DATA=ROOT.parent/'data/s_generation'
SEEDS=(11,29,47);RATIOS=(.5,1.,2.);ALPHAS=(.25,1.)
METHODS=('duplicate','surrogate','envelope','severity','pca_bootstrap','flow','diffusion')


def hashes():
    paths=[ROOT/n for n in ('s_additive.py','s_latent.py','PROTOCOL_S_GENERATION.md','u_natural.py','u_download.py',
        't_nested.py','t_readiness.py','invariant_classifier.py','event_experts.py','diagnostic_experts.py',
        'y_metrics.py','cheap_sensor.py','features.py','funnel.py','bearing.py')]
    paths += [ROOT/'results/t/readiness.json']
    paths += [CACHE/f'{n}.npz' for n in LABEL]
    paths += [CACHE/f'{n}_{seed}_aug.npz' for n in LABEL for seed in SEEDS]
    paths += [ROOT.parent/'data/t_nested'/f'{n}_{seed}.npz' for n in LABEL for seed in SEEDS]
    return {os.path.relpath(p,ROOT.parent).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def additive_training(healthy,events,derived,method,ratio,alpha):
    # Existing real baseline distribution and numerical weights are retained exactly.
    x,y,w=training(healthy,events,{},'real');real_count=len(x)
    if method=='real':return x,y,w,dict(real_count=real_count,synthetic_count=0,real_weight=float(w.sum()),synthetic_weight=0.)
    if method not in METHODS or ratio not in RATIOS or alpha not in ALPHAS:raise ValueError('Unsupported additive configuration')
    classes=Counter(c for n,c,source in events);scale=real_count/(1+len(classes))
    groups=[];labels=[];weights=[]
    for name,c,source in events:
        count=int(len(source)*ratio);a=derived[name][method][:count]
        if len(a)!=count or not np.isfinite(a).all():raise ValueError('Insufficient generated rows')
        groups.append(a);labels.append(np.full(count,c,int))
        weights.append(np.full(count,alpha*scale/(classes[c]*len(source))))
    gen=np.concatenate(groups);gy=np.concatenate(labels);gw=np.concatenate(weights)
    return np.concatenate((x,gen)),np.concatenate((y,gy)),np.concatenate((w,gw)),dict(
        real_count=real_count,synthetic_count=len(gen),real_weight=float(w.sum()),synthetic_weight=float(gw.sum()))


def prepare_models(target,seed,sources,folder):
    waves=np.concatenate([bearing(n)['terminal'] for n in sources]);codec=WaveCodec().fit(waves)
    continuous=[];labels=[];training_weights=[];counts=Counter(LABEL[n] for n in sources)
    for n in sources:
        s=bearing(n);healthy=s['healthy'][:5];rms=np.sqrt(np.mean(healthy**2))
        continuous.extend([[float(s['fr']),np.log(max(rms,1e-12))]]*10)
        labels.extend([{1:0,2:1,4:2}[LABEL[n]]]*10);training_weights.extend([1/(counts[LABEL[n]]*10)]*10)
    condition_scaler=StandardScaler().fit(continuous)
    conditions=np.column_stack((np.eye(3)[labels],condition_scaler.transform(continuous))).astype(np.float32)
    sampled_conditions=np.concatenate([np.repeat(conditions[i*10:i*10+1],20,axis=0) for i in range(len(sources))])
    output={};logs={};quality={}
    for kind in ('flow','diffusion'):
        generator=LatentGenerator(kind,seed,steps=1500).fit(codec.train_z,conditions,training_weights)
        z=generator.sample(sampled_conditions,seed+20261106);generated,info=codec.decode(z)
        output[kind]=generated;quality[kind]=info
        logs[kind]=dict(loss=generator.losses,training_seconds=generator.training_seconds,
            parameters=sum(p.numel() for p in generator.model.parameters()),steps=generator.steps)
        torch.save(dict(state_dict=generator.model.state_dict(),kind=kind,seed=seed,dimensions=codec.train_z.shape[1],
            condition_dimensions=conditions.shape[1],train_lo=generator.lo,train_hi=generator.hi,**logs[kind]),folder/f'{kind}.pt')
    rng=np.random.default_rng([seed,20261106]);indices=np.concatenate([np.concatenate((rng.permutation(10),rng.permutation(10)))+i*10 for i in range(len(sources))])
    reconstructed,info=codec.decode(codec.train_z[indices]);output['pca_bootstrap']=reconstructed;quality['pca_bootstrap']=info
    output['duplicate_indices']=indices
    with (folder/'codec.pkl').open('wb') as f:pickle.dump(dict(codec=codec,condition_scaler=condition_scaler,sources=sources),f)
    np.savez_compressed(folder/'waveforms.npz',**output)
    return output,dict(codec=codec.diagnostics,generators=logs,quality=quality)


def job(task):
    target,seed=task;start=time.perf_counter();sources=[n for n in LABEL if n!=target]
    folder=DATA/f'{target}_{seed}';folder.mkdir(exist_ok=True)
    generated,meta=prepare_models(target,seed,sources,folder)
    t=bearing(target);events=[];derived={};old=derivatives(target,seed)
    for i,name in enumerate(sources):
        s=bearing(name);events.append((name,LABEL[name],s['terminal_features']))
        indices=generated['duplicate_indices'][i*20:(i+1)*20]-i*10
        d=dict(duplicate=s['terminal_features'][indices],surrogate=old[name]['surrogate'][:20],severity=old[name]['severity'][:20])
        with np.load(CACHE/f'{name}_{seed}_aug.npz') as f:d['envelope']=f['envelope'][:20]
        for kind in ('pca_bootstrap','flow','diffusion'):
            d[kind]=Fu.feats(generated[kind][i*20:(i+1)*20,None,:],4000,float(s['fr']),ORDERS)
        derived[name]=d
    np.savez_compressed(folder/'generated_features.npz',**{n+':'+m:a for n,d in derived.items() for m,a in d.items()})
    row=dict(target=target,seed=seed,label=LABEL[target],donors=sources,reference_indices=list(range(1,6)),
        healthy_test_indices=list(range(6,11)),generation=meta,scores={},counts={})
    configs=[('real',0.,0.)]+[(m,r,a) for m in METHODS for r in RATIOS for a in ALPHAS]
    for method,ratio,alpha in configs:
        x,y,w,counts=additive_training(t['healthy_features'][:5],events,derived,method,ratio,alpha)
        key='real' if method=='real' else f'{method}:r{ratio:g}:a{alpha:g}'
        model=InvariantClassifier('rf',seed).fit(x,y,w);row['counts'][key]=counts;record={};row['scores'][key]=record
        for stage,features in (('healthy',t['healthy_features'][5:]),('preterminal',t['preterminal_features']),('terminal',t['terminal_features'])):
            raw=model.predict_proba(features);p=causal_average(raw);truth=0 if stage=='healthy' else LABEL[target]
            record[stage]=dict(raw_scores=raw.tolist(),policies={})
            for policy,pred in (('selective',selective(p,0)),('conditional',fault_labels(p))):
                record[stage]['policies'][policy]=dict(predictions=pred.tolist(),**measurements(pred,truth))
    row['elapsed_seconds']=time.perf_counter()-start
    return row


def aggregate(rows):
    summary={};keys=list(rows[0]['scores'])
    for key in keys:
        summary[key]={}
        for policy in ('selective','conditional'):
            result={};summary[key][policy]=result
            for stage in ('healthy','preterminal','terminal'):
                grouped={};false={}
                for r in rows:
                    k=(r['target'],r['label']);m=r['scores'][key][stage]['policies'][policy]
                    grouped.setdefault(k,[]).append(m['recall']);false.setdefault(k,[]).append(m['fault_claim'])
                vals={k:float(np.mean(v)) for k,v in grouped.items()}
                v=dict(recall=float(np.mean(list(vals.values()))) if stage=='healthy' else macro(vals),
                    fault_claim=float(np.mean([np.mean(a) for a in false.values()])) if stage=='healthy' else macro({k:float(np.mean(a)) for k,a in false.items()}),
                    bearing_recalls={n:value for (n,c),value in vals.items()})
                if stage!='healthy':v['per_class']={str(c):macro({k:a for k,a in vals.items() if k[1]==c}) for c in (1,2,4)}
                result[stage]=v
    for key in keys:
        for policy in ('selective','conditional'):
            for stage in ('preterminal','terminal'):
                vals=lambda k:{(n,LABEL[n]):v for n,v in summary[k][policy][stage]['bearing_recalls'].items()}
                bases=['real'] if key=='real' else ['real','duplicate:'+key.split(':',1)[1],'surrogate:'+key.split(':',1)[1]]
                summary[key][policy][stage]['differences']={base:paired_delta(vals(key),vals(base)) for base in bases}
    return summary


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=3);args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);DATA.mkdir(exist_ok=True);(OUT/'tasks').mkdir(exist_ok=True)
    frozen=hashes();prerun=OUT/'prerun.json'
    if prerun.exists() and json.loads(prerun.read_text())!=frozen:raise ValueError('Frozen source changed; use new experiment')
    prerun.write_text(json.dumps(frozen,indent=2));rows=[];todo=[]
    for target in LABEL:
        for seed in SEEDS:
            path=OUT/'tasks'/f'{target}_{seed}.json'
            if path.exists():
                saved=json.loads(path.read_text())
                if saved['sha256']!=frozen:raise ValueError('Checkpoint source mismatch')
                rows.append(saved['row'])
            else:todo.append((target,seed))
    with ProcessPoolExecutor(args.workers) as pool:
        for task,row in zip(todo,pool.map(job,todo)):
            (OUT/'tasks'/f'{task[0]}_{task[1]}.json').write_text(json.dumps(dict(sha256=frozen,row=row)),encoding='utf8')
            rows.append(row);print('Additive generative benchmark',len(rows),'/39',task,round(row['elapsed_seconds'],1),'seconds',flush=True)
    previous=json.loads((ROOT/'results/t/readiness.json').read_text());lookup={(r['target'],r['seed']):r for r in previous['rows']}
    for row in rows:
        old=lookup[row['target'],row['seed']]['libraries']['closed']['models']['rf:real']
        for stage,record in row['scores']['real'].items():
            if record['raw_scores']!=old[stage]['raw_scores']:raise ValueError('Real baseline no longer reproduces T')
    if hashes()!=frozen:raise ValueError('Source or input changed during evaluation')
    result=dict(rows=rows,summary=aggregate(rows),sha256=frozen,baseline_T_reproduced=True,confirmatory=False,
        primary='flow:r1:a0.25',primary_policy='selective',independent_bearings=13,
        models_trained=78,classifier_fits=39*43,torch=torch.__version__,device='cpu')
    (OUT/'additive.json').write_text(json.dumps(result,indent=2),encoding='utf8');print('S completed',flush=True)


if __name__=='__main__':main()
