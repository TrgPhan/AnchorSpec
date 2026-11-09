"""Sampling-step CPU ablation with checkpoint replay, no retraining."""
import os
for variable in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ.setdefault(variable,'1')
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import time
import numpy as np
import torch
from s3_cpu_benchmark import ROOT,OUT,DATA,prepare
from s3_spectral import ResidualGenerator,SmallNetwork
from s_latent import schedule
from s_additive import SEEDS,aggregate,additive_training
from u_natural import LABEL,ORDERS,bearing
from invariant_classifier import InvariantClassifier
from event_experts import causal_average
from diagnostic_experts import fault_labels
from t_readiness import selective,measurements
from y_metrics import paired_delta
import funnel as Fu


def hashes():
    paths=[ROOT/n for n in ('s3b_steps.py','PROTOCOL_S3B_STEPS.md','s3_spectral.py','s3_cpu_benchmark.py','results/s3/spectral.json')]
    for target in LABEL:
        for seed in SEEDS:
            paths.extend(DATA/f'{target}_{seed}'/n for n in ('flow.pt','diffusion.pt','codec.pkl','residuals.npz','features.npz'))
    return {p.relative_to(ROOT.parent).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def job(task):
    target,seed=task;torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    sources,waves,codec,indices,limits,_=prepare(target,seed);anchors=waves[indices];query=codec.conditions[indices]
    folder=DATA/f'{target}_{seed}';t=bearing(target);events=[(n,LABEL[n],bearing(n)['terminal_features']) for n in sources]
    row=dict(target=target,seed=seed,label=LABEL[target],scores={},counts={},replay_16=True,generation_seconds={})
    with np.load(folder/'features.npz') as f:
        for kind in ('flow','diffusion'):
            saved=torch.load(folder/f'{kind}.pt',map_location='cpu',weights_only=True)
            model=ResidualGenerator(kind,seed);model.model=SmallNetwork(saved['dimensions'],saved['condition_dimensions'])
            model.model.load_state_dict(saved['state_dict']);model.model.eval();model.lo=saved['train_lo'];model.hi=saved['train_hi']
            model.beta,model.bar=schedule()
            for steps in (16,4,8,32):
                start=time.perf_counter();residual=model.sample(query,seed+20261106,steps)*codec.scale
                generated,_=codec.apply(anchors,residual,.5,limits);row['generation_seconds'][f'{kind}_{steps}']=time.perf_counter()-start
                derived={n:{'flow':Fu.feats(generated[i*10:(i+1)*10,None,:],4000,float(bearing(n)['fr']),ORDERS)} for i,n in enumerate(sources)}
                if steps==16:
                    for n in sources:np.testing.assert_allclose(derived[n]['flow'],f[n+f':spectral_{kind}_half'],rtol=1e-12,atol=1e-12)
                    continue
                x,y,w,count=additive_training(t['healthy_features'][:5],events,derived,'flow',1.,.25)
                classifier=InvariantClassifier('rf',seed).fit(x,y,w);key=f'spectral_{kind}_steps{steps}:r1:a0.25'
                row['counts'][key]=count;record={};row['scores'][key]=record
                for stage in ('healthy','preterminal','terminal'):
                    x=t[stage+'_features'][5:] if stage=='healthy' else t[stage+'_features']
                    raw=classifier.predict_proba(x);p=causal_average(raw);truth=0 if stage=='healthy' else LABEL[target]
                    record[stage]=dict(raw_scores=raw.tolist(),policies={})
                    for policy,pred in (('selective',selective(p,0)),('conditional',fault_labels(p))):
                        record[stage]['policies'][policy]=dict(predictions=pred.tolist(),**measurements(pred,truth))
    return row


def main():
    frozen=hashes();stamp=OUT/'steps_prerun.json'
    if stamp.exists() and json.loads(stamp.read_text())!=frozen:raise ValueError('Source changed')
    stamp.write_text(json.dumps(frozen,indent=2));folder=OUT/'step_tasks';folder.mkdir(exist_ok=True)
    tasks=[(n,s) for n in LABEL for s in SEEDS];todo=[];rows=[]
    for n,s in tasks:
        path=folder/f'{n}_{s}.json'
        if path.exists():
            saved=json.loads(path.read_text());assert saved['sha256']==frozen;rows.append(saved['row'])
        else:todo.append((n,s))
    with ProcessPoolExecutor(3) as pool:
        for task,row in zip(todo,pool.map(job,todo)):
            (folder/f'{task[0]}_{task[1]}.json').write_text(json.dumps(dict(sha256=frozen,row=row)))
            rows.append(row);print('S3B steps',len(rows),'/39',task,flush=True)
    prior=json.loads((OUT/'spectral.json').read_text());s=json.loads((ROOT/'results/s/additive.json').read_text())
    lookup={(r['target'],r['seed']):r for r in prior['rows']};controls={(r['target'],r['seed']):r for r in s['rows']}
    combined=[]
    for row in rows:
        key=row['target'],row['seed'];old={k:v for k,v in controls[key]['scores'].items() if k=='real' or k.endswith(':r1:a0.25')}
        combined.append(dict(target=row['target'],seed=row['seed'],label=row['label'],scores=old|lookup[key]['scores']|row['scores']))
    summary=aggregate(combined)
    for key in summary:
        if '_steps' not in key:continue
        kind=key.split('_')[1];base=f'spectral_{kind}_half:r1:a0.25'
        for policy in ('selective','conditional'):
            for stage in ('preterminal','terminal'):
                values=lambda name:{(n,LABEL[n]):v for n,v in summary[name][policy][stage]['bearing_recalls'].items()}
                summary[key][policy][stage]['differences'][base]=paired_delta(values(key),values(base))
    assert hashes()==frozen
    result=dict(rows=rows,summary=summary,sha256=frozen,confirmatory=False,models_retrained=0,classifier_fits=234,
                replay_16_all_folds=True,candidate_steps=8,primary_steps_unchanged=16)
    (OUT/'steps.json').write_text(json.dumps(result,indent=2));print('S3B completed',flush=True)


if __name__=='__main__':main()
