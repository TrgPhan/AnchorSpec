"""Common analytic-phase rotation preserves envelope before sensor output."""
import numpy as np
from cheap_sensor import CheapSensor,output_stage


def rotate(x,phase):
    x=np.asarray(x,float)
    if x.ndim!=1 or len(x)<4 or not np.isfinite(x).all() or not np.isfinite(phase):
        raise ValueError('Finite one-dimensional waveform and phase required')
    x=x-x.mean();z=np.fft.rfft(x)
    end=-1 if len(x)%2==0 else None
    z[1:end]*=np.exp(1j*phase)
    return np.fft.irfft(z,n=len(x))


def generate(windows,rng,count=64):
    windows=np.asarray(windows,float)
    if windows.ndim!=2 or windows.shape[1]!=4000 or not len(windows) or count<1:
        raise ValueError('One-second 4kHz windows required')
    indices=rng.integers(len(windows),size=count);phases=rng.uniform(-np.pi,np.pi,size=count)
    raw=np.stack([rotate(windows[i],p) for i,p in zip(indices,phases)])
    meta=dict(source_indices=indices.tolist(),phases=phases.tolist(),clipping_fraction=float((np.abs(raw)>=8).mean()))
    return output_stage(raw,CheapSensor()),meta
