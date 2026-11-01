"""TN2: lỗi cấy (A) có thay được hỏng nhân tạo (B) và dữ liệu máy khác (C) không?

Các giai đoạn: prepare -> dev -> freeze -> test. Bearing test KHÔNG được đọc trước
`test`; `test` kiểm tra hash mã nguồn so với FROZEN.json và từ chối chạy lại.
Giao thức: PROTOCOL_TN2.md.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np
from scipy.io import loadmat
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from bearing import CWRU_6205, PADERBORN_6203  # noqa: E402
from cheap_sensor import CheapSensor, simulate, windows  # noqa: E402
from features import HealthyNorm, extract  # noqa: E402
from injection import Prior, inject, quality_gate  # noqa: E402

DATA = ROOT.parent/'data'
PB = DATA/'paderborn'
OUT = ROOT/'results'/'tn2'
CONDITION = 'N15_M07_F10'
NOMINAL_RPM = 1500.
SEEDS = (11, 29, 47)
CLASSES = ('healthy', 'inner', 'outer')
N_INJECT = 400
UNIT_TO_G = 1/9.81  # Paderborn không ghi đơn vị (Unit rỗng). Giả định m/s² (ca nhiễu bất lợi hơn); xem PROTOCOL_TN2.md
SPLIT = {
    'healthy_train': ['K001', 'K002', 'K003'], 'healthy_dev': ['K004'], 'healthy_test': ['K005', 'K006'],
    'b_outer': ['KA01', 'KA03', 'KA05', 'KA06', 'KA07', 'KA08', 'KA09'],
    'b_inner': ['KI01', 'KI03', 'KI05', 'KI07', 'KI08'],
    'dev_outer': ['KA22'], 'dev_inner': ['KI21'],
    'test_outer': ['KA04', 'KA15', 'KA16', 'KA30'], 'test_inner': ['KI04', 'KI14', 'KI16', 'KI17', 'KI18'],
}
CWRU = {'healthy': [97, 98, 99, 100],
        'inner': [105, 106, 107, 108, 169, 170, 171, 172, 209, 210, 211, 212],
        'outer': [130, 131, 132, 133, 197, 198, 199, 200, 234, 235, 236, 237]}
INDUSTRIAL = CheapSensor(fs_out=64000, bw_hz=None, noise_ug_rthz=0, range_g=None, bits=None)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def code_hashes():
    return {p.name: sha(p) for p in sorted(ROOT.glob('*.py'))}


def prepare():
    """Giải nén đúng một điều kiện vận hành; chỉ lấy rung và tốc độ."""
    (PB/'cache').mkdir(parents=True, exist_ok=True)
    manifest = {}
    for code in sum(SPLIT.values(), []):
        out = PB/'cache'/f'{code}.npz'
        rar = PB/'rar'/f'{code}.rar'
        manifest[code] = {'rar_sha256': sha(rar), 'bytes': rar.stat().st_size}
        if out.exists():
            continue
        with tempfile.TemporaryDirectory(dir=PB) as tmp:
            subprocess.run([str(Path(sys.executable).parent/'bsdtar'), '-xf', str(rar), '-C', tmp,
                            f'{code}/{CONDITION}_{code}_*.mat'], check=True)
            files = sorted(Path(tmp, code).glob('*.mat'), key=lambda p: int(p.stem.rsplit('_', 1)[1]))
            if len(files) != 20:
                raise ValueError(f'{code}: expected 20 recordings, got {len(files)}')
            vib, speed = [], []
            for f in files:
                s = loadmat(f, squeeze_me=True, struct_as_record=False)[f.stem]
                ch = {str(y.Name): y for y in s.Y}
                vib.append(np.asarray(ch['vibration_1'].Data, np.float32))
                speed.append(float(np.mean(ch['speed'].Data)))
            n = min(map(len, vib))
            np.savez(out, vib=np.stack([v[:n] for v in vib]), speed=np.array(speed))
        print('cached', code, flush=True)
    (PB/'cache'/'manifest.json').write_text(json.dumps(manifest, indent=1))


def load_bearing(code, sensor, seed, allowed):
    """Chặn đọc nhầm: code phải nằm trong tập được phép của giai đoạn hiện tại."""
    if code not in allowed:
        raise PermissionError(f'{code} is not allowed in this stage')
    a = np.load(PB/'cache'/f'{code}.npz')
    rec = []
    rng = np.random.default_rng([seed, int.from_bytes(code.encode(), 'big') % 2**31])
    for i, v in enumerate(a['vib']):
        y = simulate(v.astype(float)*UNIT_TO_G, 64000, sensor, rng if sensor.noise_ug_rthz > 0 else None)
        rec.append({'y': y, 'speed': float(a['speed'][i])})
    return rec


def bearing_features(code, sensor, seed, allowed, orders=None, max_hz=1000.):
    orders = orders or PADERBORN_6203.orders()
    win, feats, frs = [], [], []
    for r in load_bearing(code, sensor, seed, allowed):
        fr = NOMINAL_RPM/60  # tốc độ danh định; bộ ước lượng chưa đạt cổng 1%, xem PROTOCOL
        w = windows(r['y'], sensor.fs_out)
        win.append(w)
        frs.extend([fr]*len(w))
        feats.append(extract(w, sensor.fs_out, fr, orders, max_hz))
    return np.concatenate(feats), np.concatenate(win), np.array(frs)


def cwru_features(sensor, seed):
    out, orders = {}, CWRU_6205.orders()
    for label, ids in CWRU.items():
        rows = []
        for number in ids:
            m = loadmat(DATA/'cwru'/f'{number}.mat')
            raw = np.asarray(m[f'X{number:03d}_DE_time'], float).ravel()
            rpm = float(np.asarray(m.get(f'X{number:03d}RPM', 1797)).ravel()[0])
            rng = np.random.default_rng([seed, number])
            y = simulate(raw, 48000 if label == 'healthy' else 12000, sensor, rng)
            rows.append(extract(windows(y, sensor.fs_out), sensor.fs_out, rpm/60, orders))
        out[label] = np.concatenate(rows)
    return out


def fit_rf(x, y, seed):
    return RandomForestClassifier(n_estimators=200, max_features='sqrt', bootstrap=False,
                                  class_weight='balanced', random_state=seed, n_jobs=-1).fit(x, y)


def injected(backgrounds, frs, kind, n, sensor, prior, rng, label_source):
    """Cấy tới khi đủ n mẫu qua cổng; ghi mọi lần thử bị loại."""
    orders = PADERBORN_6203.orders()
    out, fr_out, ledger, rejected = [], [], [], {}
    attempts = 0
    while len(out) < n:
        attempts += 1
        if attempts > 4*n:
            raise RuntimeError(f'Quota failed {kind}: {rejected}')
        i = int(rng.integers(len(backgrounds)))
        y, meta = inject(backgrounds[i], kind, frs[i], orders, sensor, prior, rng, label_source)
        reason = quality_gate(y, backgrounds[i], sensor)
        if reason:
            rejected[reason] = rejected.get(reason, 0)+1
            continue
        out.append(y)
        fr_out.append(frs[i])
        ledger.append(meta)
    return np.array(out), np.array(fr_out), ledger, rejected


def features_by_fr(x, frs, sensor, orders):
    out = None
    uniq = np.unique(frs)
    for u in uniq:
        idx = np.where(frs == u)[0]
        f = extract(x[idx], sensor.fs_out, float(u), orders)
        if out is None:
            out = np.zeros((len(x), f.shape[1]))
        out[idx] = f
    return out


def calibrate(hw, hfr, real_norm, norm, sensor, kind, seed, draws=300, keep=.05, batch=16):
    """ABC từ chối: W1 trung bình trên đặc trưng chuẩn hóa so với lỗi thật của tập DEV."""
    rng = np.random.default_rng([seed, 991, ord(kind[0])])
    orders = PADERBORN_6203.orders()
    base = Prior()
    rows = []
    sort_real = np.sort(real_norm, axis=0)
    for _ in range(draws):
        amp = float(np.exp(rng.uniform(np.log(base.amp_rel[0]), np.log(base.amp_rel[1]))))
        fl = rng.uniform(*base.fn_low_hz)
        z = rng.uniform(*base.zeta)
        fixed = Prior(amp_rel=(amp, amp), fn_low_hz=(fl, fl), zeta=(z, z))
        idx = rng.integers(len(hw), size=batch)
        ys = np.array([inject(hw[i], kind, hfr[i], orders, sensor, fixed, rng)[0] for i in idx])
        f = np.sort(norm(extract(ys, sensor.fs_out, float(hfr[0]), orders)), axis=0)
        q = (np.arange(batch)+.5)/batch
        w1 = np.mean(np.abs(f-np.quantile(sort_real, q, axis=0)))
        rows.append((w1, amp, fl, z))
    rows = np.array(sorted(rows))
    top = rows[:max(3, int(keep*draws))]
    return {'amp_rel': [float(top[:, 1].min()), float(top[:, 1].max())],
            'fn_low_hz': [float(top[:, 2].min()), float(top[:, 2].max())],
            'zeta': [float(top[:, 3].min()), float(top[:, 3].max())],
            'w1_best': float(rows[0, 0]), 'w1_kept_max': float(top[-1, 0]), 'w1_median_all': float(np.median(rows[:, 0]))}


def build_train(seed, sensor, allowed, priors):
    """Trả về dict nhánh -> (X đã chuẩn hóa, y). Cùng một nền/chuẩn hóa Paderborn."""
    h = [bearing_features(c, sensor, seed, allowed) for c in SPLIT['healthy_train']]
    hx = np.concatenate([a[0] for a in h])
    hw = np.concatenate([a[1] for a in h])
    hfr = np.concatenate([a[2] for a in h])
    norm = HealthyNorm().fit(hx)
    orders = PADERBORN_6203.orders()
    rng = np.random.default_rng([seed, 2024])
    arms, audit = {}, {}
    hn = norm(hx)
    for arm, prior in priors.items():
        xs, ys = [hn], [np.zeros(len(hn), int)]
        audit[arm] = {}
        for k, kind in ((1, 'inner'), (2, 'outer')):
            w, fr, ledger, rejected = injected(hw, hfr, kind, N_INJECT, sensor, prior[kind], rng, 'K001-K003')
            xs.append(norm(features_by_fr(w, fr, sensor, orders)))
            ys.append(np.full(N_INJECT, k))
            audit[arm][kind] = {'accepted': len(ledger), 'rejected': rejected,
                'ledger_sha256': hashlib.sha256(json.dumps(ledger, sort_keys=True).encode()).hexdigest(),
                'amp_rel_median': float(np.median([m['amp_rel'] for m in ledger]))}
        arms[arm] = (np.concatenate(xs), np.concatenate(ys))
    bx, by = [hn], [np.zeros(len(hn), int)]
    for k, group in ((1, 'b_inner'), (2, 'b_outer')):
        for code in SPLIT[group]:
            f = norm(bearing_features(code, sensor, seed, allowed)[0])
            bx.append(f)
            by.append(np.full(len(f), k))
    arms['B_nhan_tao'] = (np.concatenate(bx), np.concatenate(by))
    c = cwru_features(sensor, seed)
    cn = HealthyNorm().fit(c['healthy'])
    cx = [cn(c[k]) for k in CLASSES]
    cy = [np.full(len(v), i) for i, v in enumerate(cx)]
    arms['C_cwru'] = (np.concatenate(cx), np.concatenate(cy))
    arms['C2_cwru_nen_may'] = (np.concatenate([hn]+cx[1:]), np.concatenate([np.zeros(len(hn), int)]+cy[1:]))
    return arms, norm, audit


def evaluate(models, norm, seed, sensor, groups, allowed):
    """Kết quả theo ổ bi. Trả về độ đúng cửa sổ theo từng ổ và dự đoán đa số."""
    res = {}
    cache = {}
    for code, k in groups.items():
        cache[code] = (norm(bearing_features(code, sensor, seed, allowed)[0]), k)
    for arm, model in models.items():
        res[arm] = {}
        all_scores, all_y = [], []
        for code, (x, k) in cache.items():
            p = model.predict_proba(x)
            pred = p.argmax(1)
            votes = np.bincount(pred, minlength=3)
            res[arm][code] = {'true': CLASSES[k], 'window_acc': float((pred == k).mean()), 'n': int(len(x)),
                              'majority': CLASSES[int(votes.argmax())], 'pred_counts': votes.tolist()}
            if k > 0:  # đúng loại khi đã biết bất thường: so inner/outer, bỏ qua lớp bình thường
                res[arm][code]['type_given_fault'] = float((p[:, k] > p[:, 3-k]).mean())
            all_scores.append(1-p[:, 0])
            all_y.append(np.full(len(x), int(k > 0)))
        res[arm]['_auc_fault_vs_healthy'] = float(roc_auc_score(np.concatenate(all_y), np.concatenate(all_scores)))
    return res


def score(per_seed, arm, codes_inner, codes_outer, codes_healthy):
    """Điểm chính: trung bình theo lớp của độ đúng theo ổ bi (2 lớp lỗi)."""
    out = []
    for r in per_seed:
        acc = lambda cs: float(np.mean([r[arm][c]['window_acc'] for c in cs]))
        out.append({'inner': acc(codes_inner), 'outer': acc(codes_outer), 'healthy': acc(codes_healthy),
                    'primary': .5*(acc(codes_inner)+acc(codes_outer)),
                    'type_given_fault': .5*(float(np.mean([r[arm][c].get('type_given_fault', np.nan) for c in codes_inner]))
                                            +float(np.mean([r[arm][c].get('type_given_fault', np.nan) for c in codes_outer]))),
                    'bearing_vote': sum(r[arm][c]['majority'] == r[arm][c]['true'] for c in codes_inner+codes_outer),
                    'auc': r[arm]['_auc_fault_vs_healthy']})
    return {k: float(np.mean([o[k] for o in out])) for k in out[0]} | {
        'primary_seeds': [o['primary'] for o in out], 'bearing_vote_seeds': [o['bearing_vote'] for o in out],
        'n_fault_bearings': len(codes_inner)+len(codes_outer)}


def bootstrap_diff(per_seed, a, b, inner, outer, n=10000, seed=0):
    """CI 95% cho hiệu điểm chính, lấy mẫu lại Ổ BI trong từng lớp (seed chỉ lấy trung bình)."""
    m = lambda arm, cs: np.mean([[r[arm][c]['window_acc'] for c in cs] for r in per_seed], axis=0)
    ai, ao, bi, bo = m(a, inner), m(a, outer), m(b, inner), m(b, outer)
    rng = np.random.default_rng(seed)
    d = []
    for _ in range(n):
        i, o = rng.integers(len(inner), size=len(inner)), rng.integers(len(outer), size=len(outer))
        d.append(.5*((ai-bi)[i].mean()+(ao-bo)[o].mean()))
    return {'diff': float(.5*((ai-bi).mean()+(ao-bo).mean())), 'ci95': [float(np.quantile(d, .025)), float(np.quantile(d, .975))]}


def priors_from(cal):
    """Prior đã hiệu chỉnh: thu hẹp amp/fn/zeta theo ABC, phần còn lại giữ nguyên."""
    out = {}
    for kind in ('inner', 'outer'):
        c = cal[kind]
        out[kind] = Prior(amp_rel=tuple(c['amp_rel']), fn_low_hz=tuple(c['fn_low_hz']), zeta=tuple(c['zeta']))
    return out


def run(stage, cal, allowed, groups, inner, outer, healthy, compare):
    sensor = CheapSensor()
    per_seed, audits = [], {}
    for seed in SEEDS:
        priors = {'A0_cay_chua_chinh': {'inner': Prior(), 'outer': Prior()}, 'A_cay_da_chinh': priors_from(cal[str(seed)])}
        arms, norm, audit = build_train(seed, sensor, allowed, priors)
        audits[seed] = audit
        models = {a: fit_rf(x, y, seed) for a, (x, y) in arms.items()}
        per_seed.append(evaluate(models, norm, seed, sensor, groups, allowed))
        print(stage, 'seed', seed, {a: round(float(np.mean([per_seed[-1][a][c]['window_acc'] for c in inner+outer])), 3) for a in models}, flush=True)
    names = list(per_seed[0])
    return {'arms': {a: score(per_seed, a, inner, outer, healthy) for a in names},
            'comparisons': {f'{x} - {y}': bootstrap_diff(per_seed, x, y, inner, outer) for x, y in compare},
            'per_seed': per_seed, 'audit': audits, 'sensor': sensor.as_dict(), 'seeds': SEEDS, 'n_inject': N_INJECT}


COMPARE = [('A_cay_da_chinh', 'C_cwru'), ('A_cay_da_chinh', 'C2_cwru_nen_may'), ('A_cay_da_chinh', 'B_nhan_tao'),
           ('A0_cay_chua_chinh', 'C_cwru'), ('A0_cay_chua_chinh', 'C2_cwru_nen_may'), ('A_cay_da_chinh', 'A0_cay_chua_chinh')]
TRAIN_ALLOWED = set(SPLIT['healthy_train']+SPLIT['b_outer']+SPLIT['b_inner'])
DEV_ALLOWED = TRAIN_ALLOWED|set(SPLIT['healthy_dev']+SPLIT['dev_outer']+SPLIT['dev_inner'])
TEST_ALLOWED = TRAIN_ALLOWED|set(SPLIT['healthy_test']+SPLIT['test_outer']+SPLIT['test_inner'])


def stage_dev_unit_g():
    """Độ nhạy đơn vị, chỉ trên dev: coi kênh rung là g, hiệu chỉnh lại, ghi tệp riêng."""
    global UNIT_TO_G
    UNIT_TO_G = 1.
    stage_dev('_unit_g')


def stage_dev(suffix=''):
    OUT.mkdir(parents=True, exist_ok=True)
    sensor = CheapSensor()
    cal = {}
    for seed in SEEDS:
        h = [bearing_features(c, sensor, seed, DEV_ALLOWED) for c in SPLIT['healthy_train']]
        hx = np.concatenate([a[0] for a in h])
        norm = HealthyNorm().fit(hx)
        hw, hfr = np.concatenate([a[1] for a in h]), np.concatenate([a[2] for a in h])
        cal[str(seed)] = {}
        for kind, code in (('inner', 'KI21'), ('outer', 'KA22')):
            real = norm(bearing_features(code, sensor, seed, DEV_ALLOWED)[0])
            cal[str(seed)][kind] = calibrate(hw, hfr, real, norm, sensor, kind, seed)
            print('calibrated', seed, kind, cal[str(seed)][kind], flush=True)
    (OUT/f'calibration{suffix}.json').write_text(json.dumps(cal, indent=1))
    groups = {'K004': 0, 'KI21': 1, 'KA22': 2}
    result = run('dev', cal, DEV_ALLOWED, groups, ['KI21'], ['KA22'], ['K004'], [])
    (OUT/f'dev{suffix}.json').write_text(json.dumps(result, indent=1, default=int))
    for arm, s in result['arms'].items():
        print(arm, {k: round(v, 3) for k, v in s.items() if isinstance(v, float)}, flush=True)


def stage_freeze():
    frozen = {'code': code_hashes(), 'calibration_sha256': sha(OUT/'calibration.json'), 'dev_sha256': sha(OUT/'dev.json'),
              'protocol_sha256': sha(ROOT/'PROTOCOL_TN2.md'), 'split': SPLIT, 'primary': 'A_cay_da_chinh',
              'rule': 'Khong sua code/tham so sau khi doc ket qua test; test chay mot lan'}
    (OUT/'FROZEN.json').write_text(json.dumps(frozen, indent=1))
    print('frozen', frozen['code']['tn2_paderborn.py'][:12])


def e6(groups, inner, outer, healthy):
    """E6: nhánh B với cảm biến công nghiệp gốc 64 kHz, không qua giả lập; so với B cảm biến rẻ."""
    per_seed = []
    for seed in SEEDS:
        f = lambda c: bearing_features(c, INDUSTRIAL, seed, TEST_ALLOWED, max_hz=30000.)[0]
        hx = np.concatenate([f(c) for c in SPLIT['healthy_train']])
        norm = HealthyNorm().fit(hx)
        xs, ys = [norm(hx)], [np.zeros(len(hx), int)]
        for k, group in ((1, 'b_inner'), (2, 'b_outer')):
            for code in SPLIT[group]:
                xs.append(norm(f(code)))
                ys.append(np.full(len(xs[-1]), k))
        model = fit_rf(np.concatenate(xs), np.concatenate(ys), seed)
        res = {'B_cong_nghiep': {}}
        scores, labels = [], []
        for code, k in groups.items():
            x = norm(f(code))
            p = model.predict_proba(x)
            pred = p.argmax(1)
            votes = np.bincount(pred, minlength=3)
            res['B_cong_nghiep'][code] = {'true': CLASSES[k], 'window_acc': float((pred == k).mean()), 'n': int(len(x)),
                                          'majority': CLASSES[int(votes.argmax())], 'pred_counts': votes.tolist()}
            if k > 0:
                res['B_cong_nghiep'][code]['type_given_fault'] = float((p[:, k] > p[:, 3-k]).mean())
            scores.append(1-p[:, 0])
            labels.append(np.full(len(x), int(k > 0)))
        res['B_cong_nghiep']['_auc_fault_vs_healthy'] = float(roc_auc_score(np.concatenate(labels), np.concatenate(scores)))
        per_seed.append(res)
    return {'score': score(per_seed, 'B_cong_nghiep', inner, outer, healthy), 'per_seed': per_seed}


def stage_test():
    frozen = json.loads((OUT/'FROZEN.json').read_text())
    if frozen['code'] != code_hashes():
        raise ValueError('Code changed after freeze')
    if sha(OUT/'calibration.json') != frozen['calibration_sha256'] or sha(ROOT/'PROTOCOL_TN2.md') != frozen['protocol_sha256']:
        raise ValueError('Calibration/protocol changed after freeze')
    dest = OUT/'test.json'
    if dest.exists():
        raise FileExistsError('Test already opened once; new run needs a new protocol')
    cal = json.loads((OUT/'calibration.json').read_text())
    groups = {c: 0 for c in SPLIT['healthy_test']}|{c: 1 for c in SPLIT['test_inner']}|{c: 2 for c in SPLIT['test_outer']}
    result = run('test', cal, TEST_ALLOWED, groups, SPLIT['test_inner'], SPLIT['test_outer'], SPLIT['healthy_test'], COMPARE)
    result['e6'] = e6(groups, SPLIT['test_inner'], SPLIT['test_outer'], SPLIT['healthy_test'])
    dest.write_text(json.dumps(result, indent=1, default=int))
    for arm, s in result['arms'].items():
        print(arm, {k: round(v, 3) for k, v in s.items() if isinstance(v, float)}, s['bearing_vote_seeds'], flush=True)
    print('E6 B_cong_nghiep', {k: round(v, 3) for k, v in result['e6']['score'].items() if isinstance(v, float)}, flush=True)
    print(json.dumps(result['comparisons'], indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['prepare', 'dev', 'dev_unit_g', 'freeze', 'test'])
    args = ap.parse_args()
    {'prepare': prepare, 'dev': stage_dev, 'dev_unit_g': stage_dev_unit_g, 'freeze': stage_freeze, 'test': stage_test}[args.stage]()
