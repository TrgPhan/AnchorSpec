"""Local sampling timing of four frozen prototypes; not a factory or Pi benchmark."""
import os
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('MKL_NUM_THREADS','1')
import hashlib
import json
import pickle
import platform
import time
from pathlib import Path
import numpy as np
import torch
from s_latent import LatentGenerator,Network,schedule
from u_natural import bearing,LABEL,ORDERS
import funnel as Fu

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results/factory_benchmark'


def main():
    OUT.mkdir(exist_ok=True);torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    rows=[];inputs={};target='1_1';seed=11
    for experiment in ('s','s2'):
        folder=ROOT.parent/f'data/{experiment}_generation/{target}_{seed}'
        codec_path=folder/'codec.pkl';inputs[str(codec_path.relative_to(ROOT.parent))]=hashlib.sha256(codec_path.read_bytes()).hexdigest()
        with codec_path.open('rb') as f:state=pickle.load(f)
        conditions=[]
        for n in state['sources']:
            s=bearing(n);rms=np.sqrt(np.mean(s['healthy'][:5]**2))
            continuous=state['condition_scaler'].transform([[float(s['fr']),np.log(max(rms,1e-12))]])[0]
            c=np.r_[np.eye(3)[{1:0,2:1,4:2}[LABEL[n]]],continuous]
            conditions.extend([c]*10)
        conditions=np.asarray(conditions,np.float32)
        for kind in ('flow','diffusion'):
            path=folder/f'{kind}.pt';digest=hashlib.sha256(path.read_bytes()).hexdigest();inputs[str(path.relative_to(ROOT.parent))]=digest
            saved=torch.load(path,map_location='cpu',weights_only=True)
            model=LatentGenerator(kind,seed);model.model=Network(saved['dimensions'],saved['condition_dimensions'])
            model.model.load_state_dict(saved['state_dict']);model.model.eval()
            model.lo=saved['train_lo'];model.hi=saved['train_hi'];model.beta,model.bar=schedule()
            measurements=[]
            for repeat in range(11):
                start=time.perf_counter();z=model.sample(conditions,20261106+repeat)
                wave,_=state['codec'].decode(z);after=time.perf_counter()
                features=np.concatenate([Fu.feats(wave[i*10:(i+1)*10,None,:],4000,float(bearing(n)['fr']),ORDERS) for i,n in enumerate(state['sources'])])
                stop=time.perf_counter()
                assert features.shape==(120,45) and np.isfinite(features).all()
                if repeat:measurements.append(dict(sampling_decode_seconds=after-start,feature_seconds=stop-after,total_seconds=stop-start))
            row=dict(experiment=experiment,method=kind,source_target=target,source_seed=seed,batch_waveforms=120,
                waveform_samples=4000,sample_rate_hz=4000,warmups=1,repeats=10,
                checkpoint_bytes=path.stat().st_size,parameters=sum(p.numel() for p in model.model.parameters()),
                measurements=measurements)
            for metric in measurements[0]:
                values=[m[metric] for m in measurements]
                row[metric+'_median']=float(np.median(values));row[metric+'_p95']=float(np.quantile(values,.95))
            rows.append(row);print(experiment,kind,round(row['sampling_decode_seconds_median'],4),'seconds per120 windows',flush=True)
            assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    result=dict(date='2026-11-06',scope='one fixed fold per model; warm in-process CPU benchmark',
        device='cpu',threads=1,platform=platform.platform(),processor=platform.processor(),python=platform.python_version(),
        torch=torch.__version__,rows=rows,sha256=inputs,includes_training=False,includes_disk_loading=False,
        includes_classifier_inference=False,raspberry_pi_measured=False,independent_factory_sessions=0)
    (OUT/'sampling_profile.json').write_text(json.dumps(result,indent=2),encoding='utf8')


if __name__=='__main__':main()
