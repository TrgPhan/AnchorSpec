"""Selective XJTU mirror acquisition, ZIP CRC plus recorded local SHA256."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import zipfile
import requests
from z_open_data import RemoteDirectory,member_download

ROOT=Path(__file__).resolve().parent
DATA=ROOT.parent/'data/xjtu_u'
URL='https://kr0k0tsch.de/rul-datasets/XJTU-SY.zip'
LABEL={'1_1':2,'1_2':2,'1_3':2,'1_4':4,'2_1':1,'2_2':2,'2_3':4,'2_4':2,'2_5':2,'3_1':2,'3_3':1,'3_4':1,'3_5':2}
COUNTS={'1_1':123,'1_2':161,'1_3':158,'1_4':122,'1_5':52,'2_1':491,'2_2':161,'2_3':533,'2_4':42,'2_5':339,'3_1':2538,'3_2':2496,'3_3':371,'3_4':1515,'3_5':114}


def main():
    DATA.mkdir(exist_ok=True)
    with zipfile.ZipFile(RemoteDirectory(URL,5448862369)) as z:entries=z.infolist()
    selected=[]
    for name in LABEL:
        rows=[r for r in entries if f'/Bearing{name}/' in r.filename and r.filename.endswith('.csv')]
        rows.sort(key=lambda r:int(Path(r.filename).stem))
        if len(rows)!=COUNTS[name] or [int(Path(r.filename).stem) for r in rows]!=list(range(1,len(rows)+1)):
            raise ValueError('Mirror inventory disagrees with author introduction')
        selected += [(name,'healthy' if i<10 else 'preterminal' if i<len(rows)-10 else 'terminal',r)
                     for i,r in enumerate(rows) if i<10 or i>=len(rows)-20]
    print('Selected',len(selected),'snapshots',sum(r.compress_size for n,s,r in selected)/1e6,'compressed MB',flush=True)
    if len(selected)!=390:raise ValueError('Unexpected selection')
    def one(task):
        name,stage,entry=task;folder=DATA/name;folder.mkdir(exist_ok=True)
        for attempt in range(3):
            try:
                row=member_download(URL,entry,folder)
                return dict(bearing=name,stage=stage,index=int(Path(entry.filename).stem),**row)
            except (requests.RequestException,ValueError):
                if attempt==2:raise
    manifest=dict(author_source='https://github.com/WangBiaoXJTU/xjtu-sy-bearing-datasets',mirror=URL,
        publisher_sha_verified=False,full_archive_checksum_verified=False,members=[])
    with ThreadPoolExecutor(6) as pool:
        for i,row in enumerate(pool.map(one,selected),1):
            manifest['members'].append(row)
            (DATA/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
            if i%30==0:print('XJTU acquisition',i,'/390',flush=True)


if __name__=='__main__':main()
