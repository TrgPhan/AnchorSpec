"""Post-hoc (12/11): 'real + Flow within, strength 0.3' in the single-RF S3 setting, re-applying the SAME saved S3 flow
residuals (data/s3_generation/<t>_<s>/residuals.npz, codec.pkl) at strength 0.3 instead of 0.5. Scored exactly like S3."""
import os, json, pickle
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from sklearn.ensemble import RandomForestClassifier as _RFC
import invariant_classifier as IC
from event_experts import causal_average
from t_readiness import selective
from s_additive import additive_training, training
from u_natural import LABEL, ORDERS, bearing
import funnel as Fu
import s3_rescore_all as S

DATA = S.DATA


def flow_feats(target, seed, strength):
    d = DATA / 's3_generation' / f'{target}_{seed}'
    cp = pickle.load(open(d / 'codec.pkl', 'rb')); codec, sources = cp['codec'], cp['sources']
    z = np.load(d / 'residuals.npz'); waves = np.concatenate([bearing(n)['terminal'] for n in sources])
    gen, _ = codec.apply(waves[z['indices']], z['flow'], strength, z['peak_limits'])
    return {n: Fu.feats(gen[i*10:(i+1)*10, None, :], 4000, float(bearing(n)['fr']), ORDERS) for i, n in enumerate(sources)}


def job(task):
    target, seed = task; t = bearing(target); src = [n for n in LABEL if n != target]
    ev = [(n, LABEL[n], bearing(n)['terminal_features']) for n in src]; h = t['healthy_features'][:5]
    f05 = flow_feats(target, seed, .5)
    with np.load(DATA / 's3_generation' / f'{target}_{seed}' / 'features.npz') as f:
        check = all(np.allclose(f05[n], f[n + ':spectral_flow_half']) for n in src)
    f03 = flow_feats(target, seed, .3); out = {}
    for trees in (50, 500):
        IC.RandomForestClassifier = lambda **kw: _RFC(**{**kw, 'n_estimators': trees})
        sets = {f'flow03_add_rf{trees}': additive_training(h, ev, {n: {'flow': f03[n]} for n in src}, 'flow', 1., .25)[:3]}
        # share variant: Flow rows take 25% of each fault class mass (class totals unchanged)
        import m_dev
        base = training(h, ev, {}, 'real'); rows = {}
        for n, c, _ in ev: rows.setdefault(c, []).append(f03[n])
        sets[f'flow03_share_rf{trees}'] = m_dev.mix(base, {c: np.concatenate(v) for c, v in rows.items()}, .25)
        for a, xyw in sets.items():
            mdl = IC.InvariantClassifier('rf', seed).fit(*xyw)
            out[a] = {st: selective(causal_average(mdl.predict_proba(x)), 0).tolist()
                      for st, x in (('healthy', t['healthy_features'][5:]), ('terminal', t['terminal_features']))}
    return dict(target=target, seed=seed, label=LABEL[target], check=bool(check), scores=out)


if __name__ == '__main__':
    tasks = [(t, s) for t in LABEL for s in S.SEEDS]
    with ProcessPoolExecutor(14) as ex: new = list(ex.map(job, tasks))
    print('áp lại độ mạnh 0,5 trùng đặc trưng Flow S3 đã lưu:', sum(r['check'] for r in new), '/', len(new))
    rows = json.load(open(S.ROOT / 'results/s3_rescore/rows.json')); idx = {(r['target'], r['seed']): r for r in new}
    for r in rows: r['scores'].update(idx[(r['target'], r['seed'])]['scores'])
    json.dump(rows, open(S.ROOT / 'results/s3_rescore/rows.json', 'w'))
    names = [('real_rf50', 'Chỉ dữ liệu thật, RF 50'), ('photocopy_rf50', 'Thật + photocopy, RF 50'), ('flow_s3_rf50', 'Thật + Flow S3 (0,5, cộng 0,25), RF 50'),
             ('flow03_add_rf50', 'Thật + Flow within 0,3 (cộng 0,25), RF 50'), ('flow03_share_rf50', 'Thật + Flow within 0,3 (chiếm 25%), RF 50'),
             ('real_rf500', 'Chỉ dữ liệu thật, RF 500'), ('photocopy_rf500', 'Thật + photocopy, RF 500'), ('flow_s3_rf500', 'Thật + Flow S3 (0,5, cộng 0,25), RF 500'),
             ('flow03_add_rf500', 'Thật + Flow within 0,3 (cộng 0,25), RF 500'), ('flow03_share_rf500', 'Thật + Flow within 0,3 (chiếm 25%), RF 500'),
             ('hier', 'hier (chốt)'), ('flow_within_03', 'hier + Flow within 0,3 (bi/cách)')]
    L = ['| Phương pháp | Avg Precision | Accuracy | Avg Recall | Recall khỏe / trong / ngoài / cách |', '|---|---:|---:|---:|---|']
    for a, n in names:
        p, acc, rc, pr, rcl = S.metrics(rows, a)
        L.append(f'| {n} | {p*100:.1f} | {acc*100:.1f} | {rc*100:.1f} | ' + ' / '.join(f'{x*100:.0f}' for x in rcl) + ' |')
    open(S.ROOT / 'results/s3_rescore/summary_within03.md', 'w').write('\n'.join(L)); print('\n'.join(L))
