"""Khám phá trên XJTU-SY đã mở: lợi ích vòng học lại, công thức vòng cách v2, cổng HI trên IMS."""
from concurrent.futures import ProcessPoolExecutor
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('OMP_NUM_THREADS', '1')

import numpy as np  # noqa: E402
from scipy import signal  # noqa: E402
from sklearn.covariance import LedoitWolf  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import tn2b_xjtu as X  # noqa: E402
from cheap_sensor import fault_path, output_stage  # noqa: E402
from injection import FS_SIM, Prior, _draw, _pulse, _train  # noqa: E402
from retrain import MachineModel  # noqa: E402

OUT = ROOT/'results'/'tn6'
K_LIST = (3, 5, 10)


def build(name, seed):
    d = X.bearing_data(name)
    fr, orders, n = d['fr'], X.UER204.orders(), d['norm']
    rng = np.random.default_rng([seed, int.from_bytes(name.encode(), 'big') % 2**31])
    sets, _ = X.injected_set(d['raw_base'], fr, orders, X.Prior(), X.FAULTS, X.N_INJECT, rng)
    F = {k: X.axis_features(sets[k], fr, orders) for k in X.FAULTS}
    inj = np.concatenate([F[k][:120] for k in X.FAULTS])
    y = np.concatenate([np.full(120, i+1) for i in range(3)])
    fx = np.concatenate([F[k][120:] for k in X.FAULTS]+[d['f']['hold']])
    fy = np.concatenate([np.full(30, i+1) for i in range(3)]+[np.zeros(len(d['f']['hold']), int)])
    return d, inj, y, fx, fy


def retrain_job(job):
    name, seed = job
    label = X.CLASSES.index(X.LABEL[name])
    d, inj, y, fx, fy = build(name, seed)
    late = d['f']['late']
    mid = len(late)//2
    out = {'name': name, 'seed': seed, 'label': X.LABEL[name], 'n_late': len(late)}
    mk = lambda: MachineModel(d['f']['base'], inj, y, fx, fy, seed=seed)
    test = late[mid:]
    m0 = mk()
    out['v1'] = float((m0.predict_proba(test).argmax(1) == label).mean())
    out['fixed_v1'] = m0.versions[0].fixed_score
    for k in K_LIST:
        if mid < k:
            continue
        m = mk()
        ok, why = m.propose(late[:k], np.full(k, label), 'ky_su')
        out[f'k{k}'] = {'accepted': bool(ok), 'why': why, 'acc': float((m.predict_proba(test).argmax(1) == label).mean())}
        bad = (label % 3)+1  # nhãn sai có chủ đích
        m2 = mk()
        ok2, why2 = m2.propose(late[:k], np.full(k, bad), 'ky_su')
        out[f'bad{k}'] = {'accepted': bool(ok2), 'why': why2, 'acc': float((m2.predict_proba(test).argmax(1) == label).mean())}
    return out


def cage_v2(n, fs, fr, orders, prior, rng):
    """Vỡ vòng cách v2: xung mạnh theo vòng quay cách (FTF), kèm cụm nhiễu theo FTF."""
    h, meta = _pulse(rng, prior, fs)
    slip = _draw(rng, prior.slip)
    ftf = orders['ftf']*fr*(1-slip)
    m = int(rng.integers(1, 3))
    count = int(n/fs*ftf*m)+2
    pos = (np.arange(count)+rng.uniform(0, 1)+rng.normal(0, .03, count))/(ftf*m)
    amps = rng.lognormal(0, .35, count)
    x = _train(pos*fs, amps, h, n)
    t = np.arange(n)/fs
    burst = np.clip(np.cos(2*np.pi*ftf*t+rng.uniform(0, 2*np.pi)), 0, None)**4
    x = x+rng.uniform(.1, .6)*np.sqrt(np.mean(x**2))*burst*rng.normal(0, 1, n)
    return x, meta | {'ftf_hz': ftf, 'pulses_per_rev': m}


def inject_v2(bg, fr, orders, prior, rng):
    n_sim = int(np.ceil(X.N*FS_SIM/X.FS))+int(.05*FS_SIM)
    raw, _ = cage_v2(n_sim, FS_SIM, fr, orders, prior, rng)
    x = fault_path(raw, FS_SIM, X.SENSOR)[-X.N:]
    x = (x-x.mean())/np.sqrt(np.mean((x-x.mean())**2))
    amp = _draw(rng, prior.amp_rel, log=True)
    gain = np.exp(rng.normal(0, .5))
    return np.stack([output_stage(bg[0]+x*amp*np.sqrt(np.mean(bg[0]**2)), X.SENSOR),
                     output_stage(bg[1]+x*amp*gain*np.sqrt(np.mean(bg[1]**2)), X.SENSOR)])


def cage_job(job):
    name, seed = job
    label = X.CLASSES.index(X.LABEL[name])
    d = X.bearing_data(name)
    fr, orders, n = d['fr'], X.UER204.orders(), d['norm']
    rng = np.random.default_rng([seed, 77, sum(map(ord, name))])
    sets, _ = X.injected_set(d['raw_base'], fr, orders, X.Prior(), ('inner', 'outer'), X.N_INJECT, rng)
    base = d['raw_base']
    v2 = np.array([inject_v2(base[int(rng.integers(len(base)))], fr, orders, X.Prior(), rng) for _ in range(X.N_INJECT)])
    Xa = np.concatenate([n(d['f']['base'])]+[n(X.axis_features(sets[k], fr, orders)) for k in ('inner', 'outer')]+[n(X.axis_features(v2, fr, orders))])
    ya = np.concatenate([np.zeros(len(d['f']['base']), int)]+[np.full(X.N_INJECT, i+1) for i in range(3)])
    m = RandomForestClassifier(random_state=seed, **X.RF).fit(Xa, ya)
    zl = n(d['f']['late'])
    p = X.expand(m.predict_proba(zl), m.classes_)
    z = zl
    half = z.shape[1]//2
    env = {c: float(np.mean(z[:, slice(*X.ENV[c])].mean(1))) for c in X.FAULTS}
    env2 = {c: float(np.mean(z[:, slice(X.ENV[c][0]+half, X.ENV[c][1]+half)].mean(1))) for c in X.FAULTS}
    return {'name': name, 'seed': seed, 'label': X.LABEL[name], 'acc': float((p.argmax(1) == label).mean()), 'counts': np.bincount(p.argmax(1), minlength=4).tolist(), 'env_z_H': env, 'env_z_V': env2,
            'hold': float((X.expand(m.predict_proba(n(d['f']['hold'])), m.classes_).argmax(1) == 0).mean())}


