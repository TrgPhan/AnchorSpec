"""Black-box CLI acceptance on the finalized release. No model tuning."""
import argparse
from pathlib import Path
import subprocess
import sys

import numpy as np

from generators import N
from mvp_core import ROOT, load_records
from mvp_run import read
from benchmark import write_json


def acceptance(release):
    output=release/'acceptance'
    output.mkdir(exist_ok=False)
    results=[]
    base=[sys.executable,str(ROOT/'mvp_cli.py')]
    def run(name,args,success):
        command=base+args+['--release',str(release)]
        completed=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
        (output/f'{name}.log').write_text(completed.stdout+completed.stderr,encoding='utf-8')
        passed=(completed.returncode==0)==success
        results.append({'test':name,'passed':passed,'exit_code':completed.returncode,
                        'expected_success':success,'command':command})
        write_json(output/'results.json',results)
        if not passed: raise RuntimeError(f'Acceptance failure: {name}')
    batch=output/'batch'
    run('generate',['generate','--label','inner','--count','16','--seed','832','--output',str(batch)],True)
    run('audit',['audit','--label','inner','--output',str(batch)],True)
    run('refuse_overwrite',['generate','--label','inner','--count','16','--output',str(batch)],False)
    run('refuse_new_rpm',['generate','--label','inner','--rpm','1200','--output',str(output/'bad_rpm')],False)
    run('refuse_new_fs',['generate','--label','inner','--fs','64000','--output',str(output/'bad_fs')],False)
    records=load_records(read(release/'records.json'),{'train'})
    fixture=np.concatenate([records[('train','inner')]['x'][:4],
                            np.zeros((1,N),np.float32),np.full((1,N),np.nan,np.float32)])
    np.save(output/'replay_input.npy',fixture)
    run('replay',['replay','--input',str(output/'replay_input.npy'),'--rpm','1797','--output',str(output/'replay.json')],True)
    result=read(output/'replay.json')
    if len(result['predictions'])!=6 or any(r['status']!='sensor_quality_failure' for r in result['predictions'][4:]):
        raise RuntimeError('Replay dropped or mislabeled invalid windows')
    run('replay_refuse_domain',['replay','--input',str(output/'replay_input.npy'),'--rpm','900','--output',str(output/'invalid_replay.json')],False)
    run('replay_refuse_overwrite',['replay','--input',str(output/'replay_input.npy'),'--rpm','1797','--output',str(output/'replay.json')],False)
    print(f'{len(results)} black-box acceptance cases passed; invalid replay rows retained')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--release',type=Path,required=True)
    acceptance(parser.parse_args().release.resolve())