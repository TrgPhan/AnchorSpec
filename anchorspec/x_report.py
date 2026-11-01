"""Tổng hợp kết quả X1-X7 tải từ Modal."""
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score
R = Path(__file__).resolve().parent/'results'/'x'
def L(n):
    p = R/f'{n}.json'
    return json.loads(p.read_text()) if p.exists() else None
def by_bearing(rows, arm, key, name='n', labfield='lab', labels=None):
    per = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if arm in r and r[arm].get(key) is not None:
            per[r[labfield]][r[name]].append(r[arm][key])
    return {c: float(np.mean([np.mean(v) for v in d.values()])) for c, d in per.items()}
x = L('x1')
if x:
    print('== X1 (E9)', len(x))
    for ds in ('xjtu', 'uored'):
        part = [r for r in x if r['ds'] == ds]
        arms = [a for a in part[0] if isinstance(part[0][a], dict)]
        arms = sorted({a for r in part for a in r if isinstance(r[a], dict)})
        print(ds, 'ban ghi', len(part), 'o', len({r['n'] for r in part}))
        for a in arms:
            acc, tgf, hold = by_bearing(part, a, 'acc'), by_bearing(part, a, 'tgf'), np.mean([r[a]['hold'] for r in part if a in r])
            print(f'  {a:18s} macro {np.mean(list(acc.values())):.3f} tgf {np.mean(list(tgf.values())):.3f} bt {hold:.2f}', {k: round(v, 2) for k, v in acc.items()})
x = L('x2')
if x:
    print('== X2 (E10)')
    for k, v in x.items():
        print(f'  {k:28s}', {a: round(b, 3) if isinstance(b, float) else b for a, b in v.items()})
x = L('x3')
if x:
    print('== X3', len(x))
    conds = ('N15_M07_F10', 'N09_M07_F10', 'N15_M01_F10', 'N15_M07_F04')
    for c in conds:
        h = [r[c] for r in x if r['lab'] == 0]
        f = [r[c] for r in x if r['lab'] > 0]
        print(f'  {c}: bao_nham goc {np.mean([q["hi_nen_goc"] for q in h]):.2f} dung {np.mean([q["hi_nen_dung"] for q in h]):.2f} | phat_hien goc {np.mean([q["hi_nen_goc"] for q in f]):.2f} dung {np.mean([q["hi_nen_dung"] for q in f]):.2f} | rf_loi goc {np.mean([q["rf_nen_goc"] for q in f]):.2f} dung {np.mean([q["rf_nen_dung"] for q in f]):.2f} | rf_bt goc {np.mean([q["rf_nen_goc"] for q in h]):.2f} dung {np.mean([q["rf_nen_dung"] for q in h]):.2f}')
x = L('x4')
if x:
    print('== X4')
    for k, v in x.items():
        print(f'  {k}', {a: round(b, 2) for a, b in v.items()})
x = L('x5')
if x:
    print('== X5', len(x))
    for ds in ('xjtu', 'uored'):
        for arm in ('cu', 'rong'):
            part = [r for r in x if r['ds'] == ds and r['lab'] in ('inner', 'outer')]
            a, t = by_bearing(part, arm, 'acc'), by_bearing(part, arm, 'tgf')
            print(f'  {ds} {arm}: acc {a} tgf {t} macro {np.mean(list(a.values())):.3f}')
x = L('x6')
if x:
    print('== X6', len(x), {r['dev'] for r in x})
    for ds in ('xjtu', 'uored'):
        part = [r for r in x if r['ds'] == ds]
        for arm in ('A_cay', 'D_that'):
            a, t = by_bearing(part, arm, 'acc'), by_bearing(part, arm, 'tgf')
            print(f'  {ds} {arm}: {({k: round(v, 2) for k, v in a.items()})} tgf {({k: round(v, 2) for k, v in t.items()})} bt {np.mean([r[arm]["hold"] for r in part]):.2f}')
