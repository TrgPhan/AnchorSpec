"""Acquire and inspect the previously unused KAIST load benchmark."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import zipfile
import requests
from z_open_data import RemoteDirectory, member_download

ROOT=Path(__file__).resolve().parent
DATA=ROOT.parent/'data'/'kaist_w'


def download():
    DATA.mkdir(parents=True,exist_ok=True)
    r=requests.get('https://data.mendeley.com/public-api/datasets/ztmf3m7h5x/files',
                   params={'version':6,'folder_id':'root'},timeout=60)
    r.raise_for_status()
    meta=next(f for f in r.json() if f['filename']=='vibration.zip')
    info=meta['content_details'];url=info['download_url']
    with zipfile.ZipFile(RemoteDirectory(url,info['size'])) as archive:
        selected=[v for v in archive.infolist() if v.filename.endswith('.mat') and
                  any(s in v.filename for s in ('Normal','BPFI','BPFO'))]
    if len(selected)!=21:raise ValueError('Unexpected source inventory')
    (DATA/'publisher.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
    manifest=dict(source='https://data.mendeley.com/datasets/ztmf3m7h5x/6',license='CC BY 4.0',
                  full_archive_checksum_verified=False,members=[])
    def one(entry):
        for attempt in range(3):
            try:return member_download(url,entry,DATA)
            except (requests.RequestException,ValueError):
                if attempt==2:raise
                print('retry',entry.filename,attempt+1,flush=True)
    with ThreadPoolExecutor(3) as pool:
        for member in pool.map(one,selected):
            manifest['members'].append(member)
            (DATA/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    print('KAIST acquired',len(manifest['members']),flush=True)


if __name__=='__main__':download()
