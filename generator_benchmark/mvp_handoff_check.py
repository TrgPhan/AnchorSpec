"""Revalidate a locked release without retraining, tuning or writing into it.

Evidence goes to a NEW sibling directory. Chrome is optional; when absent,
browser checks are explicitly marked skipped, not passed.
"""
import argparse
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np

from benchmark import write_json
from generators import LABELS
from mvp_cli import verify
from mvp_core import ROOT, load_records, sha, summary_metrics
from mvp_run import read
from mvp_validate import restore_ddpm, validate_library, validate_report_links


def require(condition, message):
    if not condition:
        raise ValueError(message)


def browser_check(release, output):
    chrome = Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
    if not chrome.is_file():
        return {'status': 'SKIPPED', 'reason': 'Reviewed Chrome executable not found'}
    # This local-only harness exercises the ORIGINAL report, not a rebuilt copy.
    # File access is enabled solely for the parent to inspect its local iframe.
    harness = output/'browser_harness.html'
    harness.write_text('''<!doctype html><html><meta charset="utf-8">
<pre id="result" data-status="pending">pending</pre>
<iframe id="report" style="width:1440px;height:1800px" src="'''
        + escape((release/'report.html').as_uri(), quote=True) + '''"></iframe>
<script>
document.getElementById('report').addEventListener('load', () => {
  const result = document.getElementById('result');
  try {
    const frame = document.getElementById('report');
    const doc = frame.contentDocument;
    const panels = Array.from(doc.querySelectorAll('.signals'));
    const select = doc.getElementById('label');
    const checks = [];
    for (const label of ['inner', 'outer', 'ball']) {
      select.value = label;
      select.dispatchEvent(new frame.contentWindow.Event('change', {bubbles:true}));
      const visible = panels.filter(p => frame.contentWindow.getComputedStyle(p).display !== 'none');
      if (visible.length !== 1 || visible[0].id !== label) throw Error('selector: ' + label);
      if (visible[0].querySelectorAll('svg').length !== 4) throw Error('panels: ' + label);
      const details = visible[0].querySelector('details');
      details.querySelector('summary').click();
      if (!details.open) throw Error('provenance did not open');
      const metadata = JSON.parse(details.querySelector('pre').textContent);
      if (!metadata.is_synthetic || metadata.source_role !== 'train') throw Error('provenance');
      details.querySelector('summary').click();
      checks.push({label, visible_panels:1, svg:4, provenance_opened:true});
    }
    if (doc.querySelectorAll('article').length !== 12) throw Error('weekly reviews');
    if (doc.querySelectorAll('tbody tr').length !== 8) throw Error('method rows');
    result.textContent = JSON.stringify({checks, weekly_reviews:12, method_rows:8});
    result.dataset.status = 'pass';
  } catch (error) {
    result.textContent = String(error);
    result.dataset.status = 'fail';
  }
});
</script></html>''', encoding='utf-8')
    with tempfile.TemporaryDirectory(prefix='denso_handoff_', ignore_cleanup_errors=True) as profile:
        base = [str(chrome), '--headless', '--disable-gpu', '--no-first-run',
                '--no-default-browser-check', '--disable-background-networking',
                f'--user-data-dir={profile}']
        commands = {
            'interaction': base + ['--allow-file-access-from-files', '--dump-dom',
                                   '--virtual-time-budget=5000', harness.as_uri()],
            'desktop': base + [f'--screenshot={output / "report_desktop.png"}',
                               '--window-size=1440,5200', '--hide-scrollbars',
                               (release/'report.html').as_uri()],
            'mobile': base + [f'--screenshot={output / "report_mobile.png"}',
                              '--window-size=390,1100', (release/'report.html').as_uri()],
        }
        for name, command in commands.items():
            run = subprocess.run(command, capture_output=True, text=True,
                                 encoding='utf-8', errors='replace', timeout=90)
            (output/f'browser_{name}.log').write_text(run.stdout+run.stderr, encoding='utf-8')
            require(run.returncode == 0, f'Chrome failed: {name}')
            if name == 'interaction':
                require('id="result" data-status="pass"' in run.stdout,
                        'Report interaction failed; inspect browser_interaction.log')
            else:
                require((output/f'report_{name}.png').is_file(), f'Missing screenshot: {name}')
    return {'status': 'PASS', 'labels_tested': list(LABELS), 'weekly_reviews': 12,
            'method_rows': 8, 'viewports': ['1440x5200', '390x1100'],
            'scope': 'Local rendering, label switching and provenance; not accessibility certification'}


