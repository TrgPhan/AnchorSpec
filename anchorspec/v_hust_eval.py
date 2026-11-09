"""HUST adapter accepting verified, naturally shorter publisher recordings."""
from functools import lru_cache
import hashlib
import numpy as np
from scipy.io import loadmat
import v_external as E


@lru_cache(None)
def signals(dataset,unit):
    if dataset!='hust':raise ValueError('HUST adapter only')
    out={};metadata={}
    for p in sorted((E.ROOT.parent/'data'/'hust_v').glob('*.mat')):
        d=loadmat(p,simplify_cells=True);native=np.asarray(d['data'],float)
        if native.ndim!=1 or not np.isfinite(native).all():raise ValueError('Unexpected waveform schema')
        x=native[:512000]/(9.80665 if unit=='mks' else 1.)
        seed=int(hashlib.sha256(p.name.encode()).hexdigest()[:8],16)
        y=E.simulate(x,51200,E.CheapSensor(),np.random.default_rng(seed))
        healthy=p.stem.startswith('N');y=y[4000:24000] if healthy else y[4000:]
        w=E.windows(y,4000);w=w-w.mean(1,keepdims=True)
        if len(w)<(5 if healthy else 3):raise ValueError('Insufficient stationary recording')
        a,b,diam,n=E.GEO[int(p.stem[1])];orders=E.Bearing(n,diam,(a+b)/2,0).orders()
        out[p.stem]=dict(w=w,f=E.Fu.feats(w[:,None,:],4000,float(d['fs']),orders),fr=float(d['fs']),orders=orders)
        metadata[p.stem]=dict(native_samples=len(native),native_duration_seconds=len(native)/51200,
            windows=len(w),native_clip8_fraction=float((np.abs(x)>=8).mean()),shaft_hz=float(d['fs']))
    return out,metadata


original_hashes=E.hashes
def hashes():
    out=original_hashes()
    for n in ('v_hust_eval.py','PROTOCOL_V_HUST_SCHEMA.md'):
        out[n]=hashlib.sha256((E.ROOT/n).read_bytes()).hexdigest()
    return out


E.signals=signals
E.hashes=hashes
E.CACHE=E.ROOT.parent/'data'/'v_hust_external'

if __name__=='__main__':E.main()
