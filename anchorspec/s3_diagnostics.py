"""Source-space failure audit and local CPU profile, separate from test scoring."""
import os
for variable in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ.setdefault(variable,'1')
import hashlib
import json
import pickle
import platform
import time
import numpy as np
import torch
from sklearn.preprocessing import StandardScaler
from s3_cpu_benchmark import ROOT,OUT,DATA,prepare
from s3_spectral import ResidualGenerator,SmallNetwork
from s_latent import schedule
from u_natural import LABEL,ORDERS,bearing
import funnel as Fu


def audit():
    records=[];inputs={}
    for target in LABEL:
        sources=[n for n in LABEL if n!=target];x=np.concatenate([bearing(n)['terminal_features'] for n in sources])
        labels=np.repeat([LABEL[n] for n in sources],10);scaler=StandardScaler().fit(x);z=scaler.transform(x)
        centroids=np.array([z[labels==c].mean(0) for c in (1,2,4)])
        donors=np.array([z[i*10:(i+1)*10].mean(0) for i in range(12)])
        for seed in (11,29,47):
            values={'real':x}
            for experiment in ('s','s2'):
                path=ROOT.parent/f'data/{experiment}_generation/{target}_{seed}/generated_features.npz'
                inputs[path.relative_to(ROOT.parent).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
                with np.load(path) as f:
                    for kind in ('flow','diffusion','pca_bootstrap'):
                        values[experiment+'_'+kind]=np.concatenate([f[n+':'+kind][:10] for n in sources])
            path=DATA/f'{target}_{seed}/features.npz'
            inputs[path.relative_to(ROOT.parent).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
            with np.load(path) as f:
                for kind in ('bootstrap','gaussian','flow','diffusion'):
                    key=f'spectral_{kind}_half';values[key]=np.concatenate([f[n+':'+key] for n in sources])
            for method,a in values.items():
                za=scaler.transform(a)
                nearest=np.array((1,2,4))[np.sum((za[:,None,:]-centroids[None,:,:])**2,axis=2).argmin(1)]
                delta=za-np.repeat(donors,10,axis=0)
                for c in (1,2,4):
                    take=labels==c
                    records.append(dict(target=target,seed=seed,method=method,fault_class=c,
                        source_centroid_label_agreement=float(np.mean(nearest[take]==c)),
                        standardized_donor_distance=float(np.sqrt(np.mean(delta[take]**2))),
                        standardized_temporal_distance=float(np.sqrt(np.mean(delta[take,:4]**2))),
                        standardized_envelope_order_distance=float(np.sqrt(np.mean(delta[take,28:40]**2))),
                        mean_kurtosis=float(a[take,1].mean()),mean_ftf_log_peak_ratio=float(a[take,31:34].mean())))
    summary=[]
    for method in dict.fromkeys(r['method'] for r in records):
        for c in (1,2,4):
            chosen=[r for r in records if r['method']==method and r['fault_class']==c]
            summary.append(dict(method=method,fault_class=c,**{k:float(np.mean([r[k] for r in chosen])) for k in list(chosen[0])[4:]}))
    result=dict(scope='Descriptive source-training-feature audit; no independent label validation; heavily overlapping donors',
                rows=records,summary=summary,sha256=inputs)
    (OUT/'failure_audit.json').write_text(json.dumps(result,indent=2));return result


def profile():
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    sources,waves,codec,indices,limits,_=prepare('1_1',11);anchors=waves[indices];query=codec.conditions[indices]
    results=[];hashes={}
    for kind in ('flow','diffusion'):
        path=DATA/'1_1_11'/f'{kind}.pt';hashes[path.relative_to(ROOT.parent).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
        saved=torch.load(path,map_location='cpu',weights_only=True)
        generator=ResidualGenerator(kind,11);generator.model=SmallNetwork(saved['dimensions'],saved['condition_dimensions'])
        generator.model.load_state_dict(saved['state_dict']);generator.model.eval()
        generator.lo=saved['train_lo'];generator.hi=saved['train_hi'];generator.beta,generator.bar=schedule()
        reference,_=codec.apply(anchors,generator.sample(query,20261117,16)*codec.scale,.5,limits)
        for steps in (4,8,16,32):
            timings=[]
            for repetition in range(11):
                begin=time.perf_counter();residual=generator.sample(query,20261117,steps)*codec.scale
                generated,_=codec.apply(anchors,residual,.5,limits);decoded=time.perf_counter()
                f=np.concatenate([Fu.feats(generated[i*10:(i+1)*10,None,:],4000,float(bearing(n)['fr']),ORDERS) for i,n in enumerate(sources)])
                end=time.perf_counter();assert f.shape==(120,45) and np.isfinite(f).all()
                if repetition:timings.append(dict(sampling_decode_seconds=decoded-begin,feature_seconds=end-decoded,total_seconds=end-begin))
            record=dict(kind=kind,evaluations=steps,batch=120,parameters=saved['parameters'],checkpoint_bytes=path.stat().st_size,
                        waveform_relative_l2_vs_16=float(np.linalg.norm(generated-reference)/np.linalg.norm(reference)),measurements=timings)
            for metric in timings[0]:
                record[metric+'_median']=float(np.median([r[metric] for r in timings]))
                record[metric+'_p95']=float(np.quantile([r[metric] for r in timings],.95))
            results.append(record)
    result=dict(device='cpu',threads=1,platform=platform.platform(),processor=platform.processor(),torch=torch.__version__,
                target='1_1',seed=11,warmups=1,repeats=10,scope='Local warm execution; not a Pi or factory SLA',
                rows=results,sha256=hashes,classifier_accuracy_for_other_step_counts_measured=False)
    (OUT/'cpu_profile.json').write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    audit();profile();print('S3 source-space audit and CPU profile completed',flush=True)