def check(release, output):
    require(not output.is_relative_to(release), 'Evidence must be outside the locked release')
    output.mkdir(parents=True, exist_ok=False)
    results = {'started_utc': datetime.now(timezone.utc).isoformat(),
               'release': str(release), 'validator_sha256': sha(Path(__file__)),
               'scope': 'Reproduction/packaging validation, not a new holdout experiment'}
    try:
        original_manifest = sha(release/'integrity.json')
        results['integrity_before'] = verify(release)
        for name in ('test_generators.py', 'test_mvp.py'):
            run = subprocess.run([sys.executable, str(ROOT/name)], capture_output=True,
                                 text=True, encoding='utf-8', errors='replace', timeout=300)
            (output/(name+'.log')).write_text(run.stdout+run.stderr, encoding='utf-8')
            results[name] = {'exit_code': run.returncode, 'code_sha256': sha(ROOT/name)}
            require(run.returncode == 0, f'Tests failed: {name}')
            print(name, 'PASS', flush=True)
        records = load_records(read(release/'records.json'), {'train'})
        results['library'] = {label: validate_library(release/'library'/label,
            records[('train', label)]['x'][:8]) for label in LABELS}
        print('Full library metadata/quality audit PASS', flush=True)
        results['ddpm_reload'] = []
        for seed in (11, 29, 47):
            generator = restore_ddpm(release/f'development/ddpm_{seed}.pt', device='cpu')
            require(generator.fit_log['steps'] == 1500, 'DDPM training budget changed')
            regenerated, _ = generator.sample('inner', 128, seed+1000)
            saved = np.load(release/f'development/ddpm_prototype_{seed}_inner.npy', allow_pickle=False)
            require(np.array_equal(regenerated, saved), f'Checkpoint reproduction failed: {seed}')
            results['ddpm_reload'].append({'seed': seed, 'label': 'inner', 'count': 128,
                'training_device': generator.fit_log['device'], 'training_steps': 1500,
                'sampling_device': 'cpu', 'bitwise_identical': True})
            print('DDPM reload', seed, 'PASS', flush=True)
        metrics = read(release/'final/metrics.json')
        keys = ('macro_fault_recall', 'fpr', 'accuracy', 'macro_f1', 'coverage')
        for row in metrics:
            with np.load(release/f"final/predictions_{row['variant']}_{row['seed']}.npz",
                         allow_pickle=False) as arrays:
                fresh = summary_metrics(arrays['y'], arrays['probabilities'], arrays['scores'],
                                        float(arrays['threshold']), arrays['valid'])
            for key in keys:
                require(np.isclose(fresh[key], row[key], atol=1e-12, rtol=0),
                        f'Saved metric mismatch: {row["variant"]}/{row["seed"]}/{key}')
        summary = read(release/'final/summary.json')
        for name, values in summary['methods'].items():
            rows = [row for row in metrics if row['variant'] == name]
            require(sorted(row['seed'] for row in rows) == [11, 29, 47], 'Missing/duplicate seeds')
            for key in keys:
                require(np.isclose(values[key], np.mean([row[key] for row in rows]), atol=1e-12, rtol=0),
                        f'Summary mismatch: {name}/{key}')
            require(values['max_seed_fpr'] == max(row['fpr'] for row in rows), 'Worst-seed mismatch')
        require(summary['selected_pretest'] == read(release/'FROZEN.json')['selected'], 'Selection changed')
        results['metric_rows_recomputed'] = len(metrics)
        results['software_acceptance'] = read(release/'acceptance/results.json')
        require(len(results['software_acceptance']) == 8 and
                all(row['passed'] for row in results['software_acceptance']), 'CLI acceptance incomplete')
        results['html_structure'] = validate_report_links(release/'report.html')
        results['browser'] = browser_check(release, output)
        results['integrity_after'] = verify(release)
        require(sha(release/'integrity.json') == original_manifest, 'Integrity manifest changed')
        results['locked_release_unchanged'] = True
        results['status'] = 'PASS'
    except Exception as error:
        results['status'] = 'FAIL'
        results['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        results['finished_utc'] = datetime.now(timezone.utc).isoformat()
        write_json(output/'results.json', results)
    print('HANDOFF CHECK PASS', output, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    check(args.release.resolve(), args.output.resolve())