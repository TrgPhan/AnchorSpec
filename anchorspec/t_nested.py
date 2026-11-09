"""Source-event-only augmentation selection, nested by physical bearing."""
import os
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import hashlib
import json
import numpy as np
from u_natural import ROOT,CACHE,LABEL,ORDERS,bearing,training
from invariant_classifier import InvariantClassifier
from measured_transport import generate
from event_experts import causal_average
from y_metrics import macro,paired_delta
from t_readiness import OUT,SEEDS,selective,measurements,digest
import funnel as Fu

METHODS=('real','surrogate','severity','transport')
DERIVED=ROOT.parent/'data/t_nested'


def frozen():
    result=digest()
    for n in ('t_nested.py','PROTOCOL_T_NESTED.md','results/t/readiness.json'):
        result['anchorspec/'+n]=hashlib.sha256((ROOT/n).read_bytes()).hexdigest()
    return result


def prepare(task):
    target,seed=task;t=bearing(target);arrays={}
    for source in LABEL:
        if source==target:continue
        s=bearing(source)
        rng=np.random.default_rng([seed,int(target[0]),int(target[-1]),int(source[0]),int(source[-1]),10])
        waves,_=generate(s['terminal'],s['healthy'],t['healthy'][:5],float(s['fr']),float(t['fr']),rng)
        for m in ('severity','transport'):
            arrays[f'{source}:{m}']=Fu.feats(waves[m][:,None,:],4000,float(s['fr']) if m=='severity' else float(t['fr']),ORDERS)
        with np.load(CACHE/f'{source}_{seed}_aug.npz') as f:arrays[f'{source}:surrogate']=f['surrogate']
    np.savez_compressed(DERIVED/f'{target}_{seed}.npz',**arrays)
    return task


@lru_cache(39)
def derivatives(target,seed):
    with np.load(DERIVED/f'{target}_{seed}.npz') as f:
        return {n:{m:f[f'{n}:{m}'] for m in METHODS if m!='real'} for n in LABEL if n!=target}


def choose(scores):
    eligible=[m for m in METHODS if scores[m]['healthy_false_fault']<=.05]
    if not eligible:return 'real',False
    best=max(eligible,key=lambda m:scores[m]['terminal_macro_recall'])
    if 'real' in eligible and scores[best]['terminal_macro_recall']<scores['real']['terminal_macro_recall']+.02:
        best='real'
    return best,True


def selection(task):
    outer,seed=task;validation=[]
    for inner in LABEL:
        if inner==outer:continue
        sources=[n for n in LABEL if n not in (outer,inner)]
        events=[(n,LABEL[n],bearing(n)['terminal_features']) for n in sources]
        data=bearing(inner);derived=derivatives(inner,seed)
        # The cached outer source exists for other folds but is never passed to training.
        derived={n:derived[n] for n in sources}
        row=dict(inner=inner,label=LABEL[inner],donors=sources,models={})
        for method in METHODS:
            model=InvariantClassifier('rf',seed).fit(*training(data['healthy_features'][:5],events,derived,method))
            metrics={}
            for stage,x,label in (('healthy',data['healthy_features'][5:],0),('terminal',data['terminal_features'],LABEL[inner])):
                pred=selective(causal_average(model.predict_proba(x)),0)
                metrics[stage]=measurements(pred,label)
            row['models'][method]=metrics
        validation.append(row)
    scores={m:dict(terminal_macro_recall=macro({(r['inner'],r['label']):r['models'][m]['terminal']['recall'] for r in validation}),
        healthy_false_fault=float(np.mean([r['models'][m]['healthy']['fault_claim'] for r in validation]))) for m in METHODS}
    selected,passed=choose(scores)
    return dict(target=outer,seed=seed,selected=selected,healthy_selection_passed=passed,scores=scores,inner_folds=validation)


def evaluate(selections,evidence):
    lookup={(r['target'],r['seed']):r for r in evidence['rows']};summary={}
    for name in (*METHODS,'selector'):
        summary[name]={}
        for stage in ('healthy','preterminal','terminal'):
            metrics={}
            for metric in ('recall','fault_claim','abstain'):
                groups={}
                for row in selections:
                    method=row['selected'] if name=='selector' else name
                    source=lookup[row['target'],row['seed']]
                    key=(row['target'],source['label'])
                    groups.setdefault(key,[]).append(source['libraries']['closed']['models']['rf:'+method][stage]['policies']['selective_0'][metric])
                vals={k:float(np.mean(v)) for k,v in groups.items()}
                metrics[metric]=float(np.mean(list(vals.values()))) if stage=='healthy' else macro(vals)
                if metric=='recall' and stage!='healthy':
                    metrics['per_class']={str(c):macro({k:v for k,v in vals.items() if k[1]==c}) for c in (1,2,4)}
                    metrics['bearing_recalls']={k[0]:v for k,v in vals.items()}
            summary[name][stage]=metrics
    for name in (*METHODS,'selector'):
        for stage in ('preterminal','terminal'):
            vals=lambda m:{(n,LABEL[n]):v for n,v in summary[m][stage]['bearing_recalls'].items()}
            summary[name][stage]['vs_real']=paired_delta(vals(name),vals('real'))
    return summary


def main():
    DERIVED.mkdir(exist_ok=True);stamp=frozen();tasks=[(n,s) for n in LABEL for s in SEEDS]
    (OUT/'nested_prerun.json').write_text(json.dumps(stamp,indent=2))
    # Always rebuild to avoid silently mixing prepared artifacts across implementations.
    with ProcessPoolExecutor(4) as pool:
        for i,t in enumerate(pool.map(prepare,tasks),1):
            if i%10==0:print('Nested prepare',i,'/39',flush=True)
    prepared={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in DERIVED.glob('*.npz')}
    selections=[]
    with ProcessPoolExecutor(4) as pool:
        for row in pool.map(selection,tasks):
            selections.append(row);print('Nested selection',len(selections),'/39',row['selected'],flush=True)
    if frozen()!=stamp:raise ValueError('Evidence changed during nested selection')
    # Selections are committed locally before the outer test outcomes are read.
    (OUT/'nested_selection.json').write_text(json.dumps(dict(rows=selections,sha256=stamp,prepared_sha256=prepared),indent=2))
    evidence=json.loads((OUT/'readiness.json').read_text())
    summary=evaluate(selections,evidence)
    if prepared!={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in DERIVED.glob('*.npz')}:
        raise ValueError('Derived data changed')
    if frozen()!=stamp:raise ValueError('Evidence changed during scoring')
    result=dict(summary=summary,choices=dict(Counter(r['selected'] for r in selections)),
        all_healthy_selection_passed=all(r['healthy_selection_passed'] for r in selections),
        sha256=stamp,confirmatory=False,independent_bearings=13,outer_folds=39,inner_fits=39*12*4)
    (OUT/'nested.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result['choices']),flush=True)
    print(json.dumps(summary['selector']),flush=True)


if __name__=='__main__':main()
