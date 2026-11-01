"""Rà lại số liệu trước báo cáo 03/11: chỉ đọc JSON đã có, không huấn luyện lại.

Tính lại theo đúng công thức E8 (theo ổ, rồi macro theo lớp), và so các nhánh X1
bằng bootstrap theo ổ. Đây là phân tích sau khi đã xem kết quả, nên là khám phá.
"""
import json
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parent/'results'
rs = np.random.default_rng(0)


def L(p):
    return json.loads((R/p).read_text())


def fmt(v):
    return 'khong co' if v is None or (isinstance(v, float) and np.isnan(v)) else f'{v:.3f}'


def macro_by_item(groups):
    """groups: {lop: [giá trị theo ổ, None = ổ không trả lời]}; bỏ None, rồi trung bình theo lớp."""
    vals = [np.mean([v for v in g if v is not None]) for g in groups.values() if any(v is not None for v in g)]
    return float(np.mean(vals)) if vals else None


def answer_stats(counts_by_item):
    """counts_by_item: {ổ: (lớp đúng 1/2, tổng đếm [chưa rõ, trong, ngoài])}. Trả cả hai cách tính."""
    groups, cov = {1: [], 2: []}, {1: [], 2: []}
    pool = {1: np.zeros(3), 2: np.zeros(3)}
    for k, c in counts_by_item.values():
        c = np.asarray(c, float)
        groups[k].append(c[k]/c[1:].sum() if c[1:].sum() else None)
        cov[k].append(c[1:].sum()/c.sum())
        pool[k] += c
    n_ans = sum(1 for g in groups.values() for v in g if v is not None)
    n_all = sum(len(g) for g in groups.values())
    return {'theo_o': macro_by_item(groups), 'tra_loi_theo_o': float(np.mean([np.mean(v) for v in cov.values()])),
            'gop_cua_so': float(np.mean([pool[k][k]/max(pool[k][1:].sum(), 1) for k in pool])),
            'o_co_tra_loi': f'{n_ans}/{n_all}'}


def vote_right(counts, k):
    """Bỏ phiếu cả đợt trên 3 lớp (bình thường, trong, ngoài)."""
    return int(np.argmax(counts) == k)


print('=== E8, UORED, 1 kHz, tung o, giai doan hong nang')
e8 = L('e8/test.json')['bearing']['1k']
LAB = {int(r['i']): r['lab'] for r in L('e8/test.json')['rows']}
c8 = {}
votes = []
det = {'st1': [], 'st2': [], 'hold': []}
for i, e in e8.items():
    lab = LAB[int(i)]
    k = {'inner': 1, 'outer': 2}.get(lab)
    det['st1'].append((lab, e['1']['hi10']))
    det['st2'].append((lab, e['2']['hi10']))
    det['hold'].append(e['hold']['hi10'])
    if k:
        rows = [r for r in L('e8/test.json')['rows'] if int(r['i']) == int(i) and r['cfg'] == '1k']
        ans = np.sum([r['2']['ans'] for r in rows], axis=0)
        c8[i] = (k, ans)
        m0 = np.sum([r['2']['m0'] for r in rows], axis=0)
        votes.append((lab, vote_right(m0, k)))
print(' M1 theo cong thuc:', {a: (fmt(b) if isinstance(b, float) else b) for a, b in answer_stats(c8).items()})
for lab in ('inner', 'outer'):
    print(f'  M0 bo phieu dung o {lab}:', sum(v for l, v in votes if l == lab), '/', sum(1 for l, _ in votes if l == lab))
for st in ('st1', 'st2'):
    a = [v for l, v in det[st] if l in ('inner', 'outer')]
    b = [v for l, v in det[st] if l in ('ball', 'cage')]
    print(f'  HI z>=10 {st}: trong+ngoai TB {np.mean(a):.3f}, o co >=50% cua so {sum(v >= .5 for v in a)}/{len(a)}; bi+cach TB {np.mean(b):.3f}, o co >=50% {sum(v >= .5 for v in b)}/{len(b)}')
print(f'  HI z>=10 doan binh thuong kiem tra: TB {np.mean(det["hold"]):.3f}, lon nhat {np.max(det["hold"]):.3f}')

print('=== X7, HUST, tinh lai theo cong thuc E8 (15 "may", co the dung chung o)')
x7 = L('x/x7.json')
c7, vote7 = {}, {'I': [], 'O': []}
for t, k in (('I', 1), ('O', 2)):
    for m in sorted({r['machine'] for r in x7}):
        rows = [r for r in x7 if r['machine'] == m and t in r]
        if rows:
            c7[(m, t)] = (k, np.sum([r[t]['ans'] for r in rows], axis=0))
            vote7[t].append(vote_right(np.sum([r[t]['m0'] for r in rows], axis=0), k))
print(' M1:', {a: (fmt(b) if isinstance(b, float) else b) for a, b in answer_stats(c7).items()})
print('  M0 bo phieu dung: I', sum(vote7['I']), '/', len(vote7['I']), ' O', sum(vote7['O']), '/', len(vote7['O']))
for size in sorted({r['machine'][0] for r in x7}):
    sub = {a: b for a, b in c7.items() if a[0][0] == size}
    s = answer_stats(sub)
    print(f'  co o {size}: dung theo may {fmt(s["theo_o"])}, tra loi {fmt(s["tra_loi_theo_o"])}')

