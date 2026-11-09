"""Replay the evaluated CPU generator from local XJTU checkpoints."""
import os
for variable in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ.setdefault(variable,'1')
import argparse
import hashlib
import json
import time
import numpy as np
import torch
from s3_cpu_benchmark import ROOT,OUT,DATA,prepare
from s3_cached_features import CachedDecoder,extract
from s3_fast_cpu import load_model
from u_natural import LABEL,ORDERS,bearing


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',choices=list(LABEL),default='1_1',help='Held-out bearing, excluded from the source library')
    parser.add_argument('--seed',type=int,choices=(11,29,47),default=11)
    parser.add_argument('--kind',choices=('flow','diffusion'),default='flow')
    parser.add_argument('--output',default=str(ROOT.parent/'data/s3_cpu_export'))
    args=parser.parse_args();torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    from pathlib import Path
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    sources,waves,codec,indices,limits,_=prepare(args.target,args.seed)
    folder=DATA/f'{args.target}_{args.seed}';model=load_model(folder,args.kind)
    begin=time.perf_counter();decoder=CachedDecoder(codec,waves[indices],limits)
    setup=time.perf_counter()-begin;begin=time.perf_counter()
    residual=model.sample(codec.conditions[indices],args.seed+20261106,16)*codec.scale
    generated=decoder(residual,.5);middle=time.perf_counter()
    features=np.concatenate([extract(generated[i*10:(i+1)*10],4000,float(bearing(n)['fr']),ORDERS) for i,n in enumerate(sources)])
    stop=time.perf_counter()
    # Exact feature replay is required for this fixed benchmark export.
    with np.load(folder/'features.npz') as f:
        expected=np.concatenate([f[n+f':spectral_{args.kind}_half'] for n in sources])
    np.testing.assert_array_equal(features,expected)
    stem=f'{args.target}_{args.seed}_{args.kind}_16steps'
    path=output/(stem+'.npz')
    np.savez_compressed(path,waveforms=generated,features=features,labels=np.repeat([LABEL[n] for n in sources],10),
                        donors=np.repeat(sources,10),source_window_indices=indices%10)
    meta=dict(scope='Public-data research augmentation; not a factory-qualified generator',device='cpu',threads=1,
              held_out_target=args.target,seed=args.seed,kind=args.kind,evaluations=16,strength=.5,
              sources=sources,synthetic_windows=120,independent_source_bearings=12,exact_benchmark_features=True,
              cache_setup_seconds=setup,sampling_decode_seconds=middle-begin,feature_seconds=stop-middle,
              checkpoint_sha256=hashlib.sha256((folder/f'{args.kind}.pt').read_bytes()).hexdigest(),
              output_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),output=str(path.resolve()))
    (output/(stem+'.json')).write_text(json.dumps(meta,indent=2));print(json.dumps(meta),flush=True)


if __name__=='__main__':main()
