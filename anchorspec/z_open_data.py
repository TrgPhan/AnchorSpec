"""Acquire selected official open datasets, with checksums and provenance.

DLR archives are read using HTTP byte ranges. Only selected sensor members are
downloaded. ZIP CRC is checked; the publisher's full-archive MD5 is recorded but
is NOT claimed verified for a partial download. Other files use publisher MD5.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import struct
import zipfile
import zlib

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data' / 'open_sources'


def metadata(record):
    r = requests.get(f'https://zenodo.org/api/records/{record}', timeout=(15, 60))
    r.raise_for_status()
    data = r.json()
    folder = DATA / str(record)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'record.json').write_text(json.dumps(data, indent=2), encoding='utf8')
    print(record, data['metadata']['title'], data['metadata'].get('license'), flush=True)
    return data, folder


def range_response(url, start, end):
    r = requests.get(url, headers={'Range': f'bytes={start}-{end}'}, stream=True, timeout=(20, 120))
    r.raise_for_status()
    expected = f'bytes {start}-{end}/'
    if r.status_code != 206 or not r.headers.get('Content-Range', '').startswith(expected):
        r.close()
        raise ValueError('Server did not honor the exact byte range; refusing whole-archive download')
    return r


class RemoteDirectory(io.RawIOBase):
    """Small seekable reads for zipfile central-directory parsing only."""
    def __init__(self, url, size):
        self.url, self.size, self.position = url, size, 0

    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.position

    def seek(self, offset, whence=0):
        self.position = offset + (0 if whence == 0 else self.position if whence == 1 else self.size)
        if self.position < 0: raise ValueError('Negative position')
        return self.position

    def read(self, n=-1):
        end = self.size if n < 0 else min(self.size, self.position + n)
        if end <= self.position: return b''
        if end-self.position > 2*1024*1024: raise ValueError('Unexpectedly large directory read')
        with range_response(self.url, self.position, end-1) as response:
            content = response.content
        if len(content) != end-self.position: raise ValueError('Short directory read')
        self.position = end
        return content


def safe_name(member):
    path = PurePosixPath(member.replace('\\', '/'))
    if path.is_absolute() or '..' in path.parts or ':' in member:
        raise ValueError('Unsafe member name')
    return path.name


def download_file(info, folder):
    path = folder / safe_name(info['key'])
    algorithm, expected = info['checksum'].split(':', 1)
    if path.exists():
        with path.open('rb') as f:
            if hashlib.file_digest(f, algorithm).hexdigest() == expected:
                return path
    partial = path.with_suffix(path.suffix+'.part')
    digest = hashlib.new(algorithm)
    with requests.get(info['links']['self'], stream=True, timeout=(20, 120)) as response:
        response.raise_for_status()
        with partial.open('wb') as f:
            for chunk in response.iter_content(1024*1024):
                f.write(chunk); digest.update(chunk)
    if digest.hexdigest() != expected or partial.stat().st_size != info['size']:
        raise ValueError('Publisher file checksum mismatch')
    partial.replace(path)
    print('verified file', path.name, flush=True)
    return path


def member_download(url, info, folder):
    name = safe_name(info.filename)
    target = folder/name
    if target.exists():
        crc = 0
        with target.open('rb') as f:
            while chunk := f.read(1024*1024): crc = zlib.crc32(chunk, crc)
        if crc == info.CRC and target.stat().st_size == info.file_size:
            with target.open('rb') as f: sha = hashlib.file_digest(f, 'sha256').hexdigest()
            return {'member': info.filename, 'local_file': name, 'sha256': sha,
                    'zip_crc32': info.CRC, 'uncompressed_bytes': info.file_size, 'crc_verified': True}
    with range_response(url, info.header_offset, info.header_offset+29) as response:
        header = response.content
    if header[:4] != b'PK\x03\x04': raise ValueError('Invalid local ZIP header')
    name_len, extra_len = struct.unpack_from('<HH', header, 26)
    start = info.header_offset + 30 + name_len + extra_len
    partial = target.with_suffix('.mat.part')
    decoder = zlib.decompressobj(-15) if info.compress_type == zipfile.ZIP_DEFLATED else None
    if info.compress_type not in (zipfile.ZIP_DEFLATED, zipfile.ZIP_STORED):
        raise ValueError('Unsupported ZIP compression')
    crc, size, compressed = 0, 0, 0
    sha = hashlib.sha256()
    with range_response(url, start, start+info.compress_size-1) as response, partial.open('wb') as f:
        for chunk in response.iter_content(1024*1024):
            compressed += len(chunk)
            raw = decoder.decompress(chunk) if decoder else chunk
            f.write(raw); size += len(raw); crc = zlib.crc32(raw, crc); sha.update(raw)
        if decoder:
            raw = decoder.flush()
            f.write(raw); size += len(raw); crc = zlib.crc32(raw, crc); sha.update(raw)
            if not decoder.eof: raise ValueError('Truncated ZIP stream')
    if compressed != info.compress_size or size != info.file_size or crc != info.CRC:
        raise ValueError('ZIP member size or CRC mismatch')
    partial.replace(target)
    print('verified member', name, f'{size/1e6:.1f} MB', flush=True)
    return {'member': info.filename, 'local_file': name, 'sha256': sha.hexdigest(),
            'zip_crc32': info.CRC, 'uncompressed_bytes': size, 'crc_verified': True}


def dlr_archive(args):
    archive, parent = args
    folder = parent/archive['key'].removesuffix('.zip')
    folder.mkdir(exist_ok=True)
    url = archive['links']['self']
    with zipfile.ZipFile(RemoteDirectory(url, archive['size'])) as z:
        entries = z.infolist()
    inventory = [{'name': e.filename, 'size': e.file_size, 'compressed': e.compress_size} for e in entries]
    (folder/'inventory.json').write_text(json.dumps(inventory, indent=2), encoding='utf8')
    selected = [e for e in entries if e.filename.endswith(('_Acc_Sensor_1.mat', '_Acc_Sensor_2.mat',
                '_Position_deg.mat', '_Temp_Sensor_1.mat', '_Temp_Sensor_2.mat', '_Ambient_Temp.mat'))]
    print(archive['key'], 'selected', len(selected), 'members', sum(e.compress_size for e in selected)/1e6, 'MB', flush=True)
    manifest = {'archive': archive, 'full_archive_checksum_verified': False,
                'selection': 'two accelerometers, angle and temperatures', 'members': []}
    for info in selected:
        manifest['members'].append(member_download(url, info, folder))
        (folder/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf8')


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('source', choices=('dlr','lubrication_tables'))
    args = parser.parse_args()
    if args.source == 'dlr':
        record, folder = metadata(20742913)
        wanted = {'Test_4.zip','Test_6.zip','Test_7.zip','Test_8.zip'}
        with ThreadPoolExecutor(2) as pool:
            list(pool.map(dlr_archive, [(f,folder) for f in record['files'] if f['key'] in wanted]))
    else:
        for identifier in (7589904,17530066):
            record, folder = metadata(identifier)
            for f in record['files']:
                if f['size'] <= 60*1024*1024: download_file(f, folder)


if __name__ == '__main__': main()
