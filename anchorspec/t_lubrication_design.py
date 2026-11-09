"""Audit exact operating-condition overlap before a lubrication benchmark."""
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent
DATA=ROOT.parent/'data/open_sources/20742913'


def main():
    record=json.loads((DATA/'record.json').read_text())
    runs={};hashes={}
    for archive in record['files']:
        p=DATA/archive['key'].removesuffix('.zip')/'inventory.json'
        hashes[archive['key']]=hashlib.sha256(p.read_bytes()).hexdigest()
        for entry in json.loads(p.read_text()):
            name=entry['name']
            if not name.endswith('_Acc_Sensor_1.mat'):continue
            m=re.search(r'Test(\d+)_(NoOil|Oil\d+)_(\d+)-(\d+(?:,\d+)?)-(\d+)_Data_',name)
            if not m:raise ValueError('Unrecognized sensor member '+name)
            run=int(m[1]);info=dict(run=run,lubrication=m[2],amplitude_deg=float(m[3]),
                radial_load_kn=float(m[4].replace(',','.')),frequency_hz=float(m[5]))
            if run in runs and runs[run]!=info:raise ValueError('Within-run regime change')
            runs[run]=info
    if set(runs)!=set(range(1,9)):raise ValueError('Missing experimental run')
    regimes={}
    for row in runs.values():
        key=(row['amplitude_deg'],row['radial_load_kn'],row['frequency_hz'])
        regimes.setdefault(key,[]).append(row)
    groups=[]
    for key,rows in sorted(regimes.items()):
        oil=[r['run'] for r in rows if r['lubrication']!='NoOil']
        nooil=[r['run'] for r in rows if r['lubrication']=='NoOil']
        groups.append(dict(amplitude_deg=key[0],radial_load_kn=key[1],frequency_hz=key[2],
            lubricated_runs=sorted(oil),unlubricated_runs=sorted(nooil),
            leave_run_out_both_classes_in_training_possible=min(len(oil),len(nooil))>=2))
    result=dict(source='https://zenodo.org/records/20742913',runs=sorted(runs.values(),key=lambda x:x['run']),
        matched_regimes=groups,inventory_sha256=hashes,full_archive_checksum_verified=False,
        verdict='insufficient independent runs for matched-regime binary leave-run-out validation',
        notes=['Two bearings in one run share test conditions; hold out whole run.',
               'Lubrication treatment is not a time-resolved fault or healthy label.',
               'Oscillating needle bearings are not continuous-rotation ball bearings.',
               'Metadata audit only; no new classification score or raw waveform download.'])
    out=ROOT/'results/t';out.mkdir(exist_ok=True)
    (out/'lubrication_design.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(groups,indent=2))


if __name__=='__main__':main()
