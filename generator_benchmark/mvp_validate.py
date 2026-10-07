"""Additional release contract checks independent of model selection."""
import hashlib
import json
from pathlib import Path

import numpy as np

from mvp_core import digest, sha, audit_library


def validate_library(path, anchors):
    path=Path(path)
    config=json.loads((path/'config.json').read_text())
    manifest=json.loads((path/'manifest.json').read_text())
    source=config['source']
    if source['role']!='train' or source['label']!=config['label'] or sha(source['file'])!=source['sha256']:
        raise ValueError('Source contract mismatch')
    anchor_hash=hashlib.sha256(np.asarray(anchors).tobytes()).hexdigest()
    if anchor_hash!=config['anchor_array_sha256']:
        raise ValueError('Anchor array mismatch')
    attempts=[json.loads(line) for line in (path/'attempts.jsonl').read_text().splitlines()]
    reasons={}; coordinates=set(); n_accepted=0
    for number,row in enumerate(attempts):
        if (row['attempt_id']!=number or row['config_hash']!=digest(config) or
            row['source_record_id']!=source['id'] or row['source_sha256']!=source['sha256'] or
            row['source_role']!='train' or not row['is_synthetic'] or
            row['intended_fault_mechanism']!=config['label'] or row['fs_hz']!=config['fs_hz'] or
            row['n_samples']!=config['window_samples'] or row['rpm']!=config['rpm']):
            raise ValueError('Attempt contract mismatch')
        if row['accepted']:
            n_accepted+=1
            coordinate=(row['shard'],row['row_index'])
            if row['rejection_reason'] is not None or coordinate in coordinates:
                raise ValueError('Accepted coordinate/reason mismatch')
            coordinates.add(coordinate)
        else:
            if not row['rejection_reason'] or row['shard'] is not None or row['row_index'] is not None:
                raise ValueError('Rejected attempt contract mismatch')
            reasons[row['rejection_reason']]=reasons.get(row['rejection_reason'],0)+1
    if (not manifest['complete'] or n_accepted!=manifest['accepted'] or reasons!=manifest['reasons'] or
        len(attempts)-n_accepted!=manifest['rejected'] or len(attempts)>config['quota']*config['max_multiplier']):
        raise ValueError('Acceptance denominator mismatch')
    summary=audit_library(path,anchors)
    summary['metadata_contract_verified']=True
    return summary


def restore_ddpm(checkpoint, device=None):
    """Restore OUR trusted DDPM state without accidentally training a new model."""
    from deep_generators import DeepGenerator, Denoiser, cosine_schedule
    import torch
    state=torch.load(checkpoint,map_location='cpu',weights_only=True)
    if state['method']!='ddpm_prototype': raise ValueError('Only reviewed DDPM supported')
    g=DeepGenerator.__new__(DeepGenerator)
    g.method=state['method'];g.device=torch.device(device or ('cuda' if torch.cuda.is_available() else 'cpu'))
    torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
    g.scales=state['scales'];g.support=state['support'];g.fit_log=state['fit_log']
    g.model=Denoiser().to(g.device);g.model.load_state_dict(state['state_dict']);g.model.eval()
    g.beta=cosine_schedule().to(g.device);g.alpha=1-g.beta;g.bar=g.alpha.cumprod(0)
    return g


def validate_report_links(path):
    """Check all local hrefs and waveform panels; no browser dependency."""
    from html.parser import HTMLParser
    class Parser(HTMLParser):
        def __init__(self):
            super().__init__(); self.links=[]; self.ids=[]; self.svg_count=0
        def handle_starttag(self,tag,attrs):
            values=dict(attrs)
            if tag=='a' and 'href' in values: self.links.append(values['href'])
            if 'id' in values: self.ids.append(values['id'])
            if tag=='svg': self.svg_count+=1
    path=Path(path); parser=Parser();parser.feed(path.read_text(encoding='utf-8'))
    for href in parser.links:
        if not (path.parent/href).is_file(): raise ValueError(f'Broken report link: {href}')
    if parser.svg_count!=12 or not {'inner','outer','ball','label'}.issubset(parser.ids):
        raise ValueError('Report missing waveform/PSD/envelope panels')
    return {'local_links_verified':len(parser.links),'svg_panels':parser.svg_count,
            'scope':'HTML structure and targets; not visual browser automation'}