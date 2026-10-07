"""Offline local CLI; explicitly limited to CWRU/SKF6205 12kHz windows."""
import argparse
import json
from pathlib import Path

import numpy as np

from generators import Generator, LABELS, FS
from mvp_core import (sha, load_records, export_library, audit_library,
                      valid_rows, detector_features, CLASSES)
from mvp_run import read, checkpoint_read, score_model
from benchmark import write_json
from mvp_validate import validate_library


def verify(release):
    inventory=read(release/'integrity.json')
    for relative,expected in inventory['files'].items():
        path=(release/relative).resolve()
        if not path.is_relative_to(release.resolve()): raise ValueError('Unsafe manifest path')
        if sha(path)!=expected: raise ValueError(f'Integrity failure: {path}')
    return {'files_verified':len(inventory['files']),'all_hashes_match':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['verify','generate','audit','replay'])
    parser.add_argument('--release',type=Path,required=True)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--label',choices=LABELS)
    parser.add_argument('--count',type=int,default=128)
    parser.add_argument('--seed',type=int,default=901)
    parser.add_argument('--input',type=Path)
    parser.add_argument('--rpm',type=float)
    parser.add_argument('--fs',type=int,default=FS)
    parser.add_argument('--dataset',choices=['CWRU'],default='CWRU')
    args=parser.parse_args(); release=args.release.resolve()
    if args.command=='verify':
        print(json.dumps(verify(release),indent=2));return
    if args.fs!=FS: parser.error('Only CWRU 12000Hz supported; no implicit fs/geometry transfer')
    if args.command in ('generate','audit'):
        if not args.label or not args.output: parser.error('--label and --output required')
        records=load_records(read(release/'records.json'),{'train'})
        anchors={k:records[('train',k)]['x'][:8] for k in LABELS}
        if args.command=='generate':
            if args.rpm is not None: parser.error('Cannot request new RPM: local anchor-condition only')
            bg=records[('train','healthy')]['x'][:20]
            rpms={k:records[('train',k)]['rpm'] for k in LABELS}
            g=Generator('constrained_surrogate',anchors,bg,args.seed,rpms)
            export_library(g,anchors[args.label],args.label,args.count,args.seed,args.output,
                           records[('train',args.label)]['source'],rpms[args.label])
        print(json.dumps(validate_library(args.output,anchors[args.label]),indent=2));return
    if args.input is None or args.output is None or args.rpm is None:
        parser.error('replay requires --input .npy --output new.json --rpm')
    if args.output.exists(): parser.error('Existing replay output refused')
    if not 1720<=args.rpm<=1810:
        parser.error('Unsupported CWRU speed domain; no prediction issued')
    freeze=read(release/'FROZEN.json'); name=freeze['selected']; seed=11
    ref=freeze['models'][f'{name}:{seed}']
    state=checkpoint_read(ref['file'],ref['sha256'])
    threshold=next(r['threshold'] for r in read(release/'final/thresholds.json') if r['variant']==name and r['seed']==seed)
    x=np.load(args.input,allow_pickle=False); valid=valid_rows(x)
    predictions=[]; probabilities=np.zeros((len(x),4)); scores=np.zeros(len(x))
    if valid.any(): probabilities[valid],scores[valid]=score_model(state['model'],detector_features(x[valid],args.rpm))
    for i in range(len(x)):
        alarm=bool(valid[i] and scores[i]>threshold)
        status='sensor_quality_failure' if not valid[i] else 'known_fault_alarm' if alarm else 'no_alarm'
        # Classifier mechanism is a separate hypothesis, not an unknown detector.
        mechanism=CLASSES[1+np.argmax(probabilities[i,1:])] if alarm else None
        predictions.append({'window':i,'status':status,'mechanism_hypothesis':mechanism,
            'fault_score':float(scores[i]) if valid[i] else None,'threshold':threshold,
            'probabilities':probabilities[i].tolist() if valid[i] else None})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    write_json(args.output,{'source':str(args.input.resolve()),'source_sha256':sha(args.input),
        'model':name,'seed':seed,'dataset_asserted_by_user':'CWRU','fs_hz':FS,'rpm':args.rpm,
        'coverage':float(valid.mean()) if len(valid) else 0.,'predictions':predictions,
        'not_claimed':['unknown mechanism detection','DENSO validation','calibrated fault probability','early warning']})
    print(f'Replayed {len(x)} windows; {int((~valid).sum())} sensor failures; {args.output}')


if __name__=='__main__':
    main()