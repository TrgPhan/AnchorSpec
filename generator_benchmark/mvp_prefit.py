"""Train a missing DDPM checkpoint using ONLY train records, before freeze.

Useful while recovery samples earlier checkpoints on CPU. Atomic checkpoint
publication; no concurrent writing to the same completed checkpoint.
"""
import argparse
from pathlib import Path
import time

import torch

from deep_generators import DeepGenerator
from mvp_core import load_records
from mvp_run import read, real_training
from benchmark import write_json


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--release',type=Path,required=True)
    parser.add_argument('--seed',type=int,required=True)
    args=parser.parse_args();out=args.release.resolve()
    if (out/'FROZEN.json').exists(): raise RuntimeError('No training after freeze')
    dest=out/'development'/f'ddpm_{args.seed}.pt'
    if dest.exists(): raise FileExistsError(dest)
    records=load_records(read(out/'records.json'),{'train'})
    anchors,_,_,_=real_training(records)
    started=time.perf_counter()
    g=DeepGenerator('ddpm_prototype',anchors,args.seed,steps=read(out/'protocol.json')['deep_steps'])
    state={'state_dict':g.model.state_dict(),'scales':g.scales,'support':g.support,
           'fit_log':g.fit_log,'seed':args.seed,'method':g.method}
    temp=dest.with_suffix('.pt.tmp');torch.save(state,temp)
    if dest.exists(): raise FileExistsError('Another process already published checkpoint')
    temp.replace(dest)
    write_json(out/f'prefit_{args.seed}.json',{'seed':args.seed,'seconds':time.perf_counter()-started,
        'train_only':True,'purpose':'overlap CUDA training with earlier CPU sampling',
        'steps':g.fit_log['steps'],'file':str(dest)})
    print('PREFIT COMPLETE',args.seed,flush=True)


if __name__=='__main__': main()