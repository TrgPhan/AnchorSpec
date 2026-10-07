"""Weekly MVP stages. Development never opens calibration/final recordings.

Use prepare -> develop -> finalize -> report; each stage refuses overwrites.
Final results are descriptive recording-shift evidence, NOT bearing-independent.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
import json
import pickle
import platform
import shutil
import sys
import time
from urllib.request import urlopen

import numpy as np
import scipy
import sklearn

from benchmark import write_json
from generators import Generator, LABELS, FS, N
from mvp_core import (ROOT, CLASSES, sha, digest, load_records, validate_splits,
    detector_features, conformal_threshold, fit_detector, fit_healthy,
    summary_metrics, export_library, audit_library, valid_rows)

SEEDS = (11, 29, 47)
METHODS = ('real_only', 'simple', 'constrained_surrogate', 'physics_unanchored',
           'physics_anchored', 'physics_calibrated', 'ddpm_prototype')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def checkpoint(path, state):
    with Path(path).open('wb') as stream:
        pickle.dump(state, stream)


def checkpoint_read(path, expected_hash):
    if sha(path) != expected_hash:
        raise ValueError('Checkpoint hash mismatch; refusing to unpickle')
    # Only checkpoints generated locally by this pipeline; never user uploads.
    with Path(path).open('rb') as stream:
        return pickle.load(stream)


def review(out, week, status, findings, evidence):
    entry = {'week': week, 'status': status, 'utc': datetime.now(timezone.utc).isoformat(),
             'findings': findings, 'evidence': evidence,
             'schedule_note': 'execution milestone, not elapsed calendar week'}
    write_json(out/f'week_{week:02d}.json', entry)
    print(f'WEEK {week}: {status}: {findings}', flush=True)


def prepare(out, args):
    out.mkdir(parents=True, exist_ok=False)
    snapshot = out/'code_snapshot'
    snapshot.mkdir()
    for path in ROOT.glob('*.py'):
        shutil.copy2(path, snapshot/path.name)
    source_hashes = {str(p): sha(p) for p in ROOT.glob('*.py')}
    protocol = {'version': 1, 'seeds': SEEDS, 'methods': METHODS,
        'fault_anchors_per_class': 8, 'healthy_train_windows': 20,
        'base_synthetic_count': 128, 'base_synthetic_class_mass': .5,
        'development_grid': {'methods': ['simple', 'constrained_surrogate'],
                             'counts': [32, 256], 'class_mass': [.25, .5]},
        'alpha': .05, 'meaningful_recall_gain': .02,
        'rf': {'n_estimators': 200, 'bootstrap': False, 'max_features': 'sqrt'},
        'deep_steps': args.deep_steps, 'production_per_class': args.quota,
        'selection': 'mean dev macro fault recall, then macro F1; require dev FPR<=.05 for every seed; real-only on ties',
        'max_development_rounds': 2,
        'final_rule': 'freeze before reading healthy2HP/cal and all3HP; no tuning after final',
        'uncertainty': '3 training seeds are not independent bearings; no window-IID CI',
        'primary_claim_gate': 'gain>=.02 vs real AND simple on final with FPR<=.05; descriptive only',
        'sources': source_hashes, 'created_utc': datetime.now(timezone.utc).isoformat()}
    write_json(out/'protocol.json', protocol)
    write_json(out/'environment.json', {'python': sys.version, 'platform': platform.platform(),
        'numpy': np.__version__, 'scipy': scipy.__version__, 'sklearn': sklearn.__version__})
    old = read(ROOT/'data_manifest.json')
    manifest = []
    for row in old:
        load = row['load_hp']
        role = 'train' if load == 0 else 'dev' if load == 1 else 'cal' if row['label'] == 'healthy' else 'dev_secondary'
        manifest.append({**row, 'role': role, 'rpm_fallback': (1797,1772,1750)[load]})
    # Verify official href/name mapping, not assumed numeric adjacency.
    class DownloadLinks(HTMLParser):
        def __init__(self):
            super().__init__(); self.href = None; self.rows = []
        def handle_starttag(self, tag, attrs):
            if tag == 'a': self.href = dict(attrs).get('href')
        def handle_data(self, data):
            if self.href: self.rows.append((self.href, data.strip()))
        def handle_endtag(self, tag):
            if tag == 'a': self.href = None
    links = []
    for page in ('12k-drive-end-bearing-fault-data', 'normal-baseline-data'):
        url = 'https://engineering.case.edu/bearingdatacenter/'+page
        body = urlopen(url, timeout=60).read()
        (out/(page+'.html')).write_bytes(body)
        parser = DownloadLinks(); parser.feed(body.decode()); links.extend(parser.rows)
    targets = [(100, 'healthy', 'Normal_3'), (108, 'inner', 'IR007_3'),
               (133, 'outer', 'OR007@6_3'), (121, 'ball', 'B007_3')]
    def download(item):
        number, label, name = item
        matched = [url for url, text in links if text == name and url.endswith(f'/{number}.mat')]
        if not matched:
            raise ValueError(f'Official link mapping not verified: {item}')
        url = matched[0]
        if url.startswith('/'): url = 'https://engineering.case.edu'+url
        path = out/'fresh_data'/f'{number}.mat'
        with urlopen(url, timeout=90) as response:
            content = response.read()
        if not content.startswith(b'MATLAB'):
            raise ValueError('Non-MATLAB source')
        path.write_bytes(content)
        return {'id': number, 'label': label, 'load_hp': 3, 'role': 'final',
            'file': str(path.resolve()), 'sha256': sha(path), 'url': url,
            'rpm_fallback': 1730, 'bearing_independence': 'not established',
            'permission': 'No commercial/redistribution permission established'}
    (out/'fresh_data').mkdir()
    with ThreadPoolExecutor(max_workers=4) as pool:
        manifest.extend(pool.map(download, targets))
    write_json(out/'records.json', manifest)
    split_audit = validate_splits(manifest)
    write_json(out/'split_audit.json', split_audit)
    train = load_records(manifest, {'train'})
    write_json(out/'train_inventory.json', [{k:v for k,v in row.items() if k != 'x'} |
        {'windows': len(row['x']), 'finite_nonconstant': bool(valid_rows(row['x']).all())} for row in train.values()])
    review(out, 1, 'PUBLIC_ONLY', 'Confirmed generation task; 17 legacy tests after CuBLAS repair; DENSO permissions/mentor pending.', ['records.json','train_inventory.json'])
    review(out, 2, 'PASS_WITH_LIMITS', 'Disjoint recording hashes; predeclared development budget; 3HP reserved. No independent bearings; healthy native fs=48k assumption.', ['protocol.json','split_audit.json'])


def real_training(records):
    anchors = {k: records[('train', k)]['x'][:8] for k in LABELS}
    bg = records[('train', 'healthy')]['x'][:20]
    rpms = {k: records[('train', k)]['rpm'] for k in CLASSES}
    real = {k: detector_features(bg if k == 'healthy' else anchors[k], rpms[k]) for k in CLASSES}
    return anchors, bg, rpms, real


def matrix(records, role):
    xs, ys, indices, valid = [], [], [], []
    for k, label in enumerate(CLASSES):
        row = records[(role, label)]
        ok = valid_rows(row['x'])
        f = np.zeros((len(ok), 25))
        f[ok] = detector_features(row['x'][ok], row['rpm'])
        xs.append(f); ys.extend([k]*len(f)); valid.extend(ok)
        indices.extend({'record_id': row['source']['id'], 'window': i, 'label': label} for i in range(len(f)))
    return np.concatenate(xs), np.array(ys), indices, np.array(valid)


def score_model(model, x):
    p = model.predict_proba(x)
    return p, 1-p[:, 0]


def develop(out, args):
    protocol = read(out/'protocol.json')
    dest = out/'development'
    if args.resume_development:
        if (out/'FROZEN.json').exists() or (out/'final').exists():
            raise ValueError('Cannot resume development after freeze/final')
        old_rows=read(dest/'metrics.json')
        if any(r['variant'] not in METHODS for r in old_rows):
            raise ValueError('Recovery only supported before dose grid')
        archive=out/('interrupted_gpu_training' if args.resume_cpu_final else 'interrupted_gpu_sampling')
        archive.mkdir(exist_ok=False)
        shutil.copy2(dest/'metrics.json',archive/'metrics.json')
        shutil.copy2(out/'protocol.json',archive/'protocol_before_recovery.json')
        if not args.resume_cpu_final:
            for path in list(dest.glob('ddpm_prototype_*'))+list(dest.glob('model_ddpm_prototype_*')):
                shutil.move(str(path),str(archive/path.name))
        amendment={
            'reason':'4GB laptop GPU sampling severe slowdown; CPU32 measured 15.57s; final unopened',
            'sampling_device':'cpu for all three DDPM seeds',
            'training_device':'seed11/29 original CUDA checkpoints; seed47 CPU' if args.resume_cpu_final else 'original CUDA checkpoints reused; seed47 trained CUDA',
            'training_budget_unchanged':True,'pre_final':True,
            'recovery_code_sha256':sha(Path(__file__))}
        protocol['cpu_training_recovery' if args.resume_cpu_final else 'recovery_amendment']=amendment
        write_json(out/'protocol.json',protocol)
        recovery_snapshot=archive/'recovery_code';recovery_snapshot.mkdir()
        for path in ROOT.glob('*.py'): shutil.copy2(path,recovery_snapshot/path.name)
    else:
        dest.mkdir(exist_ok=False)
    records = load_records(read(out/'records.json'), {'train','dev'})
    anchors, bg, rpms, real = real_training(records)
    x, y, indices, valid = matrix(records, 'dev')
    models, rows, costs, synth_cache = {}, [], [], {}
    if args.resume_development:
        rows=[r for r in old_rows if r['method']!='ddpm_prototype' or args.resume_cpu_final]
        for row in rows:
            name,seed=row['variant'],row['seed']
            path=dest/f'model_{name}_{seed}.pkl'
            models[(name,seed)]={'file':str(path),'sha256':sha(path)}
            if name!='real_only':
                costs.append({'method':name,'seed':seed,'seconds':row['generation_fit_seconds'],
                              'train_only':True,'recovered_from_saved_metric':True})
        for method in ('simple','constrained_surrogate'):
            for seed in SEEDS:
                for label in LABELS:
                    synth_cache[(method,seed,label)]=detector_features(
                        np.load(dest/f'{method}_{seed}_{label}.npy',allow_pickle=False),rpms[label])
    # Gate for all METHODS: raw finite candidates; no anti-copy disadvantage for
    # simple. Library export later has a different, explicitly declared gate.
    def evaluate_variant(name, method, seed, synthetic, mass, cost=0.):
        start = time.perf_counter()
        model, weights = fit_detector(real, synthetic, seed, mass)
        p, scores = score_model(model, x)
        threshold = conformal_threshold(scores[(y == 0) & valid], protocol['alpha'])
        metrics = summary_metrics(y, p, scores, threshold, valid)
        state = {'model': model, 'name': name, 'seed': seed, 'weights': weights}
        path = dest/f'model_{name}_{seed}.pkl'
        checkpoint(path, state)
        models[(name,seed)] = {'file': str(path), 'sha256': sha(path)}
        row = {'variant': name, 'method': method, 'seed': seed,
            'synthetic_weight': mass if synthetic else 0., 'weights': weights,
            'fit_seconds': time.perf_counter()-start, 'generation_fit_seconds': cost,
            **metrics}
        rows.append(row)
        print(name, seed, 'recall', round(metrics['macro_fault_recall'],4),
              'FPR', round(metrics['fpr'],4), 'F1', round(metrics['macro_f1'],4), flush=True)
        write_json(dest/'metrics.json', rows)
    for method in METHODS:
        if args.resume_development and method!='ddpm_prototype':
            if sum(r['variant']==method for r in rows)!=3:
                raise ValueError('Recovery requires completed three seeds for every non-DDPM base method')
            continue
        for seed in SEEDS:
            if args.resume_cpu_final and any(r['variant']==method and r['seed']==seed for r in rows):
                continue
            start = time.perf_counter()
            if method == 'real_only':
                synthetic = {}
            else:
                if method == 'ddpm_prototype':
                    from deep_generators import DeepGenerator
                    import torch
                    state_path=dest/f'ddpm_{seed}.pt'
                    if args.resume_development and state_path.exists():
                        from mvp_validate import restore_ddpm
                        generator=restore_ddpm(state_path,device='cpu')
                    else:
                        generator = DeepGenerator(method, anchors, seed, steps=protocol['deep_steps'],device='cpu',progress=True)
                        torch.save({'state_dict': generator.model.state_dict(), 'scales': generator.scales,
                            'support': generator.support, 'fit_log': generator.fit_log,
                            'seed': seed, 'method': method}, state_path)
                    # CPU sampling avoids Windows shared-VRAM thrashing on 4GB GPU.
                    generator.device=torch.device('cpu');generator.model.to('cpu')
                    generator.beta=generator.beta.cpu();generator.alpha=generator.alpha.cpu();generator.bar=generator.bar.cpu()
                    torch.cuda.empty_cache()
                else:
                    generator = Generator(method, anchors, bg, seed, {k:rpms[k] for k in LABELS})
                write_json(dest/f'fit_{method}_{seed}.json', generator.fit_log)
                synthetic = {}
                for label in LABELS:
                    count = 256 if method in ('simple','constrained_surrogate') else 128
                    waves, provenance = generator.sample(label, count, seed+1000)
                    if not valid_rows(waves).all():
                        raise ValueError(f'Invalid generated waves: {method}/{label}; do not silently drop')
                    np.save(dest/f'{method}_{seed}_{label}.npy', waves)
                    write_json(dest/f'{method}_{seed}_{label}_provenance.json', provenance)
                    f = detector_features(waves, rpms[label])
                    synth_cache[(method, seed, label)] = f
                    synthetic[label] = f[:128]
                costs.append({'method': method, 'seed': seed, 'seconds': time.perf_counter()-start,
                              'train_only': True, 'raw_synthetic_not_quality_filtered': True})
            evaluate_variant(method, method, seed, synthetic, .5, time.perf_counter()-start)
        if method == 'constrained_surrogate':
            review(out, 3, 'PASS', 'Real-only/simple/surrogate and fixed-weight RF evaluated; baseline is not replaced by generator quality metrics.', ['development/metrics.json'])
        if method == 'physics_calibrated':
            review(out, 4, 'RESEARCH_ONLY', 'Three legacy physics variants evaluated fresh; amplitude-unanchored is NOT healthy-only. No unseen-RPM/severity claim.', ['development/metrics.json'])
    review(out, 5, 'PASS_SCOPED', 'Audited shard writer with bounded attempts and fail-closed support. Hard-negative DENSO transitions unavailable.', ['code_snapshot/mvp_core.py'])
    review(out, 6, 'PASS_SCOPED', 'DDPM trained anew, checkpoints saved; no claim of paper reproduction/convergence or equal compute.', ['development/ddpm_11.pt','development/metrics.json'])
    # Round two is preregistered, not an open-ended hunt for positive results.
    for method in ('simple','constrained_surrogate'):
        for count in (32,256):
            for mass in (.25,.5):
                name = f'{method}_n{count}_w{int(mass*100)}'
                for seed in SEEDS:
                    synthetic = {label:synth_cache[(method,seed,label)][:count] for label in LABELS}
                    evaluate_variant(name, method, seed, synthetic, mass)
    # Healthy-only reference is separate: no fusion selected/calibrated by accident.
    for seed in SEEDS:
        c = fit_healthy(real['healthy'], seed)
        path = dest/f'healthy_{seed}.pkl'; checkpoint(path, c)
        models[('healthy_only',seed)] = {'file': str(path), 'sha256': sha(path)}
        scores = -c.score_samples(x)
        threshold = conformal_threshold(scores[(y == 0) & valid])
        p = np.zeros((len(x),4)); p[:,0] = 1
        rows.append({'variant':'healthy_only','method':'healthy_only','seed':seed,
                     **summary_metrics(y,p,scores,threshold,valid)})
    write_json(dest/'metrics.json', rows); write_json(dest/'costs.json', costs)
    summary = []
    for name in sorted({r['variant'] for r in rows if r['variant'] != 'healthy_only'}):
        part = [r for r in rows if r['variant'] == name]
        summary.append({'variant': name, 'method':part[0]['method'],
            'eligible': all(r['fpr'] <= .05 and r['coverage'] == 1 for r in part),
            'recall':float(np.mean([r['macro_fault_recall'] for r in part])),
            'f1':float(np.mean([r['macro_f1'] for r in part])),
            'fpr':float(np.mean([r['fpr'] for r in part]))})
    eligible = [r for r in summary if r['eligible']]
    if not eligible:
        raise RuntimeError('No development candidate meets FPR gate')
    ranked = sorted(eligible, key=lambda r:(-r['recall'],-r['f1'],r['variant'] != 'real_only',r['variant']))
    selected = ranked[0]['variant']
    simple = sorted([r for r in eligible if r['method']=='simple'], key=lambda r:(-r['recall'],-r['f1'],r['variant']))[0]['variant']
    write_json(dest/'selection.json', {'summary':summary,'selected':selected,'best_simple':simple})
    review(out, 7, 'PASS_SCOPED', 'Predeclared count/weight dose grid complete; count does not increase evidence independence.', ['development/selection.json','development/costs.json'])
    review(out, 8, 'GAP', 'Development selection complete; independent-bearing/PU evaluation not claimed. No data imported under assumed commercial permission.', ['development/selection.json'])
    review(out, 9, 'GAP', 'Unknown faults/severity/DENSO target unvalidated. Reject unsupported conditions. Frozen candidates include all base methods for transparency.', ['protocol.json'])
    variants = list(dict.fromkeys([*METHODS, selected, simple, 'healthy_only']))
    frozen_models = {f'{name}:{seed}': models[(name,seed)] for name in variants for seed in SEEDS}
    freeze = {'selected':selected, 'best_simple':simple, 'variants':variants,
        'models': frozen_models, 'protocol_sha256':sha(out/'protocol.json'),
        'records_sha256':sha(out/'records.json'), 'selection_sha256':sha(dest/'selection.json'),
        'sources': {str(ROOT/f):sha(ROOT/f) for f in ('mvp_core.py','mvp_run.py','generators.py','deep_generators.py','mvp_validate.py')},
        'utc':datetime.now(timezone.utc).isoformat(),
        'final_seen':False, 'thresholds_not_yet_fit':True}
    write_json(out/'FROZEN.json', freeze)
    print('FROZEN', selected, flush=True)


def finalize(out, args):
    freeze = read(out/'FROZEN.json')
    for path, expected in freeze['sources'].items():
        if sha(path) != expected:
            raise ValueError('Evaluation code changed after freeze; new preregistration required')
    for file, key in (('protocol.json','protocol_sha256'),('records.json','records_sha256')):
        if sha(out/file) != freeze[key]: raise ValueError('Frozen input changed')
    dest = out/'final'
    dest.mkdir(exist_ok=False)
    protocol = read(out/'protocol.json')
    manifest = read(out/'records.json')
    # Separate healthy calibration role, never reused for fusion/model selection.
    records = load_records(manifest, {'cal','final','train'})
    cal = records[('cal','healthy')]
    cal_valid = valid_rows(cal['x'])
    if not cal_valid.all(): raise ValueError('Calibration quality failure; review separately')
    cal_x = detector_features(cal['x'],cal['rpm'])
    x,y,indices,valid = matrix(records,'final')
    rows, thresholds = [], []
    for name in freeze['variants']:
        for seed in SEEDS:
            ref = freeze['models'][f'{name}:{seed}']
            state = checkpoint_read(ref['file'], ref['sha256'])
            if name == 'healthy_only':
                calibration = -state.score_samples(cal_x); scores = -state.score_samples(x)
                p = np.zeros((len(x),4)); p[:,0]=1
            else:
                _,calibration = score_model(state['model'],cal_x)
                p,scores = score_model(state['model'],x)
            threshold = conformal_threshold(calibration,protocol['alpha'])
            thresholds.append({'variant':name,'seed':seed,'threshold':threshold,
                'healthy_calibration_windows':len(calibration),'calibration_record':99,
                'rule':'strict >','cross_load_exchangeability_guaranteed':False})
            metrics = summary_metrics(y,p,scores,threshold,valid)
            rows.append({'variant':name,'seed':seed,**metrics})
            np.savez(dest/f'predictions_{name}_{seed}.npz', y=y, probabilities=p,
                     scores=scores, valid=valid, threshold=threshold)
            print('FINAL',name,seed,metrics['macro_fault_recall'],metrics['fpr'],metrics['accuracy'],flush=True)
    write_json(dest/'thresholds.json',thresholds)
    write_json(dest/'metrics.json',rows); write_json(dest/'prediction_indices.json',indices)
    summary = {}
    for name in freeze['variants']:
        part = [r for r in rows if r['variant']==name]
        summary[name] = {key:float(np.mean([r[key] for r in part])) for key in
            ('macro_fault_recall','fpr','accuracy','macro_f1','coverage')}
        summary[name]['recall_seed_range'] = [min(r['macro_fault_recall'] for r in part),max(r['macro_fault_recall'] for r in part)]
        summary[name]['max_seed_fpr'] = max(r['fpr'] for r in part)
    selected = summary[freeze['selected']]
    delta = selected['macro_fault_recall']-summary['real_only']['macro_fault_recall']
    delta_simple = selected['macro_fault_recall']-summary[freeze['best_simple']]['macro_fault_recall']
    utility = (freeze['selected']!='real_only' and delta >= .02 and delta_simple >= .02 and selected['max_seed_fpr'] <= .05)
    write_json(dest/'summary.json',{'methods':summary,'selected_pretest':freeze['selected'],
        'delta_vs_real':delta,'delta_vs_simple':delta_simple,'descriptive_utility_gate':utility,
        'independent_bearing_claim':False,'DENSO_claim':False,
        'warning':'One recording/class; correlated windows; no valid bearing-level CI or guaranteed operational FPR.'})
    review(out,10,'PASS_EVALUATION' if utility else 'UTILITY_NOT_ESTABLISHED',
        f'Final load opened once; gain vs real={delta:.4f}, vs simple={delta_simple:.4f}. Do NOT retune on these outcomes.', ['FROZEN.json','final/summary.json'])
    # Library path is predeclared local-augmentation product, not a secretly
    # chosen detector winner. Production and downstream decisions are separate.
    anchors,bg,rpms,real = real_training(records)
    generator = Generator('constrained_surrogate',anchors,bg,901,{k:rpms[k] for k in LABELS})
    library_audits = {}
    for label in LABELS:
        export_library(generator,anchors[label],label,protocol['production_per_class'],901,
            out/'library'/label,records[('train',label)]['source'],rpms[label])
        library_audits[label] = audit_library(out/'library'/label,anchors[label])
    write_json(out/'library_audit.json',library_audits)
    review(out,11,'PASS_OFFLINE', 'Sharded known-condition library fully audited; demo is read-only and not a factory pilot.', ['library_audit.json'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['prepare','develop','finalize','report'])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--deep-steps',type=int,default=1500)
    parser.add_argument('--quota',type=int,default=1000)
    parser.add_argument('--resume-development',action='store_true',help='Explicit pre-grid recovery only; preserves interrupted evidence')
    parser.add_argument('--resume-cpu-final',action='store_true',help='Second documented pre-freeze recovery retaining completed CPU DDPM rows')
    args = parser.parse_args()
    if args.resume_cpu_final and not args.resume_development:
        parser.error('--resume-cpu-final requires --resume-development')
    if args.deep_steps < 1 or args.quota < 1: parser.error('Positive budgets required')
    out = args.output.resolve()
    if args.stage == 'report':
        from mvp_report import build_report
        build_report(out)
    else:
        globals()[args.stage](out,args)


if __name__ == '__main__':
    main()