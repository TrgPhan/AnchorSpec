"""CPU execution optimization; equivalent spectral interpolation and grouped features."""
import os
for variable in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ.setdefault(variable,'1')
import hashlib
import json
import time
import numpy as np
import torch
from s3_cpu_benchmark import ROOT,OUT,DATA,prepare
from s3_spectral import ResidualGenerator,SmallNetwork
from s_latent import schedule
from s_additive import additive_training
from u_natural import LABEL,ORDERS,bearing
from invariant_classifier import InvariantClassifier
import funnel as Fu


def decode(codec,anchors,residuals,strength,limits):
    """Linear interpolation has only two nonzero coefficients per FFT bin."""
    r=np.asarray(residuals,float)
    if not np.isfinite(r).all() or r.shape!=(len(anchors),codec.bands):raise ValueError('Invalid residual')
    bounded=np.clip(r,codec.lo,codec.hi)*strength
    coordinates=np.r_[0,codec.centers,1000,codec.fs/2]
    index=np.searchsorted(coordinates,codec.freq,side='right')-1
    index=np.clip(index,0,len(coordinates)-2)
    weight=(codec.freq-coordinates[index])/(coordinates[index+1]-coordinates[index])
    values=np.column_stack((bounded[:,0],bounded,np.zeros((len(bounded),2))))
    gain=np.exp(values[:,index]*(1-weight)+values[:,index+1]*weight)
    wave=np.fft.irfft(np.fft.rfft(anchors,axis=1)*gain,n=codec.samples,axis=1)
    wave-=wave.mean(1,keepdims=True)
    wave*=np.minimum(1,np.asarray(limits)/(np.abs(wave).max(1)+1e-15))[:,None]
    return wave


def grouped_features(waves,frequencies):
    """Batch all windows with the same speed, preserving input row order."""
    frequencies=np.asarray(frequencies,float)
    if frequencies.shape!=(len(waves),):raise ValueError('Invalid speeds')
    out=np.empty((len(waves),45))
    for frequency in np.unique(frequencies):
        take=frequencies==frequency
        out[take]=Fu.feats(waves[take,None,:],4000,float(frequency),ORDERS)
    return out


def load_model(folder,kind):
    saved=torch.load(folder/f'{kind}.pt',map_location='cpu',weights_only=True)
    model=ResidualGenerator(kind,saved['seed']);model.model=SmallNetwork(saved['dimensions'],saved['condition_dimensions'])
    model.model.load_state_dict(saved['state_dict']);model.model.eval()
    model.lo=saved['train_lo'];model.hi=saved['train_hi'];model.beta,model.bar=schedule()
    return model


def main():
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    evidence=json.loads((OUT/'spectral.json').read_text());comparisons=[];checks=[]
    for row in evidence['rows']:
        target,seed=row['target'],row['seed'];sources,waves,codec,indices,limits,_=prepare(target,seed)
        folder=DATA/f'{target}_{seed}';anchors=waves[indices];speeds=np.repeat([float(bearing(n)['fr']) for n in sources],10)
        with np.load(folder/'residuals.npz') as cache,np.load(folder/'features.npz') as stored:
            for kind in ('flow','diffusion'):
                generated=decode(codec,anchors,cache[kind],.5,limits)
                expected,_=codec.apply(anchors,cache[kind],.5,limits)
                np.testing.assert_allclose(generated,expected,rtol=1e-12,atol=1e-12)
                features=grouped_features(generated,speeds)
                reference=np.concatenate([stored[n+f':spectral_{kind}_half'] for n in sources])
                np.testing.assert_allclose(features,reference,rtol=1e-9,atol=1e-9)
                t=bearing(target);events=[(n,LABEL[n],bearing(n)['terminal_features']) for n in sources]
                derived={n:{'flow':features[i*10:(i+1)*10]} for i,n in enumerate(sources)}
                x,y,w,_=additive_training(t['healthy_features'][:5],events,derived,'flow',1.,.25)
                classifier=InvariantClassifier('rf',seed).fit(x,y,w)
                for stage in ('healthy','preterminal','terminal'):
                    test=t[stage+'_features'][5:] if stage=='healthy' else t[stage+'_features']
                    np.testing.assert_array_equal(classifier.predict_proba(test),row['scores'][f'spectral_{kind}_half:r1:a0.25'][stage]['raw_scores'])
                checks.append(dict(target=target,seed=seed,kind=kind,max_feature_error=float(np.abs(features-reference).max()),raw_scores_exact=True))
        if target!='1_1' or seed!=11:continue
        for kind in ('flow','diffusion'):
            model=load_model(folder,kind);query=codec.conditions[indices]
            for evaluations in (8,16):
                records={'original':[],'optimized':[]}
                for repeat in range(11):
                    # Alternate execution order to reduce simple warm-order bias.
                    order=('original','optimized') if repeat%2==0 else ('optimized','original')
                    for implementation in order:
                        start=time.perf_counter();residual=model.sample(query,20261117,evaluations)*codec.scale
                        if implementation=='optimized':wave=decode(codec,anchors,residual,.5,limits)
                        else:wave,_=codec.apply(anchors,residual,.5,limits)
                        middle=time.perf_counter()
                        if implementation=='optimized':features=grouped_features(wave,speeds)
                        else:features=np.concatenate([Fu.feats(wave[i*10:(i+1)*10,None,:],4000,float(bearing(n)['fr']),ORDERS) for i,n in enumerate(sources)])
                        stop=time.perf_counter()
                        if repeat:records[implementation].append(dict(sampling_decode_seconds=middle-start,feature_seconds=stop-middle,total_seconds=stop-start))
                for implementation,timings in records.items():
                    record=dict(kind=kind,evaluations=evaluations,implementation=implementation,measurements=timings)
                    for metric in timings[0]:
                        record[metric+'_median']=float(np.median([r[metric] for r in timings]))
                        record[metric+'_p95']=float(np.quantile([r[metric] for r in timings],.95))
                    comparisons.append(record)
    result=dict(device='cpu',threads=1,batch_waveforms=120,profile_target='1_1',profile_seed=11,
                warmups=1,repeats=10,includes_disk_loading=False,includes_classifier=False,
                checks=checks,rows=comparisons,verified_model_folds=78,raw_scores_exact=True,
                scope='Local CPU measurement, not target factory hardware',
                sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ('s3_fast_cpu.py','results/s3/spectral.json')})
    (OUT/'cpu_optimized.json').write_text(json.dumps(result,indent=2));print('CPU optimization: 78 model folds reproduced exactly',flush=True)


if __name__=='__main__':main()
