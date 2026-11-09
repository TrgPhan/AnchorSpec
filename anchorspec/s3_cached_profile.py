"""Validate cached CPU execution on all folds; measure paired warm timings."""
import os
for variable in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ.setdefault(variable,'1')
import hashlib
import json
import time
import numpy as np
import torch
from s3_cpu_benchmark import ROOT,OUT,DATA,prepare
from s3_fast_cpu import load_model
from s3_cached_features import CachedDecoder,extract,plan
from s_additive import additive_training
from u_natural import LABEL,ORDERS,bearing
from invariant_classifier import InvariantClassifier
import funnel as Fu


def features(waves,sources):
    return np.concatenate([extract(waves[i*10:(i+1)*10],4000,float(bearing(n)['fr']),ORDERS) for i,n in enumerate(sources)])


def main():
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    evidence=json.loads((OUT/'spectral.json').read_text());checks=[];profiles=[]
    for row in evidence['rows']:
        target,seed=row['target'],row['seed'];sources,waves,c,ix,limits,_=prepare(target,seed);anchors=waves[ix]
        folder=DATA/f'{target}_{seed}';decoder=CachedDecoder(c,anchors,limits)
        with np.load(folder/'residuals.npz') as saved,np.load(folder/'features.npz') as stored:
            for kind in ('flow','diffusion'):
                generated=decoder(saved[kind]);expected,_=c.apply(anchors,saved[kind],.5,limits)
                np.testing.assert_array_equal(generated,expected)
                f=features(generated,sources);reference=np.concatenate([stored[n+f':spectral_{kind}_half'] for n in sources])
                np.testing.assert_array_equal(f,reference)
                t=bearing(target);events=[(n,LABEL[n],bearing(n)['terminal_features']) for n in sources]
                d={n:{'flow':f[i*10:(i+1)*10]} for i,n in enumerate(sources)}
                x,y,w,_=additive_training(t['healthy_features'][:5],events,d,'flow',1.,.25)
                classifier=InvariantClassifier('rf',seed).fit(x,y,w)
                for stage in ('healthy','preterminal','terminal'):
                    x=t[stage+'_features'][5:] if stage=='healthy' else t[stage+'_features']
                    np.testing.assert_array_equal(classifier.predict_proba(x),row['scores'][f'spectral_{kind}_half:r1:a0.25'][stage]['raw_scores'])
                checks.append(dict(target=target,seed=seed,kind=kind,waveforms_exact=True,features_exact=True,raw_scores_exact=True))
        if target!='1_1' or seed!=11:continue
        for kind in ('flow','diffusion'):
            generator=load_model(folder,kind);query=c.conditions[ix]
            plan.cache_clear();start=time.perf_counter();cached=CachedDecoder(c,anchors,limits)
            for n in sources:plan(4000,4000,float(bearing(n)['fr']),tuple(ORDERS.items()),1000.)
            setup=time.perf_counter()-start;records={'original':[],'cached':[]}
            for repeat in range(11):
                order=('original','cached') if repeat%2==0 else ('cached','original')
                for implementation in order:
                    start=time.perf_counter();r=generator.sample(query,seed+20261106,16)*c.scale
                    if implementation=='cached':wave=cached(r)
                    else:wave,_=c.apply(anchors,r,.5,limits)
                    middle=time.perf_counter()
                    if implementation=='cached':f=features(wave,sources)
                    else:f=np.concatenate([Fu.feats(wave[i*10:(i+1)*10,None,:],4000,float(bearing(n)['fr']),ORDERS) for i,n in enumerate(sources)])
                    stop=time.perf_counter()
                    if repeat:records[implementation].append(dict(sampling_decode_seconds=middle-start,feature_seconds=stop-middle,total_seconds=stop-start))
            for implementation,timings in records.items():
                record=dict(kind=kind,implementation=implementation,evaluations=16,cache_setup_seconds=setup if implementation=='cached' else 0.,measurements=timings)
                for metric in timings[0]:
                    record[metric+'_median']=float(np.median([r[metric] for r in timings]))
                    record[metric+'_p95']=float(np.quantile([r[metric] for r in timings],.95))
                profiles.append(record)
    result=dict(device='cpu',threads=1,batch_waveforms=120,target='1_1',seed=11,warmups=1,repeats=10,
                scope='Paired local warm CPU benchmark; setup measured separately; not factory hardware',
                includes_loading=False,includes_training=False,includes_classifier=False,
                checks=checks,rows=profiles,verified_model_folds=78,all_features_and_scores_exact=True,
                sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ('s3_cached_features.py','s3_cached_profile.py','results/s3/spectral.json')})
    (OUT/'cpu_cached.json').write_text(json.dumps(result,indent=2));print('Cached CPU: exact replay on 78 model folds',flush=True)


if __name__=='__main__':main()
