"""Equivalent 45 features with cached signal-processing constants; CPU only."""
from functools import lru_cache
import numpy as np
from scipy import signal,stats


@lru_cache(maxsize=64)
def plan(samples,fs,fr,orders_tuple,max_hz):
    orders=dict(orders_tuple);freq=np.fft.rfftfreq(samples,1/fs)
    tol=max(.02*fr*max(orders.values()),2*freq[1])
    masks=[np.abs(freq-o*fr*h)<=tol for o in (1.,*orders.values()) for h in range(1,4)]
    filters=[signal.butter(4,(lo,hi),'bandpass',fs=fs,output='sos')
             for lo,hi in ((10,max_hz),(10,.3*max_hz),(.3*max_hz,.6*max_hz),(.6*max_hz,max_hz))]
    return signal.get_window('hann',samples),masks,filters,fs/(orders['bpfo']*fr)


def extract(x,fs,fr,orders,max_hz=1000.):
    x=np.asarray(x,float);x=x-x.mean(1,keepdims=True);n=x.shape[1]
    win,masks,filters,bpfo_period=plan(n,fs,fr,tuple(orders.items()),max_hz)
    rms=np.sqrt(np.mean(x**2,1))+1e-15;peak=np.max(np.abs(x),1)
    amp=[peak/rms,stats.kurtosis(x,axis=1),stats.skew(x,axis=1),rms/(np.mean(np.abs(x),1)+1e-15)]
    f,p=signal.welch(x,fs,nperseg=min(1024,n),axis=1);inband=f<=max_hz;total=p[:,inband].sum(1)+1e-15
    edges=np.linspace(0,max_hz,11)
    bands=[np.log(p[:,(f>=a)&(f<b)].sum(1)/total+1e-15) for a,b in zip(edges[:-1],edges[1:])]
    centroid=(p[:,inband]*f[inband]).sum(1)/total
    spread=np.sqrt((p[:,inband]*(f[inband]-centroid[:,None])**2).sum(1)/total)
    def harmonics(spec):
        floor=np.median(spec,axis=1)+1e-15
        return [np.log(np.maximum(spec[:,mask].max(1),1e-15)/floor) for mask in masks]
    raw=harmonics(np.abs(np.fft.rfft(x*win,axis=1))**2)
    envs=[];kurts=[]
    for coefficients in filters:
        y=signal.sosfiltfilt(coefficients,x,axis=1);e=np.abs(signal.hilbert(y,axis=1))
        envs.append(e);kurts.append(stats.kurtosis(e,axis=1))
    kurts=np.array(kurts);best=np.argmax(kurts,axis=0);env=np.array(envs)[best,np.arange(len(x))]
    order_env=harmonics(np.abs(np.fft.rfft((env-env.mean(1,keepdims=True))*win,axis=1))**2)
    mad=np.median(np.abs(x),1)+1e-15;count=[];cv=[];ratio=[]
    for row,m in zip(x,mad):
        peaks,_=signal.find_peaks(np.abs(row),height=4*m,distance=max(1,int(.002*fs)))
        count.append(len(peaks)/(n/fs))
        if len(peaks)>2:
            gaps=np.diff(peaks);cv.append(gaps.std()/gaps.mean());ratio.append(np.median(gaps)/bpfo_period)
        else:cv.append(0.);ratio.append(0.)
    result=np.column_stack(amp+bands+[centroid,spread]+raw+order_env+[best.astype(float),kurts.max(0)]+[count,cv,ratio])
    if not np.isfinite(result).all():raise ValueError('Non-finite features')
    return result


class CachedDecoder:
    """Cache the measured-anchor FFT once; its creation cost is measured separately."""
    def __init__(self,codec,anchors,limits):
        self.codec=codec;self.spectrum=np.fft.rfft(anchors,axis=1);self.limits=np.asarray(limits)

    def __call__(self,residual,strength=.5):
        c=self.codec;bounded=np.clip(residual,c.lo,c.hi)*strength
        gain=np.exp(bounded@c.interpolation)
        wave=np.fft.irfft(self.spectrum*gain,n=c.samples,axis=1);wave-=wave.mean(1,keepdims=True)
        wave*=np.minimum(1,self.limits/(np.abs(wave).max(1)+1e-15))[:,None]
        return wave
