"""BW-LIB (PROTOCOL_PB_BW_LIB.md): sensor bandwidth (real events only) and the Paderborn artificial-damage library.
    python pb_bw_lib.py --workers 12
    python pb_bw_lib.py --report
"""
import os
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
import json
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path
import numpy as np
from u_natural import training
from event_experts import causal_average
from diagnostic_experts import fault_labels
import funnel as Fu
import s3_dose as D
import s3_uored as UO
import pb_common as P
from m_dev import Model, inj_only

OUT = P.ROOT / 'results' / 'pb_bw_lib'
SEEDS = (11, 29, 47)
SENSORS = ('1k', '2k', '6k')
PB_BUDGETS = (1, 2, 4)
UO_PROFILES = ('1-1-1', '2-2-2', '4-4-4')
LIB_SENSORS = ('1k', '6k')
ART = P.INNER_ART + P.OUTER_ART


@lru_cache(maxsize=None)
def uored(i, sensor):
    sen = P.SENSORS[sensor]; fs = sen.fs_out
    UO.U.ALLOW_FAULT['on'] = True
    base, hold, fr = UO.U.machine(i, sen)
    severe = UO.U.windows50(UO.U.sensed(i, 2, sen), fs)
    f = lambda w: Fu.feats(w, fs, fr, UO.U.ORDERS, sen.bw_hz)
    return dict(label=UO.CODE[UO.U.LAB[i]], base=f(base), test=f(severe), donor=f(severe[::2][:10]))


def predict(xyw, seed, x):
    m = Model('rf500', seed).fit(*xyw)
    return fault_labels(causal_average(m.predict_proba(x))).tolist()


def job(task):
    start = time.perf_counter()
    kind = task[0]
    if kind == 'bw_pb':
        _, target, seed, m, sensor = task
        t = P.item(target, sensor); H = P.item(P.healthy_for(target, seed), sensor)
        donors = P.pick(P.INNER_REAL, target, seed, 1, m) + P.pick(P.OUTER_REAL, target, seed, 2, m)
        base = training(H['base'], [(n, P.item(n, sensor)['label'], P.item(n, sensor)['donor']) for n in donors], {}, 'real')
        scores = {'real': predict(base, seed, t['test'])}
        label = t['label']
    elif kind == 'bw_uo':
        _, target, seed, prof, sensor = task
        t = uored(target, sensor)
        donors = D.donors_for('uored', target, seed, prof)
        base = training(t['base'], [(n, uored(n, sensor)['label'], uored(n, sensor)['donor']) for n in donors], {}, 'real')
        scores = {'real': predict(base, seed, t['test'])}
        label = t['label']
    else:
        _, target, seed, sensor = task
        sen = P.SENSORS[sensor]
        t = P.item(target, sensor); H = P.item(P.healthy_for(target, seed), sensor)
        lib = [(n, P.item(n, sensor)['label'], P.item(n, sensor)['donor']) for n in ART]
        scores = {'art_only': predict(training(H['base'], lib, {}, 'real'), seed, t['test'])}
        for m in (1, 2):
            real = P.pick(P.INNER_REAL, target, seed, 1, m) + P.pick(P.OUTER_REAL, target, seed, 2, m)
            ev = lib + [(n, P.item(n, sensor)['label'], P.item(n, sensor)['donor']) for n in real]
            scores[f'art+real_{m}'] = predict(training(H['base'], ev, {}, 'real'), seed, t['test'])
        rng = np.random.default_rng([seed, sum(map(ord, target)), 31])
        base_w = H['donor_w'][:, None, :]
        inj = {c: Fu.feats(Fu.injected(base_w, k, 150, P.FR, P.ORDERS, sen, sen.fs_out, rng), sen.fs_out, P.FR, P.ORDERS, sen.bw_hz)
               for c, k in ((1, 'inner'), (2, 'outer'))}
        scores['inj_only'] = predict(inj_only(H['base'], inj), seed, t['test'])
        label = t['label']
    return dict(task=[str(x) for x in task], label=label, scores=scores, elapsed_seconds=time.perf_counter() - start)


def tasks():
    out = [('bw_pb', t, s, m, z) for z in SENSORS for m in PB_BUDGETS for t in P.REAL for s in SEEDS]
    out += [('bw_uo', n, s, p, z) for z in SENSORS for p in UO_PROFILES for n in D.UNAMES for s in SEEDS]
    out += [('lib', t, s, z) for z in LIB_SENSORS for t in P.REAL for s in SEEDS]
    return out


def path(task):
    return OUT / 'tasks' / ('_'.join(str(x) for x in task) + '.json')


def per_bearing(rows, arm):
    d = {}
    for r in rows:
        d.setdefault(r['task'][1], []).append(float(np.mean(np.asarray(r['scores'][arm]) == r['label'])))
    return {k: float(np.mean(v)) for k, v in d.items()}


