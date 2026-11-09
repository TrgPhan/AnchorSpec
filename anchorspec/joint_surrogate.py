"""Shared analytic phase rotation with an audited sensor-bound identity fallback."""
import numpy as np
from cheap_sensor import CheapSensor,output_stage


def rotate_pair(pair,phases):
    pair=np.asarray(pair,float);phases=np.asarray(phases,float)
    if pair.ndim!=2 or pair.shape[1]<4 or phases.shape not in ((),(pair.shape[0],)) or not np.isfinite(pair).all() or not np.isfinite(phases).all():
        raise ValueError('Finite axes-by-time and common or per-axis phase required')
    z=np.fft.rfft(pair-pair.mean(1,keepdims=True),axis=1)
    end=-1 if pair.shape[1]%2==0 else None
    z[:,1:end]*=np.exp(1j*phases).reshape(-1,1)
    return np.fft.irfft(z,n=pair.shape[1],axis=1)


def generate(pairs,rng,sensor:CheapSensor,count=64):
    pairs=np.asarray(pairs,float)
    if pairs.ndim!=3 or pairs.shape[2]!=4000 or pairs.shape[1]<2 or not len(pairs) or not np.isfinite(pairs).all():
        raise ValueError('Need finite paired one-second4kHz windows')
    if sensor.fs_out!=4000 or sensor.range_g is None or count<1 or np.max(np.abs(pairs))>sensor.range_g:
        raise ValueError('Input does not satisfy declared sensor contract')
    indices=rng.integers(len(pairs),size=count);phases=rng.uniform(-np.pi,np.pi,(count,pairs.shape[1]))
    arrays={m:[] for m in ('independent_phase','joint_phase')};fallback={m:[] for m in arrays}
    for i,index in enumerate(indices):
        source=pairs[index]
        for method in arrays:
            proposal=rotate_pair(source,phases[i,0] if method=='joint_phase' else phases[i])
            rejected=bool(np.max(np.abs(proposal))>sensor.range_g)
            arrays[method].append(source.copy() if rejected else output_stage(proposal,sensor))
            fallback[method].append(rejected)
    return {m:np.stack(a) for m,a in arrays.items()},dict(source_indices=indices.tolist(),phases=phases.tolist(),
        identity_fallback={m:float(np.mean(a)) for m,a in fallback.items()},range_g=sensor.range_g)
