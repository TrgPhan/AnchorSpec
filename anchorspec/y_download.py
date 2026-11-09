"""Download only UORED v5 MATLAB files, verify publisher SHA256, cache locally."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / 'data' / 'uored' / 'mat'
API = 'https://data.mendeley.com/public-api/datasets/y2px5tg92h'


def get_json(url, **params):
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    obj = r.json()
    if not isinstance(obj, list):
        raise ValueError(f'Unexpected response from {url}: {obj}')
    return obj


def download_once(meta):
    name = meta['filename']
    if Path(name).name != name or not name.endswith('.mat'):
        raise ValueError(f'Unexpected filename: {name}')
    target = DEST / name
    info = meta['content_details']
    expected = info['sha256_hash']
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
        return name
    part = target.with_suffix('.mat.part')
    h = hashlib.sha256()
    with requests.get(info['download_url'], stream=True, timeout=(30, 120)) as r:
        r.raise_for_status()
        with part.open('wb') as f:
            for chunk in r.iter_content(1024 * 1024):
                f.write(chunk)
                h.update(chunk)
    if h.hexdigest() != expected or part.stat().st_size != info['size']:
        raise ValueError(f'Publisher checksum/size mismatch: {name}')
    part.replace(target)
    print(f'downloaded {name}', flush=True)
    return name


def download(meta):
    for attempt in range(4):
        try:
            return download_once(meta)
        except (requests.RequestException, ValueError):
            if attempt == 3:
                raise
            print(f'retry {attempt + 1}: {meta["filename"]}', flush=True)


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    folders = get_json(f'{API}/folders/5')
    parent = next(f['id'] for f in folders if 'MatLab' in f['name'])
    files = []
    for folder in folders:
        if folder.get('parent_id') == parent:
            files.extend(get_json(f'{API}/files', version=5, folder_id=folder['id']))
    files = [f for f in files if f['filename'].endswith('.mat')]
    print(f'{len(files)} files, {sum(f["content_details"]["size"] for f in files)/1e6:.1f} MB', flush=True)
    (DEST.parent / 'manifest.json').write_text(json.dumps(files, indent=2), encoding='utf8')
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(download, files))


if __name__ == '__main__':
    main()
