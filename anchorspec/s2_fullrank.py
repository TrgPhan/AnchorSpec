"""Lossless-on-training PCA ablation; no changes to frozen S source."""
import os
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('MKL_NUM_THREADS','1')
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import pickle
import time
import numpy as np
import torch
from sklearn.preprocessing import StandardScaler
from s_latent import WaveCodec,LatentGenerator
from s_additive import ROOT,hashes as s_hashes,additive_training,RATIOS,ALPHAS,SEEDS,aggregate
from u_natural import LABEL,ORDERS,bearing
from invariant_classifier import InvariantClassifier
from event_experts import causal_average
from diagnostic_experts import fault_labels
from t_readiness import selective,measurements
import funnel as Fu

OUT=ROOT/'results/s2';DATA=ROOT.parent/'data/s2_generation'
METHODS=('pca_bootstrap','flow','diffusion')


def hashes():
    d=s_hashes()
    for n in ('s2_fullrank.py','PROTOCOL_S2_FULLRANK.md','results/s/additive.json'):
        d['anchorspec/'+n]=hashlib.sha256((ROOT/n).read_bytes()).hexdigest()
    return d


def job(task):
    target,seed=task;start=time.perf_counter();sources=[n for n in LABEL if n!=target]
    folder=DATA/f'{target}_{seed}';folder.mkdir(exist_ok=True)
    waves=np.concatenate([bearing(n)['terminal'] for n in sources]);codec=WaveCodec().fit(waves,len(waves)-1)
    if codec.diagnostics['relative_reconstruction_l2']>=1e-6:raise ValueError('Full-rank PCA is not reconstructing training waveforms')
    continuous=[];labels=[];weights=[];counts=Counter(LABEL[n] for n in sources)
    for n in sources:
        s=bearing(n);rms=np.sqrt(np.mean(s['healthy'][:5]**2))
        continuous.extend([[float(s['fr']),np.log(max(rms,1e-12))]]*10)
        labels.extend([{1:0,2:1,4:2}[LABEL[n]]]*10);weights.extend([1/(counts[LABEL[n]]*10)]*10)
    scaler=StandardScaler().fit(continuous)
    conditions=np.column_stack((np.eye(3)[labels],scaler.transform(continuous))).astype(np.float32)
    query=np.concatenate([np.repeat(conditions[i*10:i*10+1],20,axis=0) for i in range(len(sources))])
    generated={};metadata=dict(codec=codec.diagnostics,generators={},quality={})
    for kind in ('flow','diffusion'):
        model=LatentGenerator(kind,seed,1500).fit(codec.train_z,conditions,weights)
        generated[kind],info=codec.decode(model.sample(query,seed+20261106));metadata['quality'][kind]=info
        metadata['generators'][kind]=dict(loss=model.losses,training_seconds=model.training_seconds,steps=model.steps,
            parameters=sum(p.numel() for p in model.model.parameters()))
        torch.save(dict(state_dict=model.model.state_dict(),kind=kind,seed=seed,dimensions=codec.train_z.shape[1],
            condition_dimensions=conditions.shape[1],train_lo=model.lo,train_hi=model.hi,**metadata['generators'][kind]),folder/f'{kind}.pt')
    rng=np.random.default_rng([seed,20261106]);indices=np.concatenate([np.concatenate((rng.permutation(10),rng.permutation(10)))+i*10 for i in range(len(sources))])
    generated['pca_bootstrap'],info=codec.decode(codec.train_z[indices]);metadata['quality']['pca_bootstrap']=info
    generated['duplicate_indices']=indices
    np.savez_compressed(folder/'waveforms.npz',**generated)
    with (folder/'codec.pkl').open('wb') as f:pickle.dump(dict(codec=codec,condition_scaler=scaler,sources=sources),f)
    events=[];derivatives={};t=bearing(target)
    for i,n in enumerate(sources):
        s=bearing(n);events.append((n,LABEL[n],s['terminal_features']))
        derivatives[n]={m:Fu.feats(generated[m][i*20:(i+1)*20,None,:],4000,float(s['fr']),ORDERS) for m in METHODS}
    np.savez_compressed(folder/'generated_features.npz',**{n+':'+m:a for n,d in derivatives.items() for m,a in d.items()})
    row=dict(target=target,seed=seed,label=LABEL[target],donors=sources,generation=metadata,scores={},counts={})
    for method in METHODS:
        for ratio in RATIOS:
            for alpha in ALPHAS:
                x,y,w,count=additive_training(t['healthy_features'][:5],events,derivatives,method,ratio,alpha)
                model=InvariantClassifier('rf',seed).fit(x,y,w);key=f'{method}_full:r{ratio:g}:a{alpha:g}'
                row['counts'][key]=count;record={};row['scores'][key]=record
                for stage,x in (('healthy',t['healthy_features'][5:]),('preterminal',t['preterminal_features']),('terminal',t['terminal_features'])):
                    raw=model.predict_proba(x);p=causal_average(raw);truth=0 if stage=='healthy' else LABEL[target]
                    record[stage]=dict(raw_scores=raw.tolist(),policies={})
                    for policy,pred in (('selective',selective(p,0)),('conditional',fault_labels(p))):
                        record[stage]['policies'][policy]=dict(predictions=pred.tolist(),**measurements(pred,truth))
    row['elapsed_seconds']=time.perf_counter()-start
    return row


def main():
    OUT.mkdir(exist_ok=True);DATA.mkdir(exist_ok=True);(OUT/'tasks').mkdir(exist_ok=True)
    frozen=hashes();prerun=OUT/'prerun.json'
    if prerun.exists() and json.loads(prerun.read_text())!=frozen:raise ValueError('Prerun source mismatch')
    prerun.write_text(json.dumps(frozen,indent=2));rows=[];tasks=[]
    for target in LABEL:
        for seed in SEEDS:
            path=OUT/'tasks'/f'{target}_{seed}.json'
            if path.exists():
                saved=json.loads(path.read_text())
                if saved['sha256']!=frozen:raise ValueError('Checkpoint mismatch')
                rows.append(saved['row'])
            else:tasks.append((target,seed))
    with ProcessPoolExecutor(3) as pool:
        for task,row in zip(tasks,pool.map(job,tasks)):
            (OUT/'tasks'/f'{task[0]}_{task[1]}.json').write_text(json.dumps(dict(sha256=frozen,row=row)))
            rows.append(row);print('Full-rank ablation',len(rows),'/39',task,round(row['elapsed_seconds'],1),'seconds',flush=True)
    old=json.loads((ROOT/'results/s/additive.json').read_text());lookup={(r['target'],r['seed']):r for r in old['rows']}
    combined=[]
    for row in rows:
        prior=lookup[row['target'],row['seed']]
        combined.append(dict(target=row['target'],seed=row['seed'],label=row['label'],scores=prior['scores']|row['scores']))
    if hashes()!=frozen:raise ValueError('Input or source changed during run')
    result=dict(rows=rows,summary=aggregate(combined),sha256=frozen,primary='flow_full:r1:a0.25',primary_policy='selective',
        baseline_source='results/s/additive.json',confirmatory=False,independent_bearings=13,models_trained=78,classifier_fits=702)
    (OUT/'fullrank.json').write_text(json.dumps(result,indent=2));print('Full rank completed',flush=True)


if __name__=='__main__':main()