x = L('x7')
if x:
    print('== X7', len(x), 'don vi', {r['unit'] for r in x}, 'fr', sorted({round(r['fr'], 1) for r in x})[:8])
    st = defaultdict(list)
    for r in x:
        for t in ('hold', 'I', 'O', 'B', 'IO', 'IB', 'OB'):
            if t in r:
                st[t].append(r[t])
    for t, v in st.items():
        a, m = np.sum([q['ans'] for q in v], axis=0), np.sum([q['m0'] for q in v], axis=0)
        print(f'  {t:5s} n={len(v)} tra_loi {a[1:].sum()/a.sum():.3f} trong/ngoai {a[1]/max(a[1:].sum(), 1):.2f}/{a[2]/max(a[1:].sum(), 1):.2f} M0(bt,trong,ngoai) {np.round(m/m.sum(), 2)} hi10 {np.mean([q["hi10"] for q in v]):.2f}')
    ai, ao = st['I'], st['O']
    ans = lambda v, k: (np.sum([q['ans'] for q in v], axis=0))
    gi, go = ans(ai, 1), ans(ao, 2)
    print('  M1 dung khi tra loi (GOP theo cua so; chi tieu E8 tinh theo o, xem x_recheck.py)', round(.5*(gi[1]/max(gi[1:].sum(), 1)+go[2]/max(go[1:].sum(), 1)), 3), 'tra loi', round(.5*(gi[1:].sum()/gi.sum()+go[1:].sum()/go.sum()), 3))
    mi, mo = np.sum([q['m0'] for q in ai], axis=0), np.sum([q['m0'] for q in ao], axis=0)
    print('  M0 macro', round(.5*(mi[1]/mi.sum()+mo[2]/mo.sum()), 3), 'bt bi goi loi M1', round(1-np.sum([q['ans'] for q in st['hold']], axis=0)[0]/np.sum([q['ans'] for q in st['hold']], axis=0).sum(), 3))
    per = defaultdict(lambda: {})
    for r in x:
        for t, y in (('I', 0), ('O', 0), ('B', 1), ('IB', 1), ('OB', 1)):
            if t in r:
                per[(r['machine'], t)].setdefault('v', []).append(r[t]['mo_ho'])
                per[(r['machine'], t)]['y'] = y
    print('  AUROC chua biet', round(roc_auc_score([p['y'] for p in per.values()], [np.mean(p['v']) for p in per.values()]), 3))
x = L('x8')
if x:
    print('== X8', len(x))
    ARMS = ('1k_cu', '1k_rong', '6k_cu', '6k_rong')
    rs = np.random.default_rng(0)

    def rate(r, a, t, k):
        c = r[a][t]
        return c[k]/max(1, sum(c))
    for ds in ('xjtu', 'uored'):
        part = [r for r in x if r['ds'] == ds and r['lab'] in ('inner', 'outer')]
        hold = [r for r in x if r['ds'] == ds]
        ns = {}
        for r in part:
            ns.setdefault(r['n'], []).append(r)
        val = {a: {n: np.mean([rate(r, a, 'late', 1 if r['lab'] == 'inner' else 2) for r in v]) for n, v in ns.items()} for a in ARMS}
        lab = {n: v[0]['lab'] for n, v in ns.items()}
        def macro(a, keys):
            return np.mean([np.mean([val[a][n] for n in keys if lab[n] == c]) for c in ('inner', 'outer') if any(lab[n] == c for n in keys)])
        keys = list(ns)
        for a in ARMS:
            print(f'  {ds} {a}: macro {macro(a, keys):.3f} bao_nham {np.mean([r[a]["hold_loi"] for r in hold]):.3f}')
        ds_boot = [macro('6k_rong', k)-macro('1k_cu', k) for k in (list(rs.choice(keys, len(keys))) for _ in range(2000))]
        print(f'  {ds} hieu 6k_rong-1k_cu {macro("6k_rong", keys)-macro("1k_cu", keys):+.3f} CI {np.percentile(ds_boot, 2.5):+.3f} {np.percentile(ds_boot, 97.5):+.3f} so o {len(keys)}')
    part = [r for r in x if r['ds'] == 'hust']
    for a in ARMS:
        I, O = np.mean([rate(r, a, 'I', 1) for r in part]), np.mean([rate(r, a, 'O', 2) for r in part])
        print(f'  hust {a}: I {I:.3f} O {O:.3f} macro {(I+O)/2:.3f} bao_nham {np.mean([r[a]["hold_loi"] for r in part]):.3f}')
x = L('x9')
if x:
    print('== X9 (kham pha, qua pheu)', len(x))
    for ds in ('xjtu', 'uored', 'hust'):
        part = [r for r in x if r['ds'] == ds]
        for a in ('1k_cu', '6k_rong'):
            h = np.sum([r[a]['hold'] for r in part], axis=0)
            per = {1: [], 2: []}
            for r in part:
                if ds == 'hust':
                    for t, k in (('I', 1), ('O', 2)):
                        if t in r[a]:
                            per[k].append(r[a][t])
                elif r['lab'] in ('inner', 'outer'):
                    per[1 if r['lab'] == 'inner' else 2].append(r[a]['late'])
            A = {k: np.sum(v, axis=0) for k, v in per.items()}
            right = sum(A[k][k] for k in A)
            ans = sum(A[k][1:].sum() for k in A)
            tot = sum(A[k].sum() for k in A)
            print(f'  {ds} {a}: dung_khi_tra_loi {right/max(ans, 1):.3f} tra_loi {ans/tot:.3f} goi_trong {A[1][1:].sum()/A[1].sum():.3f} goi_ngoai {A[2][1:].sum()/A[2].sum():.3f} bao_nham {h[1:].sum()/h.sum():.3f}')