print('=== X9, qua pheu, tinh lai theo cong thuc E8')
x9 = L('x/x9.json')
for ds in ('xjtu', 'uored', 'hust'):
    part = [r for r in x9 if r['ds'] == ds]
    for a in ('1k_cu', '6k_rong'):
        c = {}
        for n in sorted({r['n'] for r in part}):
            rows = [r for r in part if r['n'] == n]
            if ds == 'hust':
                for t, k in (('I', 1), ('O', 2)):
                    rr = [r for r in rows if t in r[a]]
                    if rr:
                        c[(n, t)] = (k, np.sum([r[a][t] for r in rr], axis=0))
            elif rows[0]['lab'] in ('inner', 'outer'):
                c[n] = ({'inner': 1, 'outer': 2}[rows[0]['lab']], np.sum([r[a]['late'] for r in rows], axis=0))
        s = answer_stats(c)
        h = np.sum([r[a]['hold'] for r in part], axis=0)
        print(f'  {ds} {a}: dung theo o {fmt(s["theo_o"])} (gop {fmt(s["gop_cua_so"])}), tra loi {fmt(s["tra_loi_theo_o"])}, o co tra loi {s["o_co_tra_loi"]}, bao nham {h[1:].sum()/h.sum():.3f}')

print('=== X1, hieu so voi A0, bootstrap theo o phan tang theo lop (2000 lan)')
x1 = L('x/x1.json')
ARMS = ['S1_k5', 'S1_kall', 'S2_k5', 'S2_kall', 'S4_k5', 'S4_kall', 'S4_all_khong_cay', 'E3_chinh_o', 'E5_chinh_o', 'E10_chinh_o']


def per_bearing(part, arm):
    out = {}
    for n in {r['n'] for r in part}:
        v = [r[arm]['acc'] for r in part if r['n'] == n and arm in r]
        if v:
            out[n] = float(np.mean(v))
    return out


for ds in ('xjtu', 'uored'):
    part = [r for r in x1 if r['ds'] == ds]
    lab = {r['n']: r['lab'] for r in part}
    base = per_bearing(part, 'A0')
    for scope, classes in (('trong+ngoai', ('inner', 'outer')), ('moi lop', tuple(sorted(set(lab.values()))))):
        idx = {c: [n for n in base if lab[n] == c] for c in classes}
        a0 = float(np.mean([np.mean([base[n] for n in idx[c]]) for c in classes]))
        print(f' {ds} {scope}: A0 {a0:.3f}, so o {[len(idx[c]) for c in classes]}')
        for arm in ARMS:
            v = per_bearing(part, arm)
            keep = {c: [n for n in idx[c] if n in v] for c in classes}
            if not all(keep.values()):
                continue
            pt = float(np.mean([np.mean([v[n]-base[n] for n in keep[c]]) for c in classes]))
            boots = [np.mean([np.mean([v[n]-base[n] for n in rs.choice(keep[c], len(keep[c]))]) for c in classes]) for _ in range(2000)]
            val = float(np.mean([np.mean([v[n] for n in keep[c]]) for c in classes]))
            print(f'   {arm:18s} {val:.3f}  hieu {pt:+.3f} CI {np.percentile(boots, 2.5):+.3f} {np.percentile(boots, 97.5):+.3f}')

print('=== X1, cay + that so voi chi that (cung so su kien), trong+ngoai, cung bootstrap')
for ds in ('xjtu', 'uored'):
    part = [r for r in x1 if r['ds'] == ds]
    lab = {r['n']: r['lab'] for r in part}
    idx = {c: [n for n in lab if lab[n] == c] for c in ('inner', 'outer')}
    for m in (1, 2, 4):
        a, b = per_bearing(part, f'S{m}_kall'), per_bearing(part, f'S{m}_all_khong_cay')
        pt = float(np.mean([np.mean([a[n]-b[n] for n in idx[c]]) for c in idx]))
        boots = [np.mean([np.mean([a[n]-b[n] for n in rs.choice(idx[c], len(idx[c]))]) for c in idx]) for _ in range(2000)]
        print(f'  {ds} S{m}: cay+that {np.mean([np.mean([a[n] for n in idx[c]]) for c in idx]):.3f}, chi that {np.mean([np.mean([b[n] for n in idx[c]]) for c in idx]):.3f}, hieu {pt:+.3f} CI {np.percentile(boots, 2.5):+.3f} {np.percentile(boots, 97.5):+.3f}')

print('=== Cung cau hinh 1 kHz tren UORED: E8 va X9 chi khac dong ngau nhien cay loi')
rows8 = [r for r in L('e8/test.json')['rows'] if r['cfg'] == '1k']
print('  seed E8', sorted({r['seed'] for r in rows8}), 'seed X9', sorted({r['seed'] for r in x9 if r['ds'] == 'uored'}))
for i in sorted({int(r['i']) for r in rows8 if r['lab'] in ('inner', 'outer')}):
    a = np.sum([r['2']['ans'] for r in rows8 if int(r['i']) == i], axis=0).astype(int).tolist()
    b = np.sum([r['1k_cu']['late'] for r in x9 if r['ds'] == 'uored' and r['n'] == str(i)], axis=0).tolist()
    print(f'  o {i:2d} {LAB[i]:5s} E8 [chua ro, trong, ngoai] {a}  X9 {b}')
