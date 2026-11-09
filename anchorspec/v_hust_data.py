"""Download the HUST single-fault subset with publisher SHA256 verification."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import requests
from scipy.io import loadmat

ROOT=Path(__file__).resolve().parent
DATA=ROOT.parent/'data'/'hust_v'


def download():
    DATA.mkdir(parents=True,exist_ok=True)
    r=requests.get('https://data.mendeley.com/public-api/datasets/cbv7jyx4p9/files',
        params={'version':3,'folder_id':'72793f17-cac2-4cc6-ac18-2b047e0d45f8'},timeout=45)
    r.raise_for_status();inventory=r.json()
    selected=[f for f in inventory if re.fullmatch('[NIOB][5678]0[024]\\.mat',f['filename'])]
    if len(selected)!=48:raise ValueError('Unexpected publisher inventory')
    (DATA/'publisher.json').write_text(json.dumps(inventory,indent=2),encoding='utf8')
    def one(entry):
        path=DATA/entry['filename'];details=entry['content_details']
        for attempt in range(3):
            if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==details['sha256_hash']:break
            reply=requests.get(details['download_url'],timeout=60);reply.raise_for_status()
            if len(reply.content)!=entry['size'] or hashlib.sha256(reply.content).hexdigest()!=details['sha256_hash']:
                if attempt==2:raise ValueError('Publisher checksum mismatch')
                continue
            path.write_bytes(reply.content);break
        return dict(filename=path.name,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),publisher_sha256_verified=True)
    manifest=dict(source='https://data.mendeley.com/datasets/cbv7jyx4p9/3',license='CC BY 4.0',files=[])
    with ThreadPoolExecutor(3) as pool:
        for row in pool.map(one,selected):
            manifest['files'].append(row)
            (DATA/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
            print('HUST',len(manifest['files']),'/48',row['filename'],flush=True)
    for name in ('N500.mat','I500.mat'):
        d=loadmat(DATA/name,simplify_cells=True)
        print(name,{k:(str(type(v)),getattr(v,'shape',None),str(v)[:200]) for k,v in d.items() if not k.startswith('__')},flush=True)


if __name__=='__main__':download()