def report():
    rows = [json.loads(p.read_text()) for p in sorted((OUT / 'tasks').glob('*.json'))]
    rng = np.random.default_rng(20261112)
    fmt = lambda c: f"{c['delta']*100:+.1f} [{c['ci95'][0]*100:+.1f}; {c['ci95'][1]*100:+.1f}]"
    L = ['# BW-LIB: băng thông và thư viện hỏng nhân tạo (RF 500 cây, chỉ chọn loại lỗi)', '', '## Câu 1: băng thông, chỉ sự cố thật', '',
         '| Bộ | 1 kHz | 2 kHz | 6 kHz | 2k − 1k (CI 95%) | 6k − 1k (CI 95%) |', '|---|---:|---:|---:|---|---|']
    out = {'bw': {}, 'lib': {}}; hits = 0
    settings = [('bw_pb', m, (1, 2)) for m in PB_BUDGETS] + [('bw_uo', p, (1, 2, 4)) for p in UO_PROFILES]
    for kind, key, cls in settings:
        per, lab = {}, {}
        for z in SENSORS:
            sub = [r for r in rows if r['task'][0] == kind and r['task'][3] == str(key) and r['task'][4] == z]
            per[z] = per_bearing(sub, 'real'); lab.update({r['task'][1]: r['label'] for r in sub})
        mac = {z: P.macro(per[z], lab, cls) for z in SENSORS}
        c2 = P.bootstrap(per['2k'], per['1k'], lab, rng, classes=cls); c6 = P.bootstrap(per['6k'], per['1k'], lab, rng, classes=cls)
        hits += c6['delta'] >= .05 and c6['ci95'][0] > 0
        name = f"{'Paderborn' if kind == 'bw_pb' else 'UORED'} {key}{' sự cố/loại' if kind == 'bw_pb' else ''}"
        out['bw'][name] = dict(macro=mac, d2k=c2, d6k=c6)
        L.append(f"| {name} | {mac['1k']*100:.1f} | {mac['2k']*100:.1f} | {mac['6k']*100:.1f} | {fmt(c2)} | {fmt(c6)} |")
    L += ['', f"Kết luận theo giao thức: băng thông rộng {'CÓ' if hits >= 2 else 'KHÔNG'} lợi ({hits}/6 bộ đạt +5 với CI dương).", '',
          '## Câu 2: thư viện hỏng nhân tạo (Paderborn, kiểm tra trên 11 ổ hỏng thật)', '',
          '| Cảm biến | Nhánh | Macro 2 lớp | Vòng trong | Vòng ngoài |', '|---|---|---:|---:|---:|']
    for z in LIB_SENSORS:
        lab = {}
        arms = {}
        lib_rows = [r for r in rows if r['task'][0] == 'lib' and r['task'][3] == z]
        for a in ('art_only', 'art+real_1', 'art+real_2', 'inj_only'):
            arms[a] = per_bearing(lib_rows, a)
        lab.update({r['task'][1]: r['label'] for r in lib_rows})
        for m in PB_BUDGETS:
            arms[f'real_{m}'] = per_bearing([r for r in rows if r['task'][0] == 'bw_pb' and r['task'][3] == str(m) and r['task'][4] == z], 'real')
        res = {}
        for a in ('real_1', 'real_2', 'real_4', 'art_only', 'art+real_1', 'art+real_2', 'inj_only'):
            res[a] = P.macro(arms[a], lab)
            inner = np.mean([v for k, v in arms[a].items() if lab[k] == 1]); outer = np.mean([v for k, v in arms[a].items() if lab[k] == 2])
            L.append(f'| {z} | {a} | {res[a]*100:.1f} | {inner*100:.1f} | {outer*100:.1f} |')
        comps = {k: P.bootstrap(arms[a], arms[b], lab, rng) for k, (a, b) in {
            'art_only − real_1': ('art_only', 'real_1'), 'art+real_1 − real_1': ('art+real_1', 'real_1'),
            'art+real_2 − real_2': ('art+real_2', 'real_2'), 'art_only − inj_only': ('art_only', 'inj_only'),
            'inj_only − real_1': ('inj_only', 'real_1')}.items()}
        ok = res['art_only'] >= res['real_1'] and comps['art+real_1 − real_1']['delta'] >= .03 and comps['art+real_1 − real_1']['ci95'][0] > 0
        out['lib'][z] = dict(macro=res, comparisons=comps, usable=bool(ok))
        L += ['', '| So sánh (' + z + ') | Chênh (CI 95%) |', '|---|---|'] + [f'| {k} | {fmt(c)} |' for k, c in comps.items()]
        L += ['', f"Kết luận theo giao thức ({z}): thư viện nhân tạo {'DÙNG ĐƯỢC' if ok else 'KHÔNG ĐẠT'}.", '']
        if z == LIB_SENSORS[0]:
            L += ['| Cảm biến | Nhánh | Macro 2 lớp | Vòng trong | Vòng ngoài |', '|---|---|---:|---:|---:|']
    (OUT / 'summary.json').write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')
    (OUT / 'summary.md').write_text('\n'.join(L), encoding='utf-8'); print('\n'.join(L))


def main():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--workers', type=int, default=12); ap.add_argument('--report', action='store_true')
    ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    (OUT / 'tasks').mkdir(parents=True, exist_ok=True)
    if a.smoke:
        for t in (('bw_pb', 'KI04', 11, 2, '6k'), ('bw_uo', 1, 11, '2-2-2', '2k'), ('lib', 'KA04', 11, '1k')):
            r = job(t); print(t, list(r['scores']), round(r['elapsed_seconds'], 1), 's')
        return
    if not a.report:
        todo = [t for t in tasks() if not path(t).exists()]
        with ProcessPoolExecutor(a.workers) as pool:
            for i, (t, row) in enumerate(zip(todo, pool.map(job, todo)), 1):
                path(t).write_text(json.dumps(row))
                print('bwlib', i, '/', len(todo), t, round(row['elapsed_seconds'], 1), 's', flush=True)
    report()


if __name__ == '__main__':
    main()
