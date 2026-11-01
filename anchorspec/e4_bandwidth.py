"""E4 (khám phá; XJTU, Paderborn đã mở): băng thông cảm biến đổi kết quả thế nào?

Cùng phương pháp (phễu, cấy tiên nghiệm rộng), chỉ đổi cảm biến. Dùng để đề xuất phần cứng cho máy quan trọng.
"""
from concurrent.futures import ProcessPoolExecutor
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('OMP_NUM_THREADS', '1')

import numpy as np  # noqa: E402
from scipy import signal, stats  # noqa: E402
from sklearn.covariance import LedoitWolf  # noqa: E402

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import funnel as Fu  # noqa: E402
import tn2b_xjtu as X  # noqa: E402
from bearing import PADERBORN_6203  # noqa: E402
from cheap_sensor import CheapSensor, simulate, windows  # noqa: E402

OUT = ROOT/'results'/'e4'
CFG = {'1k_4kHz': CheapSensor(), '1.56k_4kHz': CheapSensor(bw_hz=1560.), '2k_8kHz': CheapSensor(fs_out=8000, bw_hz=2000.),
       '6k_16kHz_8g': CheapSensor(fs_out=16000, bw_hz=6000.), '6k_16kHz_50g': CheapSensor(fs_out=16000, bw_hz=6000., range_g=50., bits=16)}
SEEDS = (11, 29)
BINS = ((.3, .5), (.5, .7), (.7, .9), (.9, 1.))


def xjtu_x(name, cfg):
    p = ROOT.parent/'data'/'xjtu'/'cache_bw'/f'{cfg}_{name}.npy'
    if p.exists():
        return np.load(p, mmap_mode='r')
    p.parent.mkdir(exist_ok=True)
    sen = CFG[cfg]
    folder = X.RAW/X.FOLDER[name[0]][0]/f'Bearing{name}'
    files = sorted(folder.glob('*.csv'), key=lambda f: int(f.stem))
    out = np.zeros((len(files), 2, sen.fs_out), np.float32)
    seed = int.from_bytes(name.encode(), 'big') % 2**31
    for i, f in enumerate(files):
        a = np.loadtxt(f, delimiter=',', skiprows=1).T
        for j in range(2):
            out[i, j] = simulate(a[j], 25600, sen, np.random.default_rng([seed, i, j]))[:sen.fs_out]
    tmp = p.with_suffix('.tmp.npy')
    np.save(tmp, out)
    tmp.replace(p)  # ghi nguyên tử để không bao giờ đọc phải tệp dở dang
    return np.load(p, mmap_mode='r')


def chunked(x, fn, size=128):
    return np.concatenate([fn(np.asarray(x[i:i+size], float)) for i in range(0, len(x), size)])


def hi_features(x, fs, bw):
    """(n, trục, N) -> đặc trưng HI đơn giản, độc lập nhãn."""
    out = []
    for a in range(x.shape[1]):
        v = np.asarray(x[:, a], float)
        v = v-v.mean(1, keepdims=True)
        r = np.sqrt((v**2).mean(1))+1e-15
        f, p = signal.welch(v, fs, nperseg=min(256, v.shape[1]), axis=1)
        e = np.linspace(0, bw, 6)
        out += [np.log(r), stats.kurtosis(v, axis=1), np.abs(v).max(1)/r]+[np.log(p[:, (f >= u) & (f < w)].sum(1)+1e-18) for u, w in zip(e[:-1], e[1:])]
    return np.column_stack(out)


def alarm_frac(x, fs, bw, b, h=10.):
    F = chunked(x, lambda v: hi_features(v, fs, bw))
    base = F[:b]
    inv = np.linalg.pinv(LedoitWolf().fit(base).covariance_)
    d = F-base.mean(0)
    hi = np.sqrt(np.maximum(np.einsum('ij,jk,ik->i', d, inv, d), 0)/F.shape[1])
    y = np.log(np.maximum(hi, 1e-6))
    med = np.median(y[:b])
    z = (y-med)/(1.4826*np.median(np.abs(y[:b]-med))+1e-6)
    run = 0
    for i in range(b, len(z)):
        run = run+1 if z[i] > h else 0
        if run >= 5:
            return i/len(z)
    return None


def prep(a):
    return xjtu_x(a[1], a[0]).shape