def ims_gate():
    """Cổng HI có phân biệt ổ hỏng và ổ đối chứng trên IMS không? Đặc trưng băng 1 kHz một trục."""
    C = ROOT.parent/'data'/'ims'/'cache'
    from scipy import stats
    rows = {}
    for name, role in (('t1_b3', 'hong'), ('t1_b4', 'hong'), ('t2_b1', 'hong'), ('t3_b3', 'hong'), ('t1_b1', 'doi_chung'), ('t1_b2', 'doi_chung'), ('t2_b2', 'doi_chung'), ('t2_b3', 'doi_chung'), ('t2_b4', 'doi_chung'), ('t3_b1', 'doi_chung'), ('t3_b2', 'doi_chung'), ('t3_b4', 'doi_chung')):
        x = np.load(C/f'{name}.npy').astype(float)
        x = x-x.mean(1, keepdims=True)
        rms = np.sqrt((x**2).mean(1))+1e-15
        f, p = signal.welch(x, 4000, nperseg=256, axis=1)
        bands = [np.log(p[:, (f >= a) & (f < b)].sum(1)+1e-18) for a, b in zip(range(0, 1000, 200), range(200, 1200, 200))]
        F = np.column_stack([np.log(rms), stats.kurtosis(x, axis=1), np.abs(x).max(1)/rms]+bands)
        b = F[:30]
        inv = np.linalg.pinv(LedoitWolf().fit(b).covariance_)
        d = F-b.mean(0)
        hi = np.sqrt(np.maximum(np.einsum('ij,jk,ik->i', d, inv, d), 0)/F.shape[1])
        y = np.log(np.maximum(hi, 1e-6))
        ref = y[:30]
        med, mad = np.median(ref), 1.4826*np.median(np.abs(ref-np.median(ref)))+1e-6
        z = (y-med)/mad
        res = {'role': role, 'n': len(x)}
        for h in (5, 10, 25):
            run, first = 0, None
            for i in range(30, len(z)):
                run = run+1 if z[i] > h else 0
                if run >= 5:
                    first = i
                    break
            res[f'z{h}'] = None if first is None else round(first/len(z), 3)
        res['z_late10_median'] = float(np.median(z[-max(5, len(z)//10):]))
        rows[name] = res
        print(name, res, flush=True)
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    names = list(X.LABEL)
    with ProcessPoolExecutor(14) as pool:
        rt = list(pool.map(retrain_job, [(n, s) for n in names for s in X.SEEDS]))
        cg = list(pool.map(cage_job, [(n, s) for n in names for s in X.SEEDS]))
    print('== hoc lai: do dung o nua sau cua 10% cuoi doi')
    for label in X.FAULTS:
        part = [r for r in rt if r['label'] == label]
        by = {'v1': np.mean([r['v1'] for r in part])}
        for k in K_LIST:
            v = [r[f'k{k}'] for r in part if f'k{k}' in r]
            b = [r[f'bad{k}'] for r in part if f'bad{k}' in r]
            by[f'k{k}'] = (round(float(np.mean([a['acc'] for a in v])), 3), f"chap_nhan {sum(a['accepted'] for a in v)}/{len(v)}", f"nhan_sai_chap_nhan {sum(a['accepted'] for a in b)}/{len(b)}", 'acc_nhan_sai', round(float(np.mean([a['acc'] for a in b])), 3))
        print(label, round(by.pop('v1'), 3), by, flush=True)
    why = {}
    for r in rt:
        for k in K_LIST:
            if f'bad{k}' in r and not r[f'bad{k}']['accepted']:
                w = r[f'bad{k}']['why'].split(':')[0]
                why[w] = why.get(w, 0)+1
    print('ly do chan nhan sai', why)
    print('== vong cach v2')
    for n in names:
        part = [r for r in cg if r['name'] == n]
        print(n, part[0]['label'], round(float(np.mean([r['acc'] for r in part])), 2), part[0]['counts'], 'hold', round(float(np.mean([r['hold'] for r in part])), 2),
              'envZ_H', {k: round(v, 1) for k, v in part[0]['env_z_H'].items()}, flush=True)
    per = {c: float(np.mean([np.mean([r['acc'] for r in cg if r['name'] == n]) for n in names if X.LABEL[n] == c])) for c in X.FAULTS}
    print('macro theo lop', {k: round(v, 3) for k, v in per.items()}, 'macro3', round(float(np.mean(list(per.values()))), 3))
    print('== cong HI tren IMS')
    gate = ims_gate()
    (OUT/'retrain_cage_gate.json').write_text(json.dumps({'retrain': rt, 'cage_v2': cg, 'cage_v2_macro': per, 'ims_gate': gate, 'block_reasons': why}, indent=1, default=float))


if __name__ == '__main__':
    main()
