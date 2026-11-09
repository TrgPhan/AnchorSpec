"""Frozen exploratory benchmark of anchored CPU spectral residual generation."""
import os
for variable in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ.setdefault(variable,'1')
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import pickle
import time
import numpy as np
import torch
from s3_spectral import SpectralResidual,ResidualGenerator
from s_additive import ROOT,SEEDS,hashes as prior_hashes,additive_training,aggregate
from u_natural import LABEL,ORDERS,bearing
from invariant_classifier import InvariantClassifier
from event_experts import causal_average
from diagnostic_experts import fault_labels
from t_readiness import selective,measurements
from y_metrics import paired_delta
import funnel as Fu

OUT=ROOT/'results/s3';DATA=ROOT.parent/'data/s3_generation'
KINDS=('bootstrap','gaussian','flow','diffusion');STRENGTHS={'half':.5,'full':1.}


def hashes():
    out=prior_hashes()
    for name in ('s3_spectral.py','s3_cpu_benchmark.py','PROTOCOL_S3_CPU_RESIDUAL.md','results/s/additive.json','results/s2/fullrank.json'):
        out['anchorspec/'+name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    for target in LABEL:
        for seed in SEEDS:
            p=ROOT.parent/f'data/s_generation/{target}_{seed}/waveforms.npz'
            out[p.relative_to(ROOT.parent).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def quality(anchors,waves,info):
    numerator=np.sum(anchors*waves,axis=1)
    correlation=numerator/np.sqrt(np.sum(anchors**2,axis=1)*np.sum(waves**2,axis=1))
    rms=lambda x:np.sqrt(np.mean(x*x,axis=1))
    return dict(**info,anchor_correlation_mean=float(np.mean(correlation)),
                anchor_correlation_min=float(np.min(correlation)),
                relative_waveform_change=float(np.linalg.norm(waves-anchors)/np.linalg.norm(anchors)),
                rms_ratio_mean=float(np.mean(rms(waves)/rms(anchors))),
                unique_waveforms=len(np.unique(waves,axis=0)))


def prepare(target,seed):
    sources=[n for n in LABEL if n!=target];counts=Counter(LABEL[n] for n in sources)
    waves=np.concatenate([bearing(n)['terminal'] for n in sources]);conditions=[];weights=[]
    for n in sources:
        s=bearing(n);c=np.r_[np.eye(3)[{1:0,2:1,4:2}[LABEL[n]]],float(s['fr']),np.log(np.sqrt(np.mean(s['healthy'][:5]**2)))]
        conditions.extend([c]*10);weights.extend([1/counts[LABEL[n]]]*10)
    codec=SpectralResidual().fit(waves,np.repeat(np.arange(12),10),np.asarray(conditions))
    with np.load(ROOT.parent/f'data/s_generation/{target}_{seed}/waveforms.npz') as z:
        indices=np.concatenate([z['duplicate_indices'][i*20:i*20+10] for i in range(12)])
    assert all(set(indices[i*10:(i+1)*10])==set(range(i*10,i*10+10)) for i in range(12))
    limits=np.concatenate([np.repeat(np.abs(waves[i*10:(i+1)*10]).max(),10) for i in range(12)])
    return sources,waves,codec,indices,limits,np.asarray(weights)[codec.pairs[:,0]]


def job(task):
    target,seed=task;start=time.perf_counter();folder=DATA/f'{target}_{seed}';folder.mkdir(exist_ok=True)
    sources,waves,codec,indices,limits,weights=prepare(target,seed)
    anchors=waves[indices];query=codec.conditions[indices];residuals={};logs={}
    for kind in ('flow','diffusion'):
        model=ResidualGenerator(kind,seed).fit(codec.z,codec.conditions[codec.pairs[:,0]],weights)
        tic=time.perf_counter();residuals[kind]=model.sample(query,seed+20261106)*codec.scale
        logs[kind]=dict(training_seconds=model.training_seconds,sampling_residual_seconds=time.perf_counter()-tic,
                        parameters=sum(p.numel() for p in model.model.parameters()),steps=model.steps,
                        evaluations=16,losses=model.losses,device='cpu')
        torch.save(dict(state_dict=model.model.state_dict(),kind=kind,seed=seed,dimensions=24,
                        condition_dimensions=query.shape[1],train_lo=model.lo,train_hi=model.hi,**logs[kind]),folder/f'{kind}.pt')
    rng=np.random.default_rng([seed,20261106,3]);empirical=[];normal=[]
    for i in range(12):
        donor_pairs=codec.residuals[codec.pairs[:,0]//10==i]
        empirical.append(donor_pairs[rng.integers(len(donor_pairs),size=10)])
        covariance=np.cov(donor_pairs.T);covariance=.8*covariance+.2*np.diag(np.diag(covariance))+np.eye(24)*1e-8
        normal.append(rng.multivariate_normal(donor_pairs.mean(0),covariance,size=10))
    residuals['bootstrap']=np.concatenate(empirical);residuals['gaussian']=np.concatenate(normal)
    np.savez_compressed(folder/'residuals.npz',indices=indices,peak_limits=limits,**residuals)
    with (folder/'codec.pkl').open('wb') as f:pickle.dump(dict(codec=codec,sources=sources),f)
    derived={n:{} for n in sources};audit={};feature_arrays={}
    for kind in KINDS:
        for strength_name,strength in STRENGTHS.items():
            method=f'spectral_{kind}_{strength_name}';tic=time.perf_counter()
            generated,info=codec.apply(anchors,residuals[kind],strength,limits)
            generation_seconds=time.perf_counter()-tic;tic=time.perf_counter()
            for i,n in enumerate(sources):
                value=Fu.feats(generated[i*10:(i+1)*10,None,:],4000,float(bearing(n)['fr']),ORDERS)
                derived[n][method]=value;feature_arrays[n+':'+method]=value
            audit[method]=dict(**quality(anchors,generated,info),decode_seconds=generation_seconds,feature_seconds=time.perf_counter()-tic)
    np.savez_compressed(folder/'features.npz',**feature_arrays)
    t=bearing(target);events=[(n,LABEL[n],bearing(n)['terminal_features']) for n in sources]
    row=dict(target=target,seed=seed,label=LABEL[target],donors=sources,reference_indices=list(range(1,6)),
             healthy_test_indices=list(range(6,11)),generation=dict(generators=logs,quality=audit,training_windows=120,derived_pairs=len(codec.pairs)),scores={},counts={})
    for method in audit:
        # Reuse verified additive-weight code; 'flow' is only its lookup alias.
        values={n:{'flow':d[method]} for n,d in derived.items()}
        x,y,w,count=additive_training(t['healthy_features'][:5],events,values,'flow',1.,.25)
        model=InvariantClassifier('rf',seed).fit(x,y,w);key=method+':r1:a0.25'
        row['counts'][key]=count;record={};row['scores'][key]=record
        for stage in ('healthy','preterminal','terminal'):
            features=t[stage+'_features'][5:] if stage=='healthy' else t[stage+'_features']
            raw=model.predict_proba(features);p=causal_average(raw);truth=0 if stage=='healthy' else LABEL[target]
            record[stage]=dict(raw_scores=raw.tolist(),policies={})
            for policy,pred in (('selective',selective(p,0)),('conditional',fault_labels(p))):
                record[stage]['policies'][policy]=dict(predictions=pred.tolist(),**measurements(pred,truth))
    row['elapsed_seconds']=time.perf_counter()-start
    return row


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=3);args=parser.parse_args()
    OUT.mkdir(exist_ok=True);DATA.mkdir(exist_ok=True);(OUT/'tasks').mkdir(exist_ok=True)
    frozen=hashes();prerun=OUT/'prerun.json'
    if prerun.exists() and json.loads(prerun.read_text())!=frozen:raise ValueError('Frozen sources changed')
    prerun.write_text(json.dumps(frozen,indent=2));todo=[];rows=[]
    for target in LABEL:
        for seed in SEEDS:
            path=OUT/'tasks'/f'{target}_{seed}.json'
            if path.exists():
                saved=json.loads(path.read_text())
                if saved['sha256']!=frozen:raise ValueError('Task sources changed')
                rows.append(saved['row'])
            else:todo.append((target,seed))
    with ProcessPoolExecutor(args.workers) as pool:
        for task,row in zip(todo,pool.map(job,todo)):
            (OUT/'tasks'/f'{task[0]}_{task[1]}.json').write_text(json.dumps(dict(sha256=frozen,row=row)))
            rows.append(row);print('S3 CPU',len(rows),'/39',task,round(row['elapsed_seconds'],1),'seconds',flush=True)
    old=json.loads((ROOT/'results/s/additive.json').read_text());old2=json.loads((ROOT/'results/s2/fullrank.json').read_text())
    lookup={(r['target'],r['seed']):r for r in old['rows']};lookup2={(r['target'],r['seed']):r for r in old2['rows']}
    combined=[]
    for row in rows:
        key=row['target'],row['seed'];prior=lookup[key]['scores']|lookup2[key]['scores']
        selected={k:v for k,v in prior.items() if k=='real' or k.endswith(':r1:a0.25')}
        combined.append(dict(target=row['target'],seed=row['seed'],label=row['label'],scores=selected|row['scores']))
    summary=aggregate(combined)
    for key in summary:
        for policy in ('selective','conditional'):
            for stage in ('preterminal','terminal'):
                values=lambda name:{(n,LABEL[n]):v for n,v in summary[name][policy][stage]['bearing_recalls'].items()}
                for base in ('severity:r1:a0.25','spectral_bootstrap_half:r1:a0.25','spectral_gaussian_half:r1:a0.25'):
                    summary[key][policy][stage]['differences'][base]=paired_delta(values(key),values(base))
    if hashes()!=frozen:raise ValueError('Source changed during run')
    result=dict(rows=rows,summary=summary,sha256=frozen,primary='spectral_flow_half:r1:a0.25',
                primary_policy='selective',confirmatory=False,independent_bearings=13,models_trained=78,
                classifier_fits=312,device='cpu',threads_per_worker=1,workers=args.workers)
    (OUT/'spectral.json').write_text(json.dumps(result,indent=2));print('S3 completed',flush=True)


if __name__=='__main__':main()
