"""Generate measured-fault variations using healthy-only spectral transport."""
import numpy as np
from scipy import signal
from scipy.ndimage import gaussian_filter1d
from cheap_sensor import output_stage,CheapSensor


def healthy_log_spectrum(windows,fs=4000):
    x=np.asarray(windows,float)
    if x.ndim!=2 or not len(x) or x.shape[1]<1024 or not np.isfinite(x).all():
        raise ValueError('Invalid healthy windows')
    f,p=signal.welch(x-x.mean(1,keepdims=True),fs,nperseg=1024,axis=1)
    p=p.mean(0);floor=max(float(p.max())*1e-6,1e-24)
    return f,gaussian_filter1d(np.log(np.maximum(p,floor)),48/(f[1]-f[0]))


def transfer_gain(source_healthy,target_healthy,fs=4000,n=4000):
    f,s=healthy_log_spectrum(source_healthy,fs)
    _,t=healthy_log_spectrum(target_healthy,fs)
    frequencies=np.fft.rfftfreq(n,1/fs)
    gain=np.exp(np.interp(frequencies,f,np.clip((t-s)/2,np.log(.5),np.log(2.))))
    gain[frequencies>1000]=1.
    return gain


def warp_speed(x,ratio):
    if not np.isfinite(ratio) or not .8<=ratio<=1.25:raise ValueError('Speed ratio outside supported range')
    if ratio==1:return np.asarray(x,float).copy()
    return np.interp(np.arange(len(x))*ratio,np.arange(len(x)),x,period=len(x))


def generate(fault,source_healthy,target_healthy,fr_source,fr_target,rng,count=64):
    fault,hs,ht=[np.asarray(a,float) for a in (fault,source_healthy,target_healthy)]
    if any(a.ndim!=2 or not len(a) or a.shape[1]!=4000 or not np.isfinite(a).all() for a in (fault,hs,ht)):
        raise ValueError('Need finite one-second 4kHz waveforms')
    if count<1 or not np.isfinite(fr_source) or fr_source<=0:raise ValueError('Invalid generation arguments')
    gain=transfer_gain(hs,ht)
    source_index=rng.integers(len(fault),size=count)
    source_healthy_index=rng.integers(len(hs),size=count)
    target_healthy_index=rng.integers(len(ht),size=count)
    shifts=rng.integers(4000,size=count);a=rng.uniform(.35,1.,size=count)
    arrays={k:[] for k in ('severity','transport','transport_mix')}
    for i,index in enumerate(source_index):
        x=np.roll(fault[index],shifts[i]);x=x-x.mean()
        moved=np.fft.irfft(np.fft.rfft(warp_speed(x,fr_target/fr_source))*gain,n=4000)
        arrays['severity'].append(np.sqrt(a[i])*x+np.sqrt(1-a[i])*hs[source_healthy_index[i]])
        arrays['transport'].append(moved)
        arrays['transport_mix'].append(np.sqrt(a[i])*moved+np.sqrt(1-a[i])*ht[target_healthy_index[i]])
    meta=dict(source_indices=source_index.tolist(),source_healthy_indices=source_healthy_index.tolist(),
        target_healthy_indices=target_healthy_index.tolist(),mix_fraction=a.tolist(),
        gain_min=float(gain.min()),gain_max=float(gain.max()),clipping={})
    for kind,rows in arrays.items():
        raw=np.stack(rows);meta['clipping'][kind]=float((np.abs(raw)>=8).mean())
        arrays[kind]=output_stage(raw,CheapSensor())
    return arrays,meta