def xjtu_job(a):
    cfg, name, seed = a
    sen = CFG[cfg]
    fs, bw = sen.fs_out, float(sen.bw_hz)
    x = xjtu_x(name, cfg)
    base, hold, _ = X.split(np.arange(len(x)))
    base, hold = np.asarray(x[base], float), np.asarray(x[hold], float)
    fr, o = X.fr_of(name), X.UER204.orders()
    m = Fu.fit_funnel(base, fr, o, sen, fs, seed, ('inner', 'outer'), max_hz=bw)
    z = m.z(chunked(x, lambda v: Fu.feats(v, fs, fr, o, bw)))
    p = m.multi_prob(z)
    pred = np.array([p[max(0, i-4):i+1].mean(0) for i in range(len(p))]).argmax(1)
    s = m.scores(z)
    s = np.array([s[max(0, i-4):i+1].mean(0) for i in range(len(s))])
    ans = Fu.decide(s, m.physics(z), np.array([m.tau[k] for k in m.kinds]))
    N = len(x)
    lab = X.LABEL[name]
    k = {'inner': 1, 'outer': 2}.get(lab)
    start = len(base)+5
    r = {'cfg': cfg, 'name': name, 'lab': lab, 'seed': seed, 'alarm': alarm_frac(x, fs, bw, len(base)), 'hold_goi_loi': float((pred[len(base):start] > 0).mean())}
    late = np.arange(N-max(5, N//10), N)
    r['late_acc'] = float((pred[late] == k).mean()) if k else None
    r['cov'] = float((ans[late] > 0).mean())
    r['sel'] = float((ans[late][ans[late] > 0] == k).mean()) if k and (ans[late] > 0).any() else None
    for lo, hi in BINS:
        idx = np.arange(max(int(lo*N), start), int(hi*N))
        r[f'b{lo}'] = float((pred[idx] == k).mean()) if k and len(idx) else None
    return r


def pb_x(code, sen):
    a = np.load(ROOT.parent/'data'/'paderborn'/'cache'/f'{code}.npz')
    rows = [windows(simulate(v.astype(float)/9.81, 64000, sen, np.random.default_rng([i, sum(map(ord, code))])), sen.fs_out) for i, v in enumerate(a['vib'])]
    return np.concatenate(rows)[:, None, :]


def pb_job(a):
    cfg, code, seed = a
    sen = CFG[cfg]
    fs, bw = sen.fs_out, float(sen.bw_hz)
    o = PADERBORN_6203.orders()
    base = np.concatenate([pb_x(c, sen) for c in ('K001', 'K002', 'K003')])
    m = Fu.fit_funnel(base, 25., o, sen, fs, seed, ('inner', 'outer'), max_hz=bw)
    t = m.z(Fu.feats(pb_x(code, sen), fs, 25., o, bw))
    k = 2 if code.startswith('KA') else 1
    return {'cfg': cfg, 'name': code, 'lab': 'outer' if k == 2 else 'inner', 'seed': seed, 'late_acc': float((m.multi_prob(t).argmax(1) == k).mean())}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(4) as pool:
        list(pool.map(prep, [(c, n) for c in CFG for n in X.LABEL], chunksize=1))
        xr = list(pool.map(xjtu_job, [(c, n, s) for c in CFG for n in X.LABEL for s in SEEDS], chunksize=1))
        pr = list(pool.map(pb_job, [(c, n, s) for c in CFG for n in ('KA04', 'KA15', 'KA16', 'KA30', 'KA22', 'KI04', 'KI14', 'KI16', 'KI17', 'KI18', 'KI21') for s in SEEDS], chunksize=1))
    tab = {}
    for c in CFG:
        part = [r for r in xr if r['cfg'] == c]
        per = lambda key, lab: np.mean([np.mean([r[key] for r in part if r['name'] == n and r[key] is not None] or [np.nan]) for n in sorted({r['name'] for r in part if r['lab'] == lab})])
        al = [np.mean([r['alarm'] for r in part if r['name'] == n and r['alarm'] is not None] or [np.nan]) for n in X.LABEL]
        pp = [r for r in pr if r['cfg'] == c]
        pb = {l: np.mean([np.mean([r['late_acc'] for r in pp if r['name'] == n]) for n in sorted({r['name'] for r in pp if r['lab'] == l})]) for l in ('inner', 'outer')}
        tab[c] = {'xjtu_trong': float(per('late_acc', 'inner')), 'xjtu_ngoai': float(per('late_acc', 'outer')), 'macro2': float(.5*(per('late_acc', 'inner')+per('late_acc', 'outer'))),
                  'tra_loi_trong': float(per('cov', 'inner')), 'tra_loi_ngoai': float(per('cov', 'outer')), 'dung_tra_loi_trong': float(per('sel', 'inner')), 'dung_tra_loi_ngoai': float(per('sel', 'outer')), 'cach_bi_tra_loi': float(per('cov', 'cage')),
                  **{f'ngoai_{lo}': float(per(f'b{lo}', 'outer')) for lo, _ in BINS}, **{f'trong_{lo}': float(per(f'b{lo}', 'inner')) for lo, _ in BINS},
                  'canh_bao_trung_vi': float(np.nanmedian(al)), 'khong_canh_bao': int(np.sum(np.isnan(al))), 'canh_bao_truoc_50': int(np.sum(np.array(al) < .5)), 'hold_goi_loi': float(np.mean([r['hold_goi_loi'] for r in part])),
                  'pb_trong': float(pb['inner']), 'pb_ngoai': float(pb['outer']), 'pb_macro': float(.5*(pb['inner']+pb['outer']))}
        print(c, {k: round(v, 3) if isinstance(v, float) else v for k, v in tab[c].items()}, flush=True)
    (OUT/'e4.json').write_text(json.dumps({'table': tab, 'xjtu': xr, 'paderborn': pr}, indent=1, default=float))


if __name__ == '__main__':
    main()
